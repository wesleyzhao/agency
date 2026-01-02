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

export HOME=/root

log "=== AgentCtl Agent Starting ==="
log "Agent ID: $AGENT_ID"

# === Create agent user (Claude Code cannot run as root) ===
log "Creating agent user..."
useradd -m -s /bin/bash agent
AGENT_HOME=/home/agent

# === Install Dependencies ===
log "Installing dependencies..."
apt-get update -qq
apt-get install -y -qq git curl python3 python3-pip jq scrot xvfb ca-certificates gnupg sudo

# Install Node.js 18 (required for Claude Code)
log "Installing Node.js 18..."
mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list
apt-get update -qq
apt-get install -y -qq nodejs

log "Node.js version: $(node --version)"

# Install Claude Code
log "Installing Claude Code..."
npm install -g @anthropic-ai/claude-code

# === Fetch Secrets from Instance Metadata ===
# NOTE: Secrets are injected by master server via metadata, NOT fetched from Secret Manager.
# This means agent VMs don't need secretmanager IAM permissions (more secure).
log "Loading secrets from metadata..."
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
METADATA_HEADER="Metadata-Flavor: Google"

ANTHROPIC_API_KEY=$(curl -s "$METADATA_URL/anthropic-api-key" -H "$METADATA_HEADER" || echo "")
GITHUB_TOKEN=$(curl -s "$METADATA_URL/github-token" -H "$METADATA_HEADER" 2>/dev/null || echo "")

if [ -z "$ANTHROPIC_API_KEY" ]; then
    log "ERROR: No Anthropic API key found in metadata!"
    exit 1
fi

# === Setup Workspace ===
mkdir -p /workspace
chown agent:agent /workspace

REPO="{repo}"
BRANCH="{branch}"

# Setup git credentials for agent user
if [ -n "$GITHUB_TOKEN" ]; then
    sudo -u agent git config --global credential.helper store
    echo "https://$GITHUB_TOKEN:x-oauth-basic@github.com" > $AGENT_HOME/.git-credentials
    chown agent:agent $AGENT_HOME/.git-credentials
fi

sudo -u agent git config --global user.email "agent@agentctl.local"
sudo -u agent git config --global user.name "AgentCtl Agent"

if [ -n "$REPO" ]; then
    log "Cloning $REPO..."
    cd /workspace
    sudo -u agent git clone "$REPO" repo 2>/dev/null || sudo -u agent git clone "https://$GITHUB_TOKEN@${{REPO#https://}}" repo
    cd repo
    if [ -n "$BRANCH" ]; then
        sudo -u agent git checkout -B "$BRANCH"
        sudo -u agent git push -u origin "$BRANCH" 2>/dev/null || true
    fi
fi

# === Save Prompt ===
cat > /workspace/.prompt << 'PROMPT_END'
{prompt}
PROMPT_END
chown agent:agent /workspace/.prompt

# === Auto-commit Function (runs as agent user) ===
auto_commit() {{
    sudo -u agent bash -c 'cd /workspace/repo 2>/dev/null || exit 0; if [ -n "$(git status --porcelain)" ]; then git add -A && git commit -m "Auto-commit: $(date +%Y-%m-%d\ %H:%M:%S)" && git push; fi' || true
}}

# === Screenshot Function ===
take_screenshot() {{
    mkdir -p /workspace/screenshots
    chown agent:agent /workspace/screenshots
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

# === Run Agent as non-root user ===
log "Starting $ENGINE with timeout ${{TIMEOUT}}s..."
WORKDIR=/workspace/repo
[ -d "$WORKDIR" ] || WORKDIR=/workspace

PROMPT=$(cat /workspace/.prompt)

if [ "$ENGINE" = "claude" ]; then
    # Run Claude Code as agent user (cannot run as root)
    # Create a runner script to avoid quoting issues
    cat > /workspace/run_claude.sh << 'RUNNER_EOF'
#!/bin/bash
cd "$1"
exec timeout "$2" claude --dangerously-skip-permissions --print "$(cat /workspace/.prompt)"
RUNNER_EOF
    chmod +x /workspace/run_claude.sh
    chown agent:agent /workspace/run_claude.sh

    sudo -u agent env ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" DISPLAY=:99 HOME=/home/agent /workspace/run_claude.sh "$WORKDIR" "$TIMEOUT" 2>&1 | tee /workspace/agent.log || true
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
