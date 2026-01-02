# AgentCtl

> CLI-first system for deploying and managing autonomous AI coding agents on Google Cloud Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

AgentCtl lets you spin up isolated cloud VMs running AI coding agents (Claude Code) that work autonomously on tasks you define. Monitor progress via logs, git commits, screenshots, or SSH directly into the machine.

**Key Features:**
- **Simple CLI** - One command to deploy an agent
- **Git Integration** - Auto-commit and push every 5 minutes
- **Screenshots** - Periodic captures of agent activity
- **SSH Access** - Drop into any agent's terminal
- **Timeouts** - Auto-stop to control costs
- **Cost Efficient** - Spot instance support

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud`)
- A GCP project with billing enabled
- Anthropic API key (for Claude Code)

### Installation

```bash
# Clone and install
git clone https://github.com/yourusername/agentctl
cd agentctl
pip install -e ".[server,dev]"

# Verify installation
agentctl --version
```

### Setup

**Step 1: Install Google Cloud SDK** (if not already installed)
```bash
# macOS
brew install --cask google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

**Step 2: Authenticate**
```bash
gcloud auth login
gcloud auth application-default login
```

**Step 3: Initialize AgentCtl**
```bash
agentctl init
```

That's it! No JSON files or environment variables needed.

<details>
<summary>Alternative: Service Account (for CI/CD)</summary>

```bash
# Set path to service account JSON
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
agentctl init
```
</details>

### Start the Master Server

```bash
# Run locally
uvicorn agentctl.server.app:app --host 0.0.0.0 --port 8000
```

### Usage

```bash
# Start an agent
agentctl run "Build a REST API for a todo app using FastAPI"

# Start with options
agentctl run \
  --name my-api \
  --repo https://github.com/you/myproject \
  --branch feature/new-api \
  --timeout 2h \
  --spot \
  "Add CRUD endpoints for tasks"

# Monitor
agentctl list                    # See all agents
agentctl status my-api           # Detailed status
agentctl logs my-api --follow    # Stream logs
agentctl ssh my-api              # SSH into the VM
agentctl screenshots my-api      # View screenshots

# Send additional instructions
agentctl tell my-api "Also add input validation"

# Stop when done
agentctl stop my-api

# Clean up
agentctl delete my-api
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        YOUR LAPTOP                           │
│   $ agentctl run "Build something awesome"                   │
└──────────────────────────────────┬───────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                      MASTER SERVER                           │
│   REST API • Agent Registry • VM Management • SQLite         │
└──────────────────────────────────┬───────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
     ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
     │   Agent VM   │       │   Agent VM   │       │   Agent VM   │
     │  Claude Code │       │  Claude Code │       │  Claude Code │
     │  + Git repo  │       │  + Git repo  │       │  + Git repo  │
     └──────────────┘       └──────────────┘       └──────────────┘
```

## CLI Reference

### Agent Management

| Command | Description |
|---------|-------------|
| `agentctl run [OPTIONS] PROMPT` | Start a new agent |
| `agentctl list` | List all agents |
| `agentctl status <ID>` | Get agent details |
| `agentctl stop <ID>` | Stop an agent (deletes VM) |
| `agentctl delete <ID>` | Delete agent and all resources |

### Monitoring

| Command | Description |
|---------|-------------|
| `agentctl logs <ID> [-f]` | View/stream agent logs |
| `agentctl ssh <ID> [-c CMD]` | SSH into agent VM |
| `agentctl screenshots <ID> [-d]` | List/download screenshots |

### Communication

| Command | Description |
|---------|-------------|
| `agentctl tell <ID> MSG` | Send instruction to running agent |

### Setup

| Command | Description |
|---------|-------------|
| `agentctl init` | Initialize GCP project |

### Run Options

```
-n, --name TEXT            Agent name (auto-generated if not provided)
-e, --engine [claude]      AI engine (default: claude)
-r, --repo TEXT            Git repository URL to clone
-b, --branch TEXT          Git branch to create/checkout
-t, --timeout TEXT         Auto-stop duration (e.g., 4h, 30m)
-m, --machine TEXT         GCE machine type (default: e2-medium)
--spot                     Use spot/preemptible instance
-f, --prompt-file PATH     Read prompt from file
--screenshot-interval INT  Seconds between screenshots (default: 300)
```

## Configuration

Config file: `~/.agentctl/config.yaml`

```yaml
gcp_project: my-project
gcp_region: us-central1
gcp_zone: us-central1-a
master_server_url: http://localhost:8000
gcs_bucket: my-project-agentctl
default_machine_type: e2-medium
default_timeout: 4h
default_engine: claude
screenshot_interval: 300
screenshot_retention: 24h
```

### Environment Variables

| Variable | Overrides |
|----------|-----------|
| `AGENTCTL_MASTER_URL` | master_server_url |
| `AGENTCTL_GCP_PROJECT` | gcp_project |
| `AGENTCTL_GCP_REGION` | gcp_region |
| `AGENTCTL_GCP_ZONE` | gcp_zone |

## REST API

The master server exposes a REST API:

```
GET  /health                    # Health check
POST /agents                    # Create agent
GET  /agents                    # List agents
GET  /agents/{id}               # Get agent
POST /agents/{id}/stop          # Stop agent
POST /agents/{id}/tell          # Send instruction
DELETE /agents/{id}             # Delete agent
POST /v1/internal/heartbeat     # Agent status updates
```

## Cost Estimates

| Machine Type | Regular | Spot | Use Case |
|--------------|---------|------|----------|
| e2-small | ~$12/mo | ~$4/mo | Light tasks |
| e2-medium | ~$25/mo | ~$8/mo | Standard (default) |
| e2-standard-2 | ~$49/mo | ~$15/mo | Heavy tasks |

*Costs are approximate. Agents auto-stop after timeout.*

## Security

- API keys stored in GCP Secret Manager
- Secrets passed via VM metadata (not fetched from agent)
- Each agent runs in isolated VM
- No credentials in code or logs

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[server,dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=agentctl tests/
```

### Local Development

```bash
# Start server locally
uvicorn agentctl.server.app:app --reload --port 8000

# Use CLI with local server
export AGENTCTL_MASTER_URL=http://127.0.0.1:8000
agentctl list
agentctl run --name test "Hello world"
```

## Project Structure

```
agentctl/
├── agentctl/
│   ├── cli/           # Click commands
│   ├── server/        # FastAPI + SQLite
│   │   ├── routes/    # API endpoints
│   │   └── services/  # GCP services
│   ├── shared/        # Models, config, API client
│   └── engines/       # AI engine adapters
├── tests/
│   ├── unit/          # Fast, no external deps
│   └── integration/   # API tests
└── docs/              # Documentation
```

## Roadmap

- [x] CLI commands (run, list, status, stop, delete, tell, logs, ssh, screenshots)
- [x] FastAPI server with SQLite persistence
- [x] GCP integration (Compute Engine, Secret Manager, Cloud Storage)
- [x] Startup script with auto-commit and screenshots
- [x] Heartbeat system for agent status
- [ ] Web UI dashboard
- [ ] Cost tracking
- [ ] Multi-user support

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [FastAPI](https://fastapi.tiangolo.com/) - API server
- [Google Cloud](https://cloud.google.com/) - Infrastructure
- [Claude Code](https://claude.com/claude-code) - AI coding agent
