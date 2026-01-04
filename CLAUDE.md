# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

```bash
# Install with all dependencies
pip install -e ".[server,dev]"

# Run all tests (135 tests)
python -m pytest

# Run a single test file
python -m pytest tests/unit/test_config.py

# Run a specific test
python -m pytest tests/unit/test_config.py::test_config_defaults -v

# Run tests with coverage
python -m pytest --cov=agentctl tests/
```

## Project Architecture

This repository contains two CLI tools for managing autonomous Claude Code agents on GCP:

### 1. `agentctl` - Full-featured agent management (requires master server)
- **CLI** (`agentctl/cli/`): Click commands for run, list, status, stop, ssh, logs, screenshots, tell
- **Server** (`agentctl/server/`): FastAPI server with SQLite persistence, manages VM lifecycle
- **Providers** (`agentctl/providers/`): Abstract VM provider (GCP implementation)

### 2. `agency-quickdeploy` - Standalone one-command launcher (no server needed)
- **CLI** (`agency_quickdeploy/cli.py`): launch, status, logs, stop, list, init
- **Launcher** (`agency_quickdeploy/launcher.py`): Orchestrates GCP resources
- **GCP modules** (`agency_quickdeploy/gcp/`): vm.py, storage.py, secrets.py

### Shared Harness (`shared/harness/`)
Reusable components for both tools:
- `startup_template.py`: Generates VM startup scripts that embed a Python agent runner
- `agent_loop.py`: Pure functions for feature list parsing, progress tracking, prompt generation

## Key Design Patterns

**Two-agent architecture**: Initializer agent creates feature_list.json, then coding agents implement features one-by-one across context windows. Based on Anthropic's [autonomous-coding pattern](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding).

**GCS-based state**: Agent status, logs, and progress synced to `gs://<bucket>/agents/<agent-id>/` - no server required for agency-quickdeploy.

**VM metadata for secrets**: API keys passed via GCP instance metadata, not environment variables in startup script.

## Authentication

`agency-quickdeploy` supports two authentication methods:

### API Key (default)
- Uses `ANTHROPIC_API_KEY` environment variable or Secret Manager
- Billed per token usage
- Secret name: `anthropic-api-key`

### OAuth Token (subscription-based)
- Uses Claude Code subscription instead of per-token billing
- Generated via `claude setup-token` (requires browser)
- Secret name: `claude-oauth-credentials`

```bash
# Generate OAuth token (on machine with browser)
claude setup-token
# Outputs: sk-ant-oat01-...

# Store in Secret Manager (as JSON)
echo '{"claudeAiOauth":{"accessToken":"sk-ant-oat01-YOUR-TOKEN"}}' | \
    gcloud secrets create claude-oauth-credentials --data-file=-

# Launch with OAuth
agency-quickdeploy launch "Build an app" --auth-type oauth
```

## Environment Variables

For `agency-quickdeploy`:
- `QUICKDEPLOY_PROJECT` or `GOOGLE_CLOUD_PROJECT`: GCP project ID (required)
- `QUICKDEPLOY_ZONE`: GCP zone (default: us-central1-a)
- `QUICKDEPLOY_BUCKET`: GCS bucket (auto-generated if not set)
- `QUICKDEPLOY_AUTH_TYPE`: Authentication type (`api_key` or `oauth`)
- `ANTHROPIC_API_KEY`: API key (for api_key auth)
- `CLAUDE_CODE_OAUTH_TOKEN`: OAuth token (for oauth auth, alternative to Secret Manager)

For `agentctl`:
- `AGENTCTL_MASTER_URL`: Master server URL
- `AGENTCTL_GCP_PROJECT`, `AGENTCTL_GCP_REGION`, `AGENTCTL_GCP_ZONE`

## Usage Examples

```bash
# QuickDeploy: Launch agent with API key (default)
QUICKDEPLOY_PROJECT=my-project agency-quickdeploy launch "Build a todo app"

# QuickDeploy: Launch agent with OAuth (subscription billing)
QUICKDEPLOY_PROJECT=my-project agency-quickdeploy launch "Build a todo app" --auth-type oauth

# Keep VM running after completion (for debugging)
agency-quickdeploy launch "Build an API" --no-shutdown

# Monitor agent
agency-quickdeploy status agent-20260102-abc123
agency-quickdeploy logs agent-20260102-abc123

# SSH into running agent VM
gcloud compute ssh AGENT_ID --zone=us-central1-a --project=my-project

# Agentctl: Requires running master server
uvicorn agentctl.server.app:app --port 8000
agentctl run "Build a REST API"
agentctl list
agentctl ssh my-agent
```
