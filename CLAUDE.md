# CLAUDE.md

Comprehensive reference for developers and Claude Code agents working on this codebase.

## Quick Start for AI Agents

```bash
# Install and test
pip install -e ".[server,dev]"
python -m pytest                    # Run all 164+ tests

# Key files to understand
agency_quickdeploy/cli.py          # Main CLI entry point
agency_quickdeploy/launcher.py     # Core orchestration logic
agency_quickdeploy/providers/      # Provider implementations (GCP, AWS, Docker, Railway)
shared/harness/startup_template.py # VM startup script generator
agent-runner/main.py               # Docker container entry point
```

**Before making changes:**
1. Read `BACKLOG.md` for known issues and current work
2. Run tests after changes: `python -m pytest -v`
3. Test both auth methods (api_key and oauth) if changing auth code

---

## Which Tool Should I Use?

This repo has **two CLI tools**. Choose based on your needs:

| Need | Use | Why |
|------|-----|-----|
| Quick experiments | `agency-quickdeploy` | Zero setup, one command |
| Local development (free) | `agency-quickdeploy --provider docker` | No cloud costs |
| CI/CD automation | `agency-quickdeploy` | Stateless, scriptable |
| Multiple concurrent agents | `agentctl` | Master server manages state |
| Team/production use | `agentctl` | Centralized control |
| SSH into agents | Either (GCP provider) | Both support GCP VMs |

**TL;DR:** Start with `agency-quickdeploy`. Use `agentctl` when you need a master server.

---

## Project Architecture

```
agency/
├── agency_quickdeploy/        # Standalone launcher (NO server needed)
│   ├── cli.py                 # Click CLI: launch, status, logs, stop, list, init
│   ├── launcher.py            # QuickDeployLauncher - main orchestration
│   ├── auth.py                # Credentials: API key & OAuth handling
│   ├── config.py              # QuickDeployConfig dataclass
│   └── providers/
│       ├── base.py            # AbstractProvider interface
│       ├── gcp.py             # GCP Compute Engine
│       ├── aws.py             # AWS EC2
│       ├── docker.py          # Local Docker containers
│       └── railway.py         # Railway containers
│
├── agentctl/                  # Full-featured (REQUIRES master server)
│   ├── cli/                   # Click commands: run, list, status, stop, ssh, logs, etc.
│   ├── server/                # FastAPI server with SQLite
│   │   ├── app.py             # Main FastAPI app
│   │   ├── routes/            # API endpoints
│   │   └── services/          # GCP services
│   └── shared/                # Models, config, API client
│
├── agent-runner/              # Docker image for containerized providers
│   ├── main.py                # Entry point for Docker/Railway agents
│   └── Dockerfile             # Builds ghcr.io/wesleyzhao/agency-agent:latest
│
├── shared/harness/            # Shared agent runtime
│   ├── startup_template.py    # Generates VM startup scripts
│   └── agent_loop.py          # Feature list parsing, prompt generation
│
└── scripts/                   # Development & CI scripts
    ├── ci_test.py             # Integration testing
    └── test_gcp_deploy.py     # Manual deployment testing
```

### Key Design Patterns

1. **Two-Agent Architecture**: Initializer agent creates `feature_list.json`, then coding agents implement features one-by-one. Based on Anthropic's [autonomous-coding pattern](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding).

2. **Cloud Storage State**: Agent status, logs, and progress sync to cloud storage (`gs://` for GCP, `s3://` for AWS, `~/.agency/` for Docker). No server needed for agency-quickdeploy.

3. **Secure Credential Passing**:
   - **GCP**: Secrets via VM instance metadata (not env vars in startup script)
   - **AWS/Docker/Railway**: Secrets via environment variables

---

## Complete CLI Reference

### agency-quickdeploy Commands

#### `launch` - Start a new agent
```bash
agency-quickdeploy launch "PROMPT" [OPTIONS]

Options:
  -n, --name TEXT               Custom agent name (auto-generated if omitted)
  -r, --repo TEXT               Git repository URL to clone
  -b, --branch TEXT             Git branch to use
  -p, --provider [gcp|aws|docker|railway]  Deployment provider (default: gcp)
  -a, --auth-type [api_key|oauth]          Authentication method (default: api_key)
  -m, --max-iterations INT      Max iterations, 0=unlimited (default: 0)
  --spot                        Use spot/preemptible instance (GCP/AWS only)
  --shutdown / --no-shutdown    Auto-shutdown on completion (default: --no-shutdown, keeps running)
```

#### `status` - Get agent status
```bash
agency-quickdeploy status AGENT_ID [-p PROVIDER]
```

#### `logs` - View agent logs
```bash
agency-quickdeploy logs AGENT_ID [-p PROVIDER] [-f/--follow]
```

#### `stop` - Stop and delete agent
```bash
agency-quickdeploy stop AGENT_ID [-p PROVIDER]
```

#### `list` - List all agents
```bash
agency-quickdeploy list [-p PROVIDER]
```

#### `init` - Verify configuration
```bash
agency-quickdeploy init [-p PROVIDER]
```

### agentctl Commands (requires master server)

**Start the master server first:**
```bash
# Production mode
uvicorn agentctl.server.app:app --host 0.0.0.0 --port 8000

# Development mode (auto-reload on code changes)
uvicorn agentctl.server.app:app --reload --port 8000

# Set the server URL for CLI
export AGENTCTL_MASTER_URL=http://localhost:8000
```

**Then use the CLI:**
```bash
# Core commands
agentctl run "PROMPT" [OPTIONS]     # Start agent
agentctl list [-s STATUS] [-o FORMAT]
agentctl status AGENT_ID
agentctl stop AGENT_ID [-f]
agentctl delete AGENT_ID [-f]

# Monitoring
agentctl logs AGENT_ID [-f] [-n LINES]
agentctl ssh AGENT_ID [-c COMMAND]
agentctl screenshots AGENT_ID [-d] [-o DIR] [-n LIMIT]

# Communication
agentctl tell AGENT_ID "INSTRUCTION"

# Setup
agentctl init [OPTIONS]
```

---

## Environment Variables (Single Source of Truth)

### Common (All Providers)

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKDEPLOY_PROVIDER` | `gcp` | Provider: `gcp`, `aws`, `docker`, `railway` |
| `QUICKDEPLOY_AUTH_TYPE` | `api_key` | Auth: `api_key` or `oauth` |
| `ANTHROPIC_API_KEY` | - | **Required** for api_key auth |
| `CLAUDE_CODE_OAUTH_TOKEN` | - | **Required** for oauth auth (token only) |

### GCP Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKDEPLOY_PROJECT` | - | **Required**: GCP project ID |
| `GOOGLE_CLOUD_PROJECT` | - | Fallback for project ID |
| `QUICKDEPLOY_ZONE` | `us-central1-a` | GCP zone |
| `QUICKDEPLOY_BUCKET` | auto | GCS bucket (auto-created if not set) |
| `QUICKDEPLOY_MACHINE_TYPE` | `e2-medium` | GCE machine type |

### AWS Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_BUCKET` | auto | S3 bucket (auto-created) |
| `AWS_INSTANCE_TYPE` | `t3.medium` | EC2 instance type |
| Standard AWS credentials (`AWS_ACCESS_KEY_ID`, etc.) | | |

**Supported regions**: us-east-1, us-east-2, us-west-1, us-west-2, eu-west-1, eu-west-2, eu-central-1, ap-northeast-1, ap-southeast-1, ap-southeast-2

### Docker Provider (Local)

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENCY_DATA_DIR` | `~/.agency` | Local data directory |
| `AGENCY_DOCKER_IMAGE` | `ghcr.io/wesleyzhao/agency-agent:latest` | Agent image |

### Railway Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `RAILWAY_TOKEN` | - | **Required**: Railway API token (UUID format from railway.com/account/tokens) |
| `RAILWAY_PROJECT_ID` | auto | Railway project (auto-created if not set) |
| `RAILWAY_WORKSPACE_ID` | auto | Workspace (auto-detected from token) |
| `RAILWAY_AGENT_IMAGE` | `ghcr.io/wesleyzhao/agency-agent:latest` | Custom agent Docker image |
| `RAILWAY_AGENT_REPO` | - | Optional: GitHub repo URL for deployment (uses Docker image if not set) |

### agentctl-specific

| Variable | Description |
|----------|-------------|
| `AGENTCTL_MASTER_URL` | Master server URL |
| `AGENTCTL_GCP_PROJECT` | Override GCP project |
| `AGENTCTL_GCP_REGION` | Override GCP region |
| `AGENTCTL_GCP_ZONE` | Override GCP zone |

---

## Authentication Deep Dive

### API Key (Default - Pay Per Token)

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Launch (api_key is default)
agency-quickdeploy launch "Build an app"
```

**Token prefix**: `sk-ant-api`
**Billing**: Per-token usage

### OAuth Token (Subscription Billing)

Use your Claude Code subscription instead of per-token billing.

#### Step 1: Generate OAuth Token

```bash
# On a machine with a browser
claude setup-token
# Browser opens, you authenticate
# Returns: sk-ant-oat01-...
```

This is the Claude Code CLI command that generates an OAuth token from your subscription.

#### Step 2: Use the Token

**Option A: Environment Variable (Simplest)**
```bash
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-YOUR-TOKEN
agency-quickdeploy launch "Build an app" --auth-type oauth --provider docker
```

**Option B: GCP Secret Manager (For GCP provider)**
```bash
# Store as JSON (required format)
echo '{"claudeAiOauth":{"accessToken":"sk-ant-oat01-YOUR-TOKEN"}}' | \
    gcloud secrets create claude-oauth-credentials --data-file=-

# Grant VM access to the secret
gcloud secrets add-iam-policy-binding claude-oauth-credentials \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Launch
agency-quickdeploy launch "Build an app" --auth-type oauth
```

**Token prefix**: `sk-ant-oat`
**Billing**: Uses your Claude Code subscription

#### OAuth JSON Format

When storing in Secret Manager, use this structure:
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",   // Optional
    "expiresAt": 1748658860401,            // Optional: Unix timestamp
    "scopes": ["user:inference", "user:profile"]  // Optional
  }
}
```

---

## Provider Comparison

| Feature | Docker | Railway | GCP | AWS |
|---------|--------|---------|-----|-----|
| **Cost** | Free (local) | Per-usage | Per-minute VM | Per-minute VM |
| **Startup time** | ~5 sec | ~30 sec | ~2-3 min | ~2-3 min |
| **SSH access** | `docker exec` | No | Yes | Via SSH key |
| **Spot instances** | N/A | No | Yes | Yes |
| **Persistent storage** | Local | Railway Volumes | GCS | S3 |
| **Max runtime** | Unlimited | Platform limits | Unlimited | Unlimited |
| **Best for** | Development | Quick deploys | Production | AWS shops |

### Provider-Specific Notes

**Docker**: No cloud costs. Agent data stored in `~/.agency/agents/{id}/`. Access container with `docker exec -it AGENT_ID bash`.

**Railway**: Requires `RAILWAY_TOKEN` from railway.com/account/tokens. Auto-creates projects. Fast startup but no SSH.

**GCP**: Full VM with SSH. Use `--spot` for 60-91% cost savings. Logs sync to GCS every 60 seconds.

**AWS**: EC2 instances. SSH keys auto-generated and stored locally. Use `--spot` for cost savings. **Note**: AWS provider has less testing than GCP.

---

## Testing

### Unit Tests
```bash
# All tests
python -m pytest

# Specific test file
python -m pytest tests/unit/test_config.py

# With coverage
python -m pytest --cov=agentctl --cov=agency_quickdeploy tests/
```

### Integration Tests (CI)

Run these for significant changes to deployment code:

```bash
# Level 1: Build/test on fresh VM (~45s)
python scripts/ci_test.py --level 1

# Level 2: Agent launch verification (~70s)
python scripts/ci_test.py --level 2

# Level 3: Full task completion (~5-10 min)
python scripts/ci_test.py --level 3

# Use local uncommitted code
python scripts/ci_test.py --level 1 --source local

# Keep VM for debugging
python scripts/ci_test.py --level 2 --no-cleanup
```

---

## Troubleshooting

### Agent stuck on "First session - initializing project..."

The `feature_list.json` wasn't created (known first-file bug).

```bash
# Check agent status
agency-quickdeploy status AGENT_ID

# SSH in (GCP)
gcloud compute ssh AGENT_ID --zone=us-central1-a

# Check logs
tail -f /var/log/agent.log

# Manually seed feature_list.json if needed
echo '[]' > /workspace/feature_list.json
```

### Can't SSH into VM (GCP)

```bash
# Check VM exists
gcloud compute instances list --filter="name~AGENT_ID"

# Try with troubleshooting
gcloud compute ssh AGENT_ID --zone=us-central1-a --troubleshoot
```

### No logs appearing

Logs sync every 60 seconds. For immediate logs:

```bash
# GCP
gcloud compute ssh AGENT_ID --zone=us-central1-a --command="tail -50 /var/log/agent.log"

# Docker
docker logs AGENT_ID
```

### OAuth token not working

1. Verify token prefix is `sk-ant-oat` (not `sk-ant-api`)
2. Check `--auth-type oauth` flag is set
3. For GCP, verify Secret Manager permissions

---

## Known Issues

See `BACKLOG.md` for full list. Key issues:

1. **First-File Creation Bug**: The `claude-agent-sdk` with `bypassPermissions` struggles to create the FIRST file. Workaround: startup script seeds empty `feature_list.json`.

2. **AWS Provider Less Tested**: Works but has less production testing than GCP.

3. **Railway Volume Persistence**: Check Railway's current volume policies.

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| `README.md` | User-friendly getting started guide |
| `CLAUDE.md` | This file - developer/agent reference |
| `BACKLOG.md` | Known issues and planned work |
| `CONTRIBUTING.md` | Contribution guidelines |
| `docs/api/API.md` | REST API specification |
| `docs/cli/COMMANDS.md` | Detailed CLI reference |
| `docs/deployment/DEPLOYMENT.md` | GCP setup guide |
| `docs/deployment/SECURITY.md` | Security model |
| `docs/architecture/` | Architecture docs |
| `docs/archive/` | Historical planning docs |

---

## For Claude Code Agents Working on This Codebase

1. **Always run tests** after making changes
2. **Check BACKLOG.md** before starting work
3. **Test both auth methods** if changing auth code
4. **The startup script** (`shared/harness/startup_template.py`) generates code that runs on VMs - changes affect all deployed agents
5. **Provider implementations** are in `agency_quickdeploy/providers/` - each has its own quirks
6. **OAuth and API key paths are separate** - modifications to one may not affect the other

### Key Files for Common Tasks

| Task | Files |
|------|-------|
| Add CLI option | `agency_quickdeploy/cli.py` |
| Change launch behavior | `agency_quickdeploy/launcher.py` |
| Add/modify provider | `agency_quickdeploy/providers/{provider}.py` |
| Change VM startup | `shared/harness/startup_template.py` |
| Change Docker agent | `agent-runner/main.py`, `agent-runner/Dockerfile` |
| Change auth handling | `agency_quickdeploy/auth.py` |
| Add agentctl command | `agentctl/cli/` |
| Change server API | `agentctl/server/routes/` |
