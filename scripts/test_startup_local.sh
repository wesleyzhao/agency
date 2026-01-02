#!/bin/bash
# Test the VM startup script locally using Docker
# This catches 90% of issues without touching GCP

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
AGENT_ID="${1:-test-$(date +%s)}"
PROMPT="${2:-Create a simple hello.txt file with the text 'Hello World'}"
MAX_ITERATIONS="${3:-3}"  # Limit iterations for testing

echo "=== AgentCtl Local Docker Test ==="
echo "Agent ID: $AGENT_ID"
echo "Prompt: $PROMPT"
echo "Max iterations: $MAX_ITERATIONS"
echo ""

# Check for required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY environment variable not set"
    echo "Export it: export ANTHROPIC_API_KEY=your-key"
    exit 1
fi

# Generate the startup script using Python
echo "Generating startup script..."
STARTUP_SCRIPT=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from agentctl.server.services.startup_script import generate_startup_script

script = generate_startup_script(
    agent_id='$AGENT_ID',
    prompt='''$PROMPT''',
    engine='claude',
    project='test-project',
    bucket='test-bucket',
    master_url='',  # No master for local testing
    max_iterations=$MAX_ITERATIONS,
)
print(script)
")

# Check bash syntax
echo "Checking bash syntax..."
echo "$STARTUP_SCRIPT" | bash -n
if [ $? -ne 0 ]; then
    echo "ERROR: Startup script has syntax errors!"
    exit 1
fi
echo "Syntax OK"

# Save script for inspection
SCRIPT_FILE="/tmp/startup_script_$AGENT_ID.sh"
echo "$STARTUP_SCRIPT" > "$SCRIPT_FILE"
echo "Startup script saved to: $SCRIPT_FILE"
echo ""

# Create a modified version for Docker (skip shutdown, mock metadata)
DOCKER_SCRIPT=$(cat << 'DOCKER_EOF'
#!/bin/bash
# Mock the GCP metadata service
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY_FROM_ENV"

# Override metadata fetch
curl() {
    if [[ "$*" == *"metadata.google.internal"*"anthropic-api-key"* ]]; then
        echo "$ANTHROPIC_API_KEY"
    elif [[ "$*" == *"metadata.google.internal"*"github-token"* ]]; then
        echo ""
    else
        /usr/bin/curl "$@"
    fi
}
export -f curl

# Override gsutil to be a no-op for local testing
gsutil() {
    echo "[MOCK] gsutil $@"
}
export -f gsutil

# Override shutdown to just exit
shutdown() {
    echo "[MOCK] shutdown requested, exiting instead"
    exit 0
}
export -f shutdown

DOCKER_EOF
)

# Combine mock functions with actual startup script (removing the first shebang)
DOCKER_STARTUP="${DOCKER_SCRIPT}
$(echo "$STARTUP_SCRIPT" | tail -n +2)"

# Save Docker script
DOCKER_SCRIPT_FILE="/tmp/docker_startup_$AGENT_ID.sh"
echo "$DOCKER_STARTUP" > "$DOCKER_SCRIPT_FILE"
chmod +x "$DOCKER_SCRIPT_FILE"

echo "=== Starting Docker container ==="
echo "This will run the startup script in an Ubuntu 22.04 container"
echo "Press Ctrl+C to stop"
echo ""

# Run in Docker
docker run --rm -it \
    -e ANTHROPIC_API_KEY_FROM_ENV="$ANTHROPIC_API_KEY" \
    -v "$DOCKER_SCRIPT_FILE:/startup.sh:ro" \
    ubuntu:22.04 \
    bash -c "chmod +x /startup.sh && /startup.sh"

echo ""
echo "=== Docker test complete ==="
