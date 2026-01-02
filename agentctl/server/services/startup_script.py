"""Generate VM startup scripts."""

STARTUP_SCRIPT_TEMPLATE = '''#!/bin/bash
set -e

# --- Configuration ---
AGENT_ID="{agent_id}"
MASTER_URL="{master_url}"
PROJECT="{project}"
ENGINE="{engine}"
PROMPT_FILE="/workspace/.prompt"

echo "=== AgentCtl Agent Starting ==="
echo "Agent ID: $AGENT_ID"

# --- Install Dependencies ---
apt-get update
apt-get install -y git curl python3 python3-pip nodejs npm jq

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# --- Fetch Secrets ---
ANTHROPIC_KEY=$(gcloud secrets versions access latest --secret=anthropic-api-key)
export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"

# GitHub token (optional)
GITHUB_TOKEN=$(gcloud secrets versions access latest --secret=github-token 2>/dev/null || echo "")
if [ -n "$GITHUB_TOKEN" ]; then
    export GITHUB_TOKEN
fi

# --- Setup Workspace ---
mkdir -p /workspace
cd /workspace

# Clone repo if specified
REPO="{repo}"
BRANCH="{branch}"
if [ -n "$REPO" ]; then
    if [ -n "$GITHUB_TOKEN" ]; then
        git clone "https://${{GITHUB_TOKEN}}@${{REPO#https://}}" repo
    else
        git clone "$REPO" repo
    fi
    cd repo
    if [ -n "$BRANCH" ]; then
        git checkout -B "$BRANCH"
    fi
fi

# --- Save Prompt ---
cat > "$PROMPT_FILE" << 'PROMPT_END'
{prompt}
PROMPT_END

# --- Report Ready ---
curl -X POST "$MASTER_URL/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "running"}}' || true

# --- Run Agent ---
echo "Starting $ENGINE..."
if [ "$ENGINE" = "claude" ]; then
    cd /workspace/repo 2>/dev/null || cd /workspace
    timeout {timeout}s claude --dangerously-skip-permissions --print "$(cat $PROMPT_FILE)" || true
fi

# --- Cleanup ---
echo "Agent finished"
curl -X POST "$MASTER_URL/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "completed"}}' || true

# Final git commit
cd /workspace/repo 2>/dev/null && git add -A && git commit -m "Final auto-commit" && git push || true

# Shutdown
shutdown -h now
'''


def generate_startup_script(
    agent_id: str,
    prompt: str,
    engine: str,
    master_url: str,
    project: str,
    repo: str = "",
    branch: str = "",
    timeout: int = 14400,
) -> str:
    """Generate startup script for agent VM."""
    return STARTUP_SCRIPT_TEMPLATE.format(
        agent_id=agent_id,
        prompt=prompt.replace("'", "'\"'\"'"),  # Escape single quotes
        engine=engine,
        master_url=master_url,
        project=project,
        repo=repo or "",
        branch=branch or "",
        timeout=timeout,
    )
