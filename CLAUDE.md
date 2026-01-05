# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation Quick Reference

**Current Work & Issues:** See [BACKLOG.md](BACKLOG.md) for known issues, bugs, and planned features.

**Detailed Documentation:**
- **API Reference:** [docs/api/API.md](docs/api/API.md) - REST API specification
- **CLI Commands:** [docs/cli/COMMANDS.md](docs/cli/COMMANDS.md) - Complete CLI reference
- **Deployment Guide:** [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) - GCP setup & deployment
- **Security:** [docs/deployment/SECURITY.md](docs/deployment/SECURITY.md) - Security model & best practices
- **Architecture:** [docs/architecture/TECHNICAL_SPEC.md](docs/architecture/TECHNICAL_SPEC.md) - Technical architecture
- **PRD:** [docs/architecture/PRD.md](docs/architecture/PRD.md) - Product requirements
- **Architecture Review:** [docs/architecture/ARCHITECTURE_REVIEW.md](docs/architecture/ARCHITECTURE_REVIEW.md)

**Historical Context:** [docs/archive/](docs/archive/) contains completed work logs and planning documents.

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

This repository contains two CLI tools for managing autonomous Claude Code agents on GCP or Railway:

### 1. `agentctl` - Full-featured agent management (requires master server)
- **CLI** (`agentctl/cli/`): Click commands for run, list, status, stop, ssh, logs, screenshots, tell
- **Server** (`agentctl/server/`): FastAPI server with SQLite persistence, manages VM lifecycle
- **Providers** (`agentctl/providers/`): Abstract VM provider (GCP implementation)

### 2. `agency-quickdeploy` - Standalone one-command launcher (no server needed)
- **CLI** (`agency_quickdeploy/cli.py`): launch, status, logs, stop, list, init
- **Launcher** (`agency_quickdeploy/launcher.py`): Orchestrates resources via providers
- **Providers** (`agency_quickdeploy/providers/`): Abstract provider with GCP and Railway implementations
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

For `agency-quickdeploy` (GCP provider):
- `QUICKDEPLOY_PROJECT` or `GOOGLE_CLOUD_PROJECT`: GCP project ID (required for GCP)
- `QUICKDEPLOY_ZONE`: GCP zone (default: us-central1-a)
- `QUICKDEPLOY_BUCKET`: GCS bucket (auto-generated if not set)
- `QUICKDEPLOY_AUTH_TYPE`: Authentication type (`api_key` or `oauth`)
- `QUICKDEPLOY_PROVIDER`: Deployment provider (`gcp` or `railway`)
- `ANTHROPIC_API_KEY`: API key (for api_key auth)
- `CLAUDE_CODE_OAUTH_TOKEN`: OAuth token (for oauth auth, alternative to Secret Manager)

For `agency-quickdeploy` (Railway provider):
- `RAILWAY_TOKEN`: Railway API token (required for Railway)
- `RAILWAY_PROJECT_ID`: Railway project ID (optional, auto-created if not set)
- `RAILWAY_AGENT_IMAGE`: Custom Docker image for agent (optional)

For `agentctl`:
- `AGENTCTL_MASTER_URL`: Master server URL
- `AGENTCTL_GCP_PROJECT`, `AGENTCTL_GCP_REGION`, `AGENTCTL_GCP_ZONE`

## Usage Examples

### GCP Provider (default)

```bash
# Launch agent with API key (default)
QUICKDEPLOY_PROJECT=my-project agency-quickdeploy launch "Build a todo app"

# Launch agent with OAuth (subscription billing)
QUICKDEPLOY_PROJECT=my-project agency-quickdeploy launch "Build a todo app" --auth-type oauth

# Keep VM running after completion (for debugging)
agency-quickdeploy launch "Build an API" --no-shutdown

# Monitor agent
agency-quickdeploy status agent-20260102-abc123
agency-quickdeploy logs agent-20260102-abc123

# SSH into running agent VM
gcloud compute ssh AGENT_ID --zone=us-central1-a --project=my-project

# Stop an agent
agency-quickdeploy stop agent-20260102-abc123

# List all running agents
agency-quickdeploy list
```

### Railway Provider

```bash
# Launch agent on Railway
RAILWAY_TOKEN=your-token ANTHROPIC_API_KEY=sk-ant... \
  agency-quickdeploy launch "Build a todo app" --provider railway

# Monitor agent
agency-quickdeploy status agent-123 --provider railway
agency-quickdeploy logs agent-123 --provider railway

# Stop an agent
agency-quickdeploy stop agent-123 --provider railway

# List all agents on Railway
agency-quickdeploy list --provider railway
```

## Known Issues

### First-File Creation Bug
The `claude-agent-sdk` with `permission_mode='bypassPermissions'` has trouble creating the FIRST file in a session. Subsequent files work fine.

**Workaround**: Startup script seeds an empty `feature_list.json` so the agent populates it rather than creating from scratch. See `BACKLOG.md` for details.

## Troubleshooting

### Agent stuck on "First session - initializing project..."
This means `feature_list.json` wasn't created. Check:
1. VM is running: `agency-quickdeploy status <agent-id>`
2. SSH in and check logs: `tail -f /var/log/agent.log`
3. Manually create feature_list.json if needed (see BACKLOG.md)

### Can't SSH into VM
```bash
# Check if VM is running
gcloud compute instances list --filter="name~<agent-id>"

# Try with troubleshoot flag
gcloud compute ssh <agent-id> --zone=us-central1-a --troubleshoot
```

### No logs appearing
Logs sync to GCS every 60 seconds. For immediate logs:
```bash
gcloud compute ssh <agent-id> --zone=us-central1-a --command="tail -50 /var/log/agent.log"
```

## For Other Claude Code Agents

When working on this codebase:
1. Run tests after changes: `python -m pytest agency_quickdeploy/ shared/ -v`
2. Check `BACKLOG.md` for known issues and planned work
3. The startup script embeds a Python agent runner - changes there affect all VMs
4. OAuth and API key paths are separate - test both if changing auth

```bash
# Agentctl: Requires running master server
uvicorn agentctl.server.app:app --port 8000
agentctl run "Build a REST API"
agentctl list
agentctl ssh my-agent
```
