# AgentCtl

> CLI-first system for deploying and managing autonomous AI coding agents on Google Cloud Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

AgentCtl lets you spin up isolated cloud VMs running AI coding agents (Claude Code, Codex) that work autonomously on tasks you define. Monitor progress via logs, git commits, screenshots, or SSH directly into the machine.

**Key Features:**
- 🚀 **Simple CLI** - One command to deploy an agent
- 🔄 **Git Integration** - Auto-commit and push to your repos
- 📸 **Screenshots** - Periodic captures of agent activity
- 💻 **SSH Access** - Drop into any agent's terminal
- ⏰ **Timeouts** - Auto-stop to control costs
- 💰 **Cost Efficient** - Spot instance support

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud`)
- A GCP project with billing enabled
- Anthropic API key (for Claude Code)

### Installation

```bash
pip install agentctl
```

### Setup

```bash
# Initialize AgentCtl (creates GCP resources, prompts for API keys)
agentctl init
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
agentctl logs my-api --follow    # Stream logs
agentctl ssh my-api              # SSH into the VM
agentctl screenshots my-api      # View screenshots

# Send additional instructions
agentctl tell my-api "Also add input validation"

# Stop when done
agentctl stop my-api
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        YOUR LAPTOP                            │
│   $ agentctl run "Build something awesome"                   │
└──────────────────────────────────┬───────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                      MASTER SERVER (GCP)                      │
│   REST API • Agent Registry • VM Management                   │
└──────────────────────────────────┬───────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
     ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
     │   Agent VM   │       │   Agent VM   │       │   Agent VM   │
     │  Claude Code │       │    Codex     │       │  Claude Code │
     │  + Git repo  │       │  + Git repo  │       │  + Git repo  │
     └──────────────┘       └──────────────┘       └──────────────┘
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `agentctl init` | Initialize GCP project |
| `agentctl run [PROMPT]` | Start a new agent |
| `agentctl list` | List all agents |
| `agentctl status <ID>` | Get agent details |
| `agentctl logs <ID>` | View agent logs |
| `agentctl ssh <ID>` | SSH into agent VM |
| `agentctl tell <ID> <MSG>` | Send instruction to agent |
| `agentctl stop <ID>` | Stop an agent |
| `agentctl delete <ID>` | Delete an agent |
| `agentctl screenshots <ID>` | View/download screenshots |
| `agentctl git <ID> <CMD>` | Git operations |
| `agentctl secrets <CMD>` | Manage API keys |
| `agentctl cost` | View cost estimate |

See [COMMANDS.md](docs/COMMANDS.md) for full documentation.

## Configuration

Config file: `~/.agentctl/config.yaml`

```yaml
gcp_project: my-project
gcp_region: us-central1
gcp_zone: us-central1-a
master_server_url: http://X.X.X.X:8080
default_timeout: 4h
default_engine: claude
screenshot_interval: 300    # seconds, 0 to disable
screenshot_retention: 24h   # or "7d", "all"
```

## Cost Estimates

| Machine Type | Regular | Spot | Use Case |
|--------------|---------|------|----------|
| e2-small | $12/mo | $4/mo | Light tasks |
| e2-medium | $25/mo | $8/mo | Standard (default) |
| e2-standard-2 | $49/mo | $15/mo | Heavy tasks |

*Costs are approximate. Agents auto-stop after timeout.*

## Security

- API keys stored in GCP Secret Manager
- Each agent runs in isolated VM
- Service accounts with minimal permissions
- No credentials in code or logs

## Development

```bash
# Clone repo
git clone https://github.com/yourusername/agentctl
cd agentctl

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start server locally
uvicorn agentctl.server.app:app --reload
```

## Documentation

- [Product Requirements](docs/PRD.md)
- [Technical Specification](docs/TECHNICAL_SPEC.md)
- [CLI Commands](docs/COMMANDS.md)
- [REST API](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)

## Roadmap

- [x] Basic agent lifecycle
- [x] Git integration
- [x] Screenshot capture
- [x] Multiple engine support (Claude, Codex)
- [ ] Web UI dashboard
- [ ] Task queuing
- [ ] Auto-PR creation
- [ ] Multi-user support

## Contributing

Contributions welcome! Please read the implementation plan before starting.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [FastAPI](https://fastapi.tiangolo.com/) - API server
- [Google Cloud](https://cloud.google.com/) - Infrastructure
- [Claude Code](https://anthropic.com/) - AI coding agent
