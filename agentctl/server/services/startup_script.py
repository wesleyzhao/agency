"""Generate VM startup scripts for continuous Claude Code agents.

This script sets up a GCP VM to run Anthropic's autonomous-coding harness,
which handles session management, progress tracking, and context preservation
across multiple iterations.

Key features:
- Installs all dependencies (Node.js 18, Python 3.11, gcloud SDK)
- Runs Anthropic's proven harness (not raw claude CLI)
- Syncs progress to GCS every minute (no master server needed)
- VM runs continuously until task completes or max_iterations reached
"""

STARTUP_SCRIPT_TEMPLATE = '''#!/bin/bash
set -e

# === Configuration ===
AGENT_ID="__AGENT_ID__"
PROJECT="__PROJECT__"
BUCKET="__BUCKET__"
TIMEOUT=__TIMEOUT__
MAX_ITERATIONS=__MAX_ITERATIONS__
MASTER_URL="__MASTER_URL__"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/agent.log; }

export HOME=/root
export DEBIAN_FRONTEND=noninteractive

# === Helper: Report status to master server ===
report_status() {
    local status=$1
    local message=${2:-""}

    # Always write to GCS
    echo "$status" > /tmp/agent_status
    gsutil -q cp /tmp/agent_status gs://$BUCKET/agents/$AGENT_ID/status 2>/dev/null || true

    # Report to master server if URL is set and reachable
    if [ -n "$MASTER_URL" ] && [ "$MASTER_URL" != "none" ]; then
        curl -s -X POST "$MASTER_URL/v1/internal/heartbeat" \
            -H "Content-Type: application/json" \
            -d "{\"agent_id\": \"$AGENT_ID\", \"status\": \"$status\", \"message\": \"$message\"}" \
            --connect-timeout 5 \
            --max-time 10 \
            2>/dev/null || log "Warning: Could not reach master server"
    fi
}

log "=== AgentCtl Agent Starting ==="
log "Agent ID: $AGENT_ID"
log "Project: $PROJECT"
log "Bucket: $BUCKET"
log "Master URL: ${MASTER_URL:-none}"

# === Create agent user (Claude Code cannot run as root) ===
log "Creating agent user..."
useradd -m -s /bin/bash agent || true
AGENT_HOME=/home/agent

# === Install Dependencies ===
log "Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq git curl jq ca-certificates gnupg sudo python3.11 python3.11-venv python3-pip

# Install Node.js 18 (required for Claude Code CLI)
log "Installing Node.js 18..."
mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list
apt-get update -qq
apt-get install -y -qq nodejs

log "Node.js version: $(node --version)"

# Install Google Cloud SDK (for gsutil)
log "Installing Google Cloud SDK..."
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list
apt-get update -qq
apt-get install -y -qq google-cloud-cli

log "gcloud version: $(gcloud --version | head -1)"

# Report progress
report_status "starting" "Dependencies installed, setting up workspace"

# Install Claude Code CLI
log "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# Install claude-code-sdk for Python harness
log "Installing claude-code-sdk..."
pip3 install claude-code-sdk --break-system-packages

# === Fetch Secrets from Instance Metadata ===
log "Loading secrets from metadata..."
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
METADATA_HEADER="Metadata-Flavor: Google"

ANTHROPIC_API_KEY=$(curl -s "$METADATA_URL/anthropic-api-key" -H "$METADATA_HEADER" || echo "")
GITHUB_TOKEN=$(curl -s "$METADATA_URL/github-token" -H "$METADATA_HEADER" 2>/dev/null || echo "")

if [ -z "$ANTHROPIC_API_KEY" ]; then
    log "ERROR: No Anthropic API key found in metadata!"
    # Upload error log to GCS before exiting
    gsutil cp /var/log/agent.log gs://$BUCKET/agents/$AGENT_ID/logs/startup.log 2>/dev/null || true
    exit 1
fi

export ANTHROPIC_API_KEY

# === Setup Workspace ===
log "Setting up workspace..."
WORKSPACE=/workspace/$AGENT_ID
mkdir -p $WORKSPACE
chown -R agent:agent /workspace

# Setup git for agent user
sudo -u agent git config --global user.email "agent@agentctl.local"
sudo -u agent git config --global user.name "AgentCtl Agent $AGENT_ID"
if [ -n "$GITHUB_TOKEN" ]; then
    sudo -u agent git config --global credential.helper store
    echo "https://$GITHUB_TOKEN:x-oauth-basic@github.com" > $AGENT_HOME/.git-credentials
    chown agent:agent $AGENT_HOME/.git-credentials
fi

REPO="__REPO__"
BRANCH="__BRANCH__"

if [ -n "$REPO" ]; then
    log "Cloning $REPO..."
    cd $WORKSPACE
    sudo -u agent git clone "$REPO" project 2>/dev/null || sudo -u agent git clone "https://$GITHUB_TOKEN@${REPO#https://}" project
    cd project
    if [ -n "$BRANCH" ]; then
        sudo -u agent git checkout -B "$BRANCH"
        sudo -u agent git push -u origin "$BRANCH" 2>/dev/null || true
    fi
    WORKDIR=$WORKSPACE/project
else
    WORKDIR=$WORKSPACE/project
    mkdir -p $WORKDIR
    chown agent:agent $WORKDIR
fi

# === Save Prompt/App Spec ===
cat > $WORKSPACE/app_spec.txt << 'PROMPT_END'
__PROMPT__
PROMPT_END
chown agent:agent $WORKSPACE/app_spec.txt

# === Create Agent Runner Script ===
# This implements Anthropic's two-agent pattern for long-running tasks
cat > $WORKSPACE/run_agent.py << 'AGENT_SCRIPT'
#!/usr/bin/env python3
"""
Continuous Claude Code agent using Anthropic's proven patterns.

This implements:
- Session management across context windows
- Progress tracking via files (feature_list.json, claude-progress.txt)
- Git-based history for continuity
- Automatic continuation between sessions

Based on: https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Import claude-code-sdk
try:
    from claude_code_sdk import Client
except ImportError:
    print("ERROR: claude-code-sdk not installed")
    sys.exit(1)


def log(msg: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def is_first_session(project_dir: Path) -> bool:
    """Check if this is the first session (no progress file yet)."""
    return not (project_dir / "feature_list.json").exists()


def get_initializer_prompt(app_spec: str) -> str:
    """Prompt for the first session - sets up project structure."""
    return f"""You are an AI coding agent tasked with building an application.

## Your Task
Read the application specification below and:
1. Create a feature_list.json file with ALL features needed (be comprehensive)
2. Set up the initial project structure
3. Create an init.sh script that sets up the development environment
4. Initialize git and make the first commit

## Application Specification
{app_spec}

## Feature List Format
Create feature_list.json with this structure:
{{
    "features": [
        {{"id": 1, "description": "Feature description", "status": "pending"}},
        ...
    ]
}}

## Important
- Be thorough - list ALL features needed
- Mark all features as "pending" initially
- The feature list is the source of truth for what needs to be done
- Make sure init.sh is executable and works

Start by creating the feature_list.json file."""


def get_coding_prompt(app_spec: str, progress: str) -> str:
    """Prompt for subsequent sessions - implements features."""
    return f"""You are an AI coding agent continuing work on an application.

## Your Task
1. Read feature_list.json to see what features are pending
2. Pick the FIRST pending feature
3. Implement it completely
4. Test it works
5. Update feature_list.json to mark it as "completed"
6. Commit your changes with a descriptive message

## Application Specification
{app_spec}

## Previous Progress
{progress}

## Important Rules
- Only work on ONE feature per session
- Test your work before marking complete
- Always commit after completing a feature
- Update claude-progress.txt with what you did

Start by reading feature_list.json and picking the next pending feature."""


def load_progress(project_dir: Path) -> str:
    """Load progress notes from previous sessions."""
    progress_file = project_dir / "claude-progress.txt"
    if progress_file.exists():
        return progress_file.read_text()
    return "No previous progress."


def sync_to_gcs(workspace: Path, bucket: str, agent_id: str):
    """Sync progress files to GCS."""
    import subprocess

    files_to_sync = [
        "feature_list.json",
        "claude-progress.txt",
        "agent.log",
    ]

    for fname in files_to_sync:
        fpath = workspace / fname
        if fpath.exists():
            dest = f"gs://{bucket}/agents/{agent_id}/{fname}"
            subprocess.run(
                ["gsutil", "-q", "cp", str(fpath), dest],
                capture_output=True
            )

    # Also sync the log
    log_path = Path("/var/log/agent.log")
    if log_path.exists():
        subprocess.run(
            ["gsutil", "-q", "cp", str(log_path), f"gs://{bucket}/agents/{agent_id}/logs/agent.log"],
            capture_output=True
        )


async def run_session(client: Client, prompt: str, project_dir: Path) -> str:
    """Run a single agent session."""
    log("Starting session...")

    response_text = ""
    async for event in client.query(
        prompt,
        cwd=str(project_dir),
    ):
        if hasattr(event, 'text'):
            print(event.text, end='', flush=True)
            response_text += event.text

    print()  # newline after response
    return response_text


async def run_agent(
    workspace: Path,
    project_dir: Path,
    app_spec: str,
    bucket: str,
    agent_id: str,
    max_iterations: int = 0,
):
    """Run the continuous agent loop."""
    iteration = 0

    while True:
        iteration += 1
        log(f"=== Iteration {iteration} ===")

        if max_iterations > 0 and iteration > max_iterations:
            log(f"Reached max iterations ({max_iterations})")
            break

        # Create fresh client for each session (manages context)
        client = Client()

        # Determine which prompt to use
        if is_first_session(project_dir):
            log("First session - initializing project...")
            prompt = get_initializer_prompt(app_spec)
        else:
            log("Continuing from previous session...")
            progress = load_progress(project_dir)
            prompt = get_coding_prompt(app_spec, progress)

            # Check if all features are complete
            feature_file = project_dir / "feature_list.json"
            if feature_file.exists():
                try:
                    features = json.loads(feature_file.read_text())
                    pending = [f for f in features.get("features", []) if f.get("status") == "pending"]
                    if not pending:
                        log("All features completed!")
                        break
                    log(f"{len(pending)} features remaining")
                except json.JSONDecodeError:
                    pass

        try:
            await run_session(client, prompt, project_dir)
        except Exception as e:
            log(f"Session error: {e}")

        # Sync progress to GCS after each session
        log("Syncing to GCS...")
        sync_to_gcs(workspace, bucket, agent_id)

        # Brief pause between sessions
        log("Waiting 5 seconds before next session...")
        await asyncio.sleep(5)

    log("Agent completed all iterations")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--max-iterations", type=int, default=0)
    args = parser.parse_args()

    workspace = Path(args.workspace)
    project_dir = Path(args.project_dir)

    # Load app spec
    app_spec = (workspace / "app_spec.txt").read_text()

    log(f"Workspace: {workspace}")
    log(f"Project dir: {project_dir}")
    log(f"Max iterations: {args.max_iterations or 'unlimited'}")

    asyncio.run(run_agent(
        workspace=workspace,
        project_dir=project_dir,
        app_spec=app_spec,
        bucket=args.bucket,
        agent_id=args.agent_id,
        max_iterations=args.max_iterations,
    ))


if __name__ == "__main__":
    main()
AGENT_SCRIPT
chmod +x $WORKSPACE/run_agent.py
chown agent:agent $WORKSPACE/run_agent.py

# === GCS Sync Background Job ===
# Sync progress to GCS every 60 seconds
log "Starting GCS sync background job..."
(
    while true; do
        sleep 60
        gsutil -q cp $WORKSPACE/feature_list.json gs://$BUCKET/agents/$AGENT_ID/ 2>/dev/null || true
        gsutil -q cp $WORKSPACE/claude-progress.txt gs://$BUCKET/agents/$AGENT_ID/ 2>/dev/null || true
        gsutil -q cp /var/log/agent.log gs://$BUCKET/agents/$AGENT_ID/logs/ 2>/dev/null || true
    done
) &
SYNC_PID=$!

# === Report Running Status ===
report_status "running" "Agent starting"

# === Run Agent ===
log "Starting continuous agent..."
cd $WORKSPACE

MAX_ITER_ARG=""
if [ "$MAX_ITERATIONS" -gt 0 ]; then
    MAX_ITER_ARG="--max-iterations $MAX_ITERATIONS"
fi

sudo -u agent env \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    HOME=$AGENT_HOME \
    python3 $WORKSPACE/run_agent.py \
        --workspace $WORKSPACE \
        --project-dir $WORKDIR \
        --bucket $BUCKET \
        --agent-id $AGENT_ID \
        $MAX_ITER_ARG \
    2>&1 | tee -a /var/log/agent.log

EXIT_CODE=$?

# === Cleanup ===
log "Agent finished with exit code $EXIT_CODE"

# Kill background sync
kill $SYNC_PID 2>/dev/null || true

# Final sync
log "Final GCS sync..."
gsutil -q cp $WORKSPACE/feature_list.json gs://$BUCKET/agents/$AGENT_ID/ 2>/dev/null || true
gsutil -q cp $WORKSPACE/claude-progress.txt gs://$BUCKET/agents/$AGENT_ID/ 2>/dev/null || true
gsutil -q cp /var/log/agent.log gs://$BUCKET/agents/$AGENT_ID/logs/ 2>/dev/null || true

# Report final status
if [ $EXIT_CODE -eq 0 ]; then
    report_status "completed" "Agent finished successfully"
else
    report_status "failed" "Agent exited with code $EXIT_CODE"
fi

log "Shutting down VM..."
shutdown -h now
'''


def generate_startup_script(
    agent_id: str,
    prompt: str,
    engine: str,
    project: str,
    bucket: str,
    master_url: str = "",
    repo: str = "",
    branch: str = "",
    timeout: int = 14400,
    max_iterations: int = 0,
    **kwargs,  # Accept but ignore unused params for backwards compatibility
) -> str:
    """Generate startup script for continuous agent VM.

    Args:
        agent_id: Unique agent identifier
        prompt: Task prompt / application specification
        engine: AI engine to use (currently only "claude" supported)
        project: GCP project ID
        bucket: GCS bucket name for progress/logs
        master_url: URL of master server for status callbacks (optional)
        repo: Git repository URL to clone (optional)
        branch: Git branch to work on (optional)
        timeout: Not used (kept for API compatibility)
        max_iterations: Max agent iterations (0 = unlimited)

    Returns:
        Bash startup script as a string
    """
    # Escape the prompt for heredoc
    escaped_prompt = prompt.replace("\\", "\\\\")

    # Use simple string replacement to avoid conflicts with bash/Python braces
    script = STARTUP_SCRIPT_TEMPLATE
    script = script.replace("__AGENT_ID__", agent_id)
    script = script.replace("__PROMPT__", escaped_prompt)
    script = script.replace("__PROJECT__", project)
    script = script.replace("__BUCKET__", bucket)
    script = script.replace("__MASTER_URL__", master_url or "none")
    script = script.replace("__REPO__", repo or "")
    script = script.replace("__BRANCH__", branch or "")
    script = script.replace("__TIMEOUT__", str(timeout))
    script = script.replace("__MAX_ITERATIONS__", str(max_iterations))
    return script
