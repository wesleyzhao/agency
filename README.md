# AgentCtl

> CLI-first system for deploying and managing autonomous AI coding agents on GCP, AWS, Railway, or locally via Docker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This repository contains **two complementary tools** for running autonomous AI coding agents on **GCP, AWS, Railway, or Docker**:

### 🚀 agency-quickdeploy (Recommended for Getting Started)
**Standalone, zero-infrastructure launcher** - One command to launch an agent. No server needed.

```bash
# Deploy locally (free - no cloud costs!)
agency-quickdeploy launch "Build a Python CLI tool" --provider docker

# Deploy on GCP (full VMs with SSH)
agency-quickdeploy launch "Build a Python CLI tool" --provider gcp

# Deploy on AWS (EC2 + S3)
agency-quickdeploy launch "Build a Python CLI tool" --provider aws

# Deploy on Railway (fast containers)
agency-quickdeploy launch "Build a Python CLI tool" --provider railway
```

**Perfect for:**
- Quick experiments and prototypes
- Single-agent workflows
- Getting started without infrastructure setup
- CI/CD integration

**Supports four deployment providers:**
- **Docker** - Run locally for free, 24/7 agents on your own machine
- **GCP** - Full-size VMs with SSH access, GCS for state
- **AWS** - EC2 instances with S3 for state, spot instances supported
- **Railway** - Lightweight containers, fast startup

### 🏗️ agentctl (Full-Featured)
**Enterprise-ready agent orchestration** with centralized master server, SQLite persistence, and multi-agent management.

```bash
agentctl run "Build a REST API for a todo app"
```

**Perfect for:**
- Managing multiple concurrent agents
- Team collaboration
- Production deployments
- Advanced monitoring and control

---

**Both tools:**
- **Isolated environments** - Each agent runs in its own VM or container
- **SSH Access** - Drop into any agent's terminal (GCP only)
- **Cloud Storage** - Logs and output synced automatically
- **Cost Efficient** - Auto-terminate when done
- **OAuth & API Key** - Support both Claude subscription and pay-per-token billing

## Quick Start

### Prerequisites

- Python 3.11+
- **Anthropic API key** - Get from [console.anthropic.com](https://console.anthropic.com/)
- **Deployment platform** (choose one):
  - **Docker** (local): Docker installed on your machine (easiest, no cloud needed!)
  - **GCP**: Google Cloud SDK + project with billing enabled
  - **AWS**: AWS CLI configured with credentials + S3 bucket
  - **Railway**: Account at [railway.com](https://railway.com) (simpler, faster startup)

### Installation

```bash
# Clone and install
git clone https://github.com/wesleyzhao/agency.git
cd agency
pip install -e ".[dev]"

# For agentctl with server support
pip install -e ".[server,dev]"

# Verify installation
agency-quickdeploy --help
agentctl --version
```

### Quick Start with agency-quickdeploy

**No server setup required!** Choose your platform:

<details open>
<summary><b>🐳 Docker (Easiest - Run Locally for Free!)</b></summary>

```bash
# 1. Set environment variable
export ANTHROPIC_API_KEY=sk-ant-...  # Get from console.anthropic.com

# 2. Initialize (pulls the agent image)
agency-quickdeploy init --provider docker

# 3. Launch an agent
agency-quickdeploy launch "Build a Python calculator CLI" --provider docker

# 4. Monitor and interact
agency-quickdeploy status <agent-id> --provider docker
agency-quickdeploy logs <agent-id> --provider docker
docker exec -it <agent-id> bash  # Shell into container

# 5. Stop when done
agency-quickdeploy stop <agent-id> --provider docker
```

</details>

<details>
<summary><b>🚂 Railway (Fast Containers)</b></summary>

```bash
# 1. Set environment variables
export RAILWAY_TOKEN=your-token      # Get from railway.com/account/tokens
export ANTHROPIC_API_KEY=sk-ant-...  # Get from console.anthropic.com

# 2. Verify setup
agency-quickdeploy init --provider railway

# 3. Launch an agent
agency-quickdeploy launch "Build a Python calculator CLI" --provider railway

# 4. Monitor and stop
agency-quickdeploy status <agent-id> --provider railway
agency-quickdeploy logs <agent-id> --provider railway
agency-quickdeploy stop <agent-id> --provider railway
```

</details>

<details>
<summary><b>☁️ GCP (Full-featured with SSH access)</b></summary>

```bash
# 1. Set environment variables
export QUICKDEPLOY_PROJECT=your-gcp-project
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Authenticate with GCP
gcloud auth login
gcloud auth application-default login

# 3. Launch an agent
agency-quickdeploy launch "Build a Python calculator CLI"

# 4. Monitor and stop
agency-quickdeploy status <agent-id>
agency-quickdeploy logs <agent-id>
agency-quickdeploy stop <agent-id>

# SSH into running agent (GCP only)
gcloud compute ssh <agent-id> --zone=us-central1-a
```

</details>

<details>
<summary><b>☁️ AWS (EC2 + S3)</b></summary>

```bash
# 1. Set environment variables
export AWS_REGION=us-east-1              # Or your preferred region
export AWS_BUCKET=my-agency-bucket       # For state storage (optional, auto-created)
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Configure AWS credentials (if not already done)
aws configure

# 3. Launch an agent
agency-quickdeploy launch "Build a Python calculator CLI" --provider aws

# 4. Use spot instances to save money
agency-quickdeploy launch "Build an API" --provider aws --spot

# 5. Monitor and stop
agency-quickdeploy status <agent-id> --provider aws
agency-quickdeploy logs <agent-id> --provider aws
agency-quickdeploy stop <agent-id> --provider aws
```

</details>

See the [agency-quickdeploy documentation](#agency-quickdeploy-reference) below for full details.

---

### Full Setup with agentctl (Advanced)

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

### Test Deploy (Standalone)

For quick testing without the master server:

```bash
# Deploy agent, wait for output, then cleanup VM
python scripts/test_gcp_deploy.py \
  --prompt "Create a Python calculator with tests" \
  --wait \
  --cleanup \
  --output-dir ./my-output

# Deploy with SSH inspection (VM stays running)
python scripts/test_gcp_deploy.py \
  --prompt "Build something" \
  --no-shutdown

# After completion, SSH in:
gcloud compute ssh agent-test-XXXXX --zone=us-central1-a
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

---

## agency-quickdeploy Reference

### Commands

| Command | Description |
|---------|-------------|
| `agency-quickdeploy launch PROMPT [OPTIONS]` | Launch a new agent |
| `agency-quickdeploy status <ID> [--provider]` | Get agent status |
| `agency-quickdeploy logs <ID> [--provider]` | View agent logs |
| `agency-quickdeploy stop <ID> [--provider]` | Stop agent and delete VM/service |
| `agency-quickdeploy list [--provider]` | List all running agents |
| `agency-quickdeploy init [--provider]` | Check configuration |

### Launch Options

```
--provider [gcp|railway]      Deployment provider (default: gcp)
--auth-type [api_key|oauth]   Authentication method (default: api_key)
--no-shutdown                 Keep running after completion (GCP only)
--name TEXT                   Custom agent name
--repo TEXT                   Git repository to clone
--branch TEXT                 Git branch to use
--spot                        Use spot/preemptible instance (GCP only)
--max-iterations INT          Max agent iterations (0=unlimited)
```

### Environment Variables

See `.env.example` for all options. Key variables:

#### GCP Provider (default)

| Variable | Required | Description |
|----------|----------|-------------|
| `QUICKDEPLOY_PROJECT` | **Yes** | GCP project ID |
| `ANTHROPIC_API_KEY` | **Yes*** | API key (if using api_key auth) |
| `CLAUDE_CODE_OAUTH_TOKEN` | **Yes*** | OAuth token (if using oauth auth) |
| `QUICKDEPLOY_ZONE` | No | GCP zone (default: us-central1-a) |
| `QUICKDEPLOY_BUCKET` | No | GCS bucket (auto-generated if not set) |
| `QUICKDEPLOY_AUTH_TYPE` | No | Auth type: api_key or oauth |

*One of ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN required

#### Railway Provider

| Variable | Required | Description |
|----------|----------|-------------|
| `RAILWAY_TOKEN` | **Yes** | Railway API token (get from [railway.com/account/tokens](https://railway.com/account/tokens)) |
| `ANTHROPIC_API_KEY` | **Yes*** | API key (if using api_key auth) |
| `CLAUDE_CODE_OAUTH_TOKEN` | **Yes*** | OAuth token (if using oauth auth) |
| `RAILWAY_PROJECT_ID` | No | Use existing Railway project (creates new if not set) |
| `RAILWAY_AGENT_REPO` | No | Custom agent runner repo (default: this repo) |
| `QUICKDEPLOY_PROVIDER` | No | Default provider: gcp or railway |

*One of ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN required

### Authentication Methods

**API Key (default):**
```bash
# Set in .env
ANTHROPIC_API_KEY=sk-ant-api03-...

# Launch
agency-quickdeploy launch "Build something"
```

**OAuth Token (subscription):**
```bash
# Generate token (requires browser)
claude setup-token
# Outputs: sk-ant-oat01-...

# Store in Secret Manager (GCP)
echo '{"claudeAiOauth":{"accessToken":"sk-ant-oat01-YOUR-TOKEN"}}' | \
  gcloud secrets create claude-oauth-credentials --data-file=-

# Or set in .env
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...

# Launch with OAuth
agency-quickdeploy launch "Build something" --auth-type oauth
```

### Railway Details

**How Railway deployment works:**
- Railway clones this repo and builds from `agent-runner/` directory
- Uses Nixpacks to auto-detect and install Python + Node.js
- Agent runner starts and processes your prompt
- No Docker needed - pure GitHub repo deployment

**Railway vs GCP:**
| Feature | GCP | Railway |
|---------|-----|---------|
| Startup time | ~2-3 min | ~30 sec |
| SSH access | Yes | No |
| Persistent storage | GCS | Railway Volumes |
| Spot instances | Yes | No |
| Cost model | Per-minute VM | Per-usage container |

### How It Works

1. **Launch**: Creates GCP VM with startup script
2. **Initialize**: First agent session creates `feature_list.json` with implementation plan
3. **Execute**: Subsequent sessions implement features one-by-one
4. **Sync**: Logs and workspace sync to GCS every 60 seconds
5. **Complete**: VM auto-terminates (unless `--no-shutdown`)

### Troubleshooting

**Agent stuck on "First session - initializing..."**
- SSH in: `gcloud compute ssh <agent-id> --zone=us-central1-a`
- Check logs: `tail -f /var/log/agent.log`
- Check if `feature_list.json` was created

**Can't SSH into VM**
```bash
gcloud compute instances list --filter="name~<agent-id>"
gcloud compute ssh <agent-id> --zone=us-central1-a --troubleshoot
```

**No logs appearing**
Logs sync every 60 seconds. For immediate logs:
```bash
gcloud compute ssh <agent-id> --zone=us-central1-a \
  --command="tail -50 /var/log/agent.log"
```

See [CLAUDE.md](CLAUDE.md) for complete documentation and [BACKLOG.md](BACKLOG.md) for known issues.

---

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

# Run all tests (135 tests across both tools)
pytest -v

# Run agency-quickdeploy tests only
pytest agency_quickdeploy/tests/ shared/harness/tests/ -v

# Run agentctl tests only
pytest tests/ -v

# Run with coverage
pytest --cov=agency_quickdeploy --cov=agentctl --cov=shared tests/ agency_quickdeploy/ shared/
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
.
├── agency_quickdeploy/      # Standalone launcher (no server)
│   ├── cli.py               # CLI commands
│   ├── launcher.py          # Main orchestration
│   ├── auth.py              # API key & OAuth handling
│   ├── config.py            # Configuration
│   ├── providers/           # Deployment providers
│   │   ├── base.py          # Abstract base provider
│   │   ├── gcp.py           # GCP Compute Engine provider
│   │   └── railway.py       # Railway container provider
│   ├── gcp/                 # GCP-specific integrations
│   │   ├── vm.py            # Compute Engine
│   │   ├── storage.py       # Cloud Storage
│   │   └── secrets.py       # Secret Manager
│   └── tests/               # Unit tests
├── agentctl/                # Full-featured with server
│   ├── cli/                 # Click commands
│   ├── server/              # FastAPI + SQLite
│   │   ├── routes/          # API endpoints
│   │   └── services/        # GCP services
│   ├── shared/              # Models, config, API client
│   └── engines/             # AI engine adapters
├── shared/                  # Shared by both tools
│   └── harness/             # Agent runtime components
│       ├── startup_template.py  # VM startup script generator
│       ├── agent_loop.py        # Agent execution logic
│       └── tests/               # Unit tests
├── tests/                   # agentctl tests
│   ├── unit/
│   └── integration/
└── docs/                    # Documentation
```

## Roadmap

- [x] CLI commands (run, list, status, stop, delete, tell, logs, ssh, screenshots)
- [x] FastAPI server with SQLite persistence
- [x] GCP integration (Compute Engine, Secret Manager, Cloud Storage)
- [x] Startup script with auto-commit and screenshots
- [x] Heartbeat system for agent status
- [x] Workspace sync to GCS
- [x] Output download after completion
- [x] SSH inspection mode (--no-shutdown)
- [x] **Railway provider (container-based deployment)**
- [ ] Web UI dashboard
- [ ] Cost tracking
- [ ] Multi-user support
- [ ] Pre-baked VM images (faster startup)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [FastAPI](https://fastapi.tiangolo.com/) - API server
- [Google Cloud](https://cloud.google.com/) - Infrastructure
- [Claude Code](https://claude.com/claude-code) - AI coding agent
