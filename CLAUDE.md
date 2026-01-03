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

## Environment Variables

For `agency-quickdeploy`:
- `QUICKDEPLOY_PROJECT` or `GOOGLE_CLOUD_PROJECT`: GCP project ID (required)
- `QUICKDEPLOY_ZONE`: GCP zone (default: us-central1-a)
- `QUICKDEPLOY_BUCKET`: GCS bucket (auto-generated if not set)

For `agentctl`:
- `AGENTCTL_MASTER_URL`: Master server URL
- `AGENTCTL_GCP_PROJECT`, `AGENTCTL_GCP_REGION`, `AGENTCTL_GCP_ZONE`

## Usage Examples

```bash
# QuickDeploy: Launch agent without a server
QUICKDEPLOY_PROJECT=my-project agency-quickdeploy launch "Build a todo app"
agency-quickdeploy status agent-20260102-abc123
agency-quickdeploy logs agent-20260102-abc123

# Agentctl: Requires running master server
uvicorn agentctl.server.app:app --port 8000
agentctl run "Build a REST API"
agentctl list
agentctl ssh my-agent
```
