#!/bin/bash
# Test the VM startup script locally using Docker
# Emulates GCP environment as closely as possible

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
AGENT_ID="${1:-test-$(date +%s)}"
PROMPT="${2:-Create a simple hello.txt file with the text 'Hello World'}"
MAX_ITERATIONS="${3:-1}"  # Default to 1 iteration for testing
FULL_TEST="${4:-false}"   # Set to 'true' to run actual Claude (uses API credits)

echo "=== AgentCtl Local Docker Test ==="
echo "Agent ID: $AGENT_ID"
echo "Prompt: $PROMPT"
echo "Max iterations: $MAX_ITERATIONS"
echo "Full test (uses API): $FULL_TEST"
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

# Create mock metadata server script
MOCK_METADATA_FILE="/tmp/mock_metadata_$AGENT_ID.py"
cat > "$MOCK_METADATA_FILE" << 'METADATA_EOF'
#!/usr/bin/env python3
"""Mock GCP metadata server for local testing."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import sys

class MetadataHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Check for required header
        if self.headers.get('Metadata-Flavor') != 'Google':
            self.send_error(403, 'Missing Metadata-Flavor header')
            return

        # Route requests
        if 'anthropic-api-key' in self.path:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(os.environ.get('ANTHROPIC_API_KEY', '').encode())
        elif 'github-token' in self.path:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(os.environ.get('GITHUB_TOKEN', '').encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8888), MetadataHandler)
    print('Mock metadata server running on :8888', file=sys.stderr)
    server.serve_forever()
METADATA_EOF

# Create wrapper script that sets up the environment
DOCKER_WRAPPER_FILE="/tmp/docker_wrapper_$AGENT_ID.sh"
cat > "$DOCKER_WRAPPER_FILE" << 'WRAPPER_EOF'
#!/bin/bash
set -ex

echo "[wrapper] Installing python3 and curl..."
apt-get update -qq && apt-get install -y -qq python3 curl >/dev/null 2>&1
echo "[wrapper] Dependencies installed"

echo "[wrapper] Starting mock metadata server..."
python3 /mock_metadata.py &
METADATA_PID=$!
sleep 1
echo "[wrapper] Metadata server started (PID: $METADATA_PID)"

echo "[wrapper] Adding hosts entry..."
echo "127.0.0.1 metadata.google.internal" >> /etc/hosts
echo "[wrapper] Hosts entry added"

# Override curl to use our mock metadata server port
# Export the real curl path so child processes can use it
export REAL_CURL=/usr/bin/curl
curl() {
    # Rewrite metadata.google.internal URLs to localhost:8888
    args=("$@")
    new_args=()
    for arg in "${args[@]}"; do
        if [[ "$arg" == *"metadata.google.internal"* ]]; then
            arg="${arg/metadata.google.internal/127.0.0.1:8888}"
        fi
        new_args+=("$arg")
    done
    $REAL_CURL "${new_args[@]}"
}
export -f curl
echo "[wrapper] curl function defined"

# Mock gsutil - simulate GCS operations locally
mkdir -p /tmp/mock_gcs
gsutil() {
    case "$1" in
        cp)
            shift
            src=""
            dest=""
            quiet=false
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    -q) quiet=true; shift ;;
                    -m) shift ;;
                    gs://*) dest="$1"; shift ;;
                    *) src="$1"; shift ;;
                esac
            done
            if [ -n "$src" ] && [ -n "$dest" ]; then
                mock_path="/tmp/mock_gcs/${dest#gs://}"
                mkdir -p "$(dirname "$mock_path")"
                if [ -f "$src" ]; then
                    cp "$src" "$mock_path" 2>/dev/null || true
                    $quiet || echo "[GCS] Uploaded $src -> $dest"
                fi
            fi
            ;;
        cat)
            gcs_path="$2"
            mock_path="/tmp/mock_gcs/${gcs_path#gs://}"
            [ -f "$mock_path" ] && cat "$mock_path"
            ;;
        *)
            echo "[GCS-MOCK] gsutil $@"
            ;;
    esac
}
export -f gsutil

# Mock shutdown - just cleanup and exit
shutdown() {
    echo ""
    echo "============================================"
    echo "[MOCK] VM shutdown requested"
    echo "============================================"
    echo ""
    echo "=== Mock GCS Contents ==="
    find /tmp/mock_gcs -type f 2>/dev/null | while read f; do
        echo "  $f"
        head -c 100 "$f" 2>/dev/null | tr '\n' ' '
        echo "..."
    done
    echo ""
    kill $METADATA_PID 2>/dev/null || true
    exit 0
}
export -f shutdown

# Run the actual startup script
echo "=== Running startup script ==="
bash /startup.sh
WRAPPER_EOF

echo "=== Starting Docker container ==="
echo "Using x86_64 platform to match GCP VMs"
echo "Press Ctrl+C to stop"
echo ""

# Run in Docker with x86_64 emulation to match GCP
# Use -t only if we have a TTY
if [ -t 0 ]; then
    DOCKER_FLAGS="-it"
else
    DOCKER_FLAGS=""
fi

# Use platform flag to emulate GCP's x86_64 architecture
docker run --rm $DOCKER_FLAGS \
    --platform linux/amd64 \
    -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    -e GITHUB_TOKEN="${GITHUB_TOKEN:-}" \
    -v "$SCRIPT_FILE:/startup.sh:ro" \
    -v "$MOCK_METADATA_FILE:/mock_metadata.py:ro" \
    -v "$DOCKER_WRAPPER_FILE:/wrapper.sh:ro" \
    ubuntu:22.04 \
    bash /wrapper.sh

echo ""
echo "=== Docker test complete ==="
