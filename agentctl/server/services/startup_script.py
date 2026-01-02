"""Generate VM startup scripts."""

STARTUP_SCRIPT_TEMPLATE = '''#!/bin/bash
set -e

# === Configuration ===
AGENT_ID="{agent_id}"
MASTER_URL="{master_url}"
PROJECT="{project}"
ENGINE="{engine}"
TIMEOUT={timeout}
SCREENSHOT_INTERVAL={screenshot_interval}

log() {{ echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }}

log "=== AgentCtl Agent Starting ==="
log "Agent ID: $AGENT_ID"

# === Install Dependencies ===
log "Installing dependencies..."
apt-get update -qq
apt-get install -y -qq git curl python3 python3-pip nodejs npm jq scrot xvfb

# Install Claude Code
npm install -g @anthropic-ai/claude-code 2>/dev/null || true

# === Fetch Secrets from Instance Metadata ===
# NOTE: Secrets are injected by master server via metadata, NOT fetched from Secret Manager.
# This means agent VMs don't need secretmanager IAM permissions (more secure).
log "Loading secrets from metadata..."
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
METADATA_HEADER="Metadata-Flavor: Google"

export ANTHROPIC_API_KEY=$(curl -s "$METADATA_URL/anthropic-api-key" -H "$METADATA_HEADER" || echo "")
GITHUB_TOKEN=$(curl -s "$METADATA_URL/github-token" -H "$METADATA_HEADER" 2>/dev/null || echo "")

if [ -z "$ANTHROPIC_API_KEY" ]; then
    log "ERROR: No Anthropic API key found in metadata!"
    exit 1
fi

if [ -n "$GITHUB_TOKEN" ]; then
    export GITHUB_TOKEN
    git config --global credential.helper store
    echo "https://$GITHUB_TOKEN:x-oauth-basic@github.com" > ~/.git-credentials
fi

# === Setup Workspace ===
mkdir -p /workspace
cd /workspace

REPO="{repo}"
BRANCH="{branch}"
if [ -n "$REPO" ]; then
    log "Cloning $REPO..."
    git clone "$REPO" repo 2>/dev/null || git clone "https://$GITHUB_TOKEN@${{REPO#https://}}" repo
    cd repo
    git config user.email "agent@agentctl.local"
    git config user.name "AgentCtl Agent"
    if [ -n "$BRANCH" ]; then
        git checkout -B "$BRANCH"
        git push -u origin "$BRANCH" 2>/dev/null || true
    fi
fi

# === Save Prompt ===
cat > /workspace/.prompt << 'PROMPT_END'
{prompt}
PROMPT_END

# === Auto-commit Function ===
auto_commit() {{
    cd /workspace/repo 2>/dev/null || return
    if [ -n "$(git status --porcelain)" ]; then
        git add -A
        git commit -m "Auto-commit: $(date '+%Y-%m-%d %H:%M:%S')" || true
        git push || true
    fi
}}

# === Screenshot Function ===
take_screenshot() {{
    mkdir -p /workspace/screenshots
    DISPLAY=:99 scrot "/workspace/screenshots/$(date +%s).png" 2>/dev/null || true
}}

# === Start Background Services ===
# Virtual display for screenshots
Xvfb :99 -screen 0 1280x720x24 &
export DISPLAY=:99

# Auto-commit every 5 minutes
while true; do sleep 300; auto_commit; done &
AUTOCOMMIT_PID=$!

# Screenshots (if enabled)
if [ "$SCREENSHOT_INTERVAL" -gt 0 ]; then
    while true; do sleep $SCREENSHOT_INTERVAL; take_screenshot; done &
fi

# === Report Ready ===
log "Reporting ready status..."
curl -s -X POST "$MASTER_URL/v1/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "running"}}' || true

# === Run Agent ===
log "Starting $ENGINE with timeout ${{TIMEOUT}}s..."
cd /workspace/repo 2>/dev/null || cd /workspace

PROMPT=$(cat /workspace/.prompt)

if [ "$ENGINE" = "claude" ]; then
    timeout $TIMEOUT claude --dangerously-skip-permissions --print "$PROMPT" 2>&1 | tee /workspace/agent.log || true
fi

# === Cleanup ===
log "Agent task completed"

# Kill background jobs
kill $AUTOCOMMIT_PID 2>/dev/null || true

# Final commit
auto_commit
log "Final commit done"

# Upload screenshots to GCS
gsutil -m cp /workspace/screenshots/* gs://{bucket}/$AGENT_ID/screenshots/ 2>/dev/null || true

# Report completion
curl -s -X POST "$MASTER_URL/v1/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "completed"}}' || true

log "Shutting down..."
shutdown -h now
'''


def generate_startup_script(
    agent_id: str,
    prompt: str,
    engine: str,
    master_url: str,
    project: str,
    bucket: str,
    repo: str = "",
    branch: str = "",
    timeout: int = 14400,
    screenshot_interval: int = 60,
) -> str:
    """Generate startup script for agent VM.

    Args:
        agent_id: Unique agent identifier
        prompt: Task prompt for the agent
        engine: AI engine to use (e.g., "claude")
        master_url: URL of the master server for heartbeats
        project: GCP project ID
        bucket: GCS bucket name for artifacts
        repo: Git repository URL to clone (optional)
        branch: Git branch to work on (optional)
        timeout: Task timeout in seconds (default: 4 hours)
        screenshot_interval: Seconds between screenshots (0 to disable)

    Returns:
        Bash startup script as a string
    """
    return STARTUP_SCRIPT_TEMPLATE.format(
        agent_id=agent_id,
        prompt=prompt.replace("'", "'\"'\"'"),  # Escape single quotes
        engine=engine,
        master_url=master_url,
        project=project,
        bucket=bucket,
        repo=repo or "",
        branch=branch or "",
        timeout=timeout,
        screenshot_interval=screenshot_interval,
    )
