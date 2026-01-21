# Agency

> Deploy autonomous AI coding agents on GCP, AWS, Railway, or locally via Docker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**One command to launch an AI agent that writes code for you:**

```bash
agency-quickdeploy launch "Build a Python CLI that converts CSV to JSON"
```

The agent runs autonomously in a VM or container, writing code until the task is complete.

---

## Choose Your Path

### I want to try it locally (free, no cloud)

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-api03-...  # Get from console.anthropic.com
agency-quickdeploy launch "Build a calculator CLI" --provider docker
```

### I want cloud VMs with SSH access

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-api03-...
export QUICKDEPLOY_PROJECT=my-gcp-project   # GCP project ID
gcloud auth application-default login
agency-quickdeploy launch "Build a REST API"
```

### I want to use my Claude subscription (not pay-per-token)

```bash
# Generate OAuth token (one-time, requires browser)
claude setup-token
# Returns: sk-ant-oat01-...

export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-YOUR-TOKEN
agency-quickdeploy launch "Build an app" --auth-type oauth --provider docker
```

---

## Quick Start by Provider

<details open>
<summary><h3>Docker (Local, Free)</h3></summary>

Run agents on your own machine. No cloud costs.

```bash
# Prerequisites: Docker installed

# 1. Install
pip install -e .

# 2. Set API key
export ANTHROPIC_API_KEY=sk-ant-api03-...

# 3. Initialize (pulls agent image)
agency-quickdeploy init --provider docker

# 4. Launch
agency-quickdeploy launch "Build a todo app with SQLite" --provider docker

# 5. Monitor
agency-quickdeploy status <agent-id> --provider docker
agency-quickdeploy logs <agent-id> --provider docker
docker exec -it <agent-id> bash    # Shell into container

# 6. Stop
agency-quickdeploy stop <agent-id> --provider docker
```

</details>

<details>
<summary><h3>GCP (Full VMs with SSH)</h3></summary>

Full Linux VMs with SSH access and GCS storage.

```bash
# Prerequisites: gcloud CLI installed

# 1. Install
pip install -e .

# 2. Configure
export ANTHROPIC_API_KEY=sk-ant-api03-...
export QUICKDEPLOY_PROJECT=your-gcp-project

# 3. Authenticate
gcloud auth login
gcloud auth application-default login

# 4. Launch
agency-quickdeploy launch "Build a REST API with FastAPI"

# 5. Monitor
agency-quickdeploy status <agent-id>
agency-quickdeploy logs <agent-id>
gcloud compute ssh <agent-id> --zone=us-central1-a    # SSH in

# 6. Stop
agency-quickdeploy stop <agent-id>

# Pro tip: Use spot instances for 60-90% cost savings
agency-quickdeploy launch "Build something" --spot
```

</details>

<details>
<summary><h3>AWS (EC2 + S3)</h3></summary>

EC2 instances with S3 storage.

```bash
# Prerequisites: AWS CLI configured

# 1. Install
pip install -e .

# 2. Configure
export ANTHROPIC_API_KEY=sk-ant-api03-...
export AWS_REGION=us-east-1

# 3. Launch
agency-quickdeploy launch "Build a Lambda function" --provider aws

# 4. Monitor
agency-quickdeploy status <agent-id> --provider aws
agency-quickdeploy logs <agent-id> --provider aws

# 5. Stop
agency-quickdeploy stop <agent-id> --provider aws

# Pro tip: Use spot instances
agency-quickdeploy launch "Build something" --provider aws --spot
```

</details>

<details>
<summary><h3>Railway (Fast Containers)</h3></summary>

Lightweight containers with fast startup.

```bash
# Prerequisites: Railway account

# 1. Install
pip install -e .

# 2. Configure
export ANTHROPIC_API_KEY=sk-ant-api03-...
export RAILWAY_TOKEN=...    # Get from railway.com/account/tokens

# 3. Launch
agency-quickdeploy launch "Build a Discord bot" --provider railway

# 4. Monitor
agency-quickdeploy status <agent-id> --provider railway
agency-quickdeploy logs <agent-id> --provider railway

# 5. Stop
agency-quickdeploy stop <agent-id> --provider railway
```

</details>

---

## Provider Comparison

| | Docker | GCP | AWS | Railway |
|---|--------|-----|-----|---------|
| **Cost** | Free | ~$0.02/hr | ~$0.02/hr | Per-usage |
| **Startup** | ~5s | ~2-3 min | ~2-3 min | ~30s |
| **SSH** | `docker exec` | Yes | Via key | No |
| **Spot/Preemptible** | N/A | Yes | Yes | No |
| **Best for** | Development | Production | AWS users | Quick tests |

---

## Using Your Claude Subscription (OAuth)

Instead of paying per-token with an API key, use your Claude Code subscription:

### Step 1: Generate Token

```bash
# On a machine with a browser
claude setup-token
# Opens browser, you authenticate
# Returns: sk-ant-oat01-...
```

### Step 2: Use Token

**Simple (Environment Variable):**
```bash
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-YOUR-TOKEN
agency-quickdeploy launch "Build an app" --auth-type oauth --provider docker
```

**GCP Secret Manager (More Secure):**
```bash
# Store token
echo '{"claudeAiOauth":{"accessToken":"sk-ant-oat01-YOUR-TOKEN"}}' | \
    gcloud secrets create claude-oauth-credentials --data-file=-

# Launch (reads from Secret Manager automatically)
agency-quickdeploy launch "Build an app" --auth-type oauth
```

---

## CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `launch "PROMPT"` | Start a new agent |
| `status <id>` | Check agent status |
| `logs <id>` | View agent logs |
| `list` | List all agents |
| `stop <id>` | Stop and delete agent |
| `init` | Verify configuration |

### Common Options

```bash
agency-quickdeploy launch "PROMPT" [OPTIONS]

  -p, --provider [gcp|aws|docker|railway]   # Deployment target (default: gcp)
  -a, --auth-type [api_key|oauth]           # Authentication (default: api_key)
  -n, --name TEXT                           # Custom agent name
  -r, --repo URL                            # Git repo to clone
  -b, --branch NAME                         # Git branch
  --spot                                    # Use spot instances (GCP/AWS)
  --shutdown                                # Auto-shutdown on completion (default: stays running)
  -m, --max-iterations N                    # Limit iterations (0=unlimited)
```

---

## Environment Variables

### Required

| Variable | Provider | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | All | API key (for pay-per-token) |
| `CLAUDE_CODE_OAUTH_TOKEN` | All | OAuth token (for subscription) |
| `QUICKDEPLOY_PROJECT` | GCP | GCP project ID |
| `RAILWAY_TOKEN` | Railway | Railway API token |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKDEPLOY_PROVIDER` | `gcp` | Default provider |
| `QUICKDEPLOY_ZONE` | `us-central1-a` | GCP zone |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AGENCY_DATA_DIR` | `~/.agency` | Docker data directory |

---

## How It Works

1. **Launch**: Creates a VM/container with your prompt
2. **Initialize**: Agent creates `feature_list.json` breaking down the task
3. **Execute**: Agent implements features one-by-one across sessions
4. **Sync**: Logs and code sync to cloud storage
5. **Complete**: VM/container terminates (or stays up with `--no-shutdown`)

Based on Anthropic's [autonomous-coding pattern](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding).

---

## agentctl (Advanced)

For managing multiple agents with a central server:

```bash
# Install with server support
pip install -e ".[server]"

# Start master server
uvicorn agentctl.server.app:app --port 8000

# For development (auto-reload on changes)
uvicorn agentctl.server.app:app --reload --port 8000

# Point CLI to server
export AGENTCTL_MASTER_URL=http://localhost:8000

# Use CLI
agentctl run "Build an API"
agentctl list
agentctl ssh my-agent
agentctl logs my-agent --follow
agentctl tell my-agent "Also add tests"
```

See [CLAUDE.md](CLAUDE.md) for full agentctl documentation.

---

## Troubleshooting

### Agent stuck initializing

```bash
# Check status
agency-quickdeploy status <agent-id>

# View logs
agency-quickdeploy logs <agent-id>

# SSH in (GCP)
gcloud compute ssh <agent-id> --zone=us-central1-a
tail -f /var/log/agent.log
```

### No logs appearing

Logs sync every 60 seconds. For immediate logs:

```bash
# GCP
gcloud compute ssh <agent-id> --command="tail -50 /var/log/agent.log"

# Docker
docker logs <agent-id>
```

### OAuth not working

1. Token must start with `sk-ant-oat` (not `sk-ant-api`)
2. Use `--auth-type oauth` flag
3. For GCP, ensure Secret Manager permissions are set

---

## Development

```bash
# Install dev dependencies
pip install -e ".[server,dev]"

# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=agency_quickdeploy --cov=agentctl
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](CLAUDE.md) | Technical reference (for developers & AI agents) |
| [BACKLOG.md](BACKLOG.md) | Known issues and planned work |
| [docs/deployment/](docs/deployment/) | Detailed deployment guides |
| [docs/api/API.md](docs/api/API.md) | REST API reference |

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Links

- [Anthropic Console](https://console.anthropic.com/) - Get API key
- [Claude Code](https://claude.ai/code) - Generate OAuth token with `claude setup-token`
- [Railway](https://railway.com/account/tokens) - Get Railway token
