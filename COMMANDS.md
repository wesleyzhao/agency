# AgentCtl - CLI Command Reference

## Overview

`agentctl` is the command-line interface for managing autonomous AI coding agents.

## Installation

```bash
# From PyPI
pip install agentctl

# From source
git clone https://github.com/yourusername/agentctl
cd agentctl
pip install -e .
```

## Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud`) installed and authenticated
- A GCP project with billing enabled

---

## Commands

### `agentctl init`

Initialize AgentCtl in a GCP project. This sets up all required resources.

```bash
agentctl init [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--project` | GCP project ID | Auto-detected from gcloud |
| `--region` | GCP region | us-central1 |
| `--zone` | GCP zone | us-central1-a |
| `--skip-secrets` | Don't prompt for API keys | False |

**Example:**
```bash
# Interactive setup
agentctl init

# Non-interactive
agentctl init --project my-project --region us-west1 --zone us-west1-a
```

**What it does:**
1. Enables required GCP APIs
2. Creates a GCS bucket for artifacts
3. Creates service accounts with appropriate IAM roles
4. Prompts for and stores API keys in Secret Manager
5. Deploys the master server
6. Saves configuration to `~/.agentctl/config.yaml`

---

### `agentctl run`

Start a new agent with a prompt.

```bash
agentctl run [OPTIONS] [PROMPT]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `PROMPT` | The task prompt for the agent (optional if --prompt-file used) |

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--name`, `-n` | Agent name/ID | Auto-generated |
| `--engine`, `-e` | AI engine: `claude` or `codex` | claude |
| `--repo`, `-r` | Git repository URL to clone | None |
| `--branch`, `-b` | Git branch to create/checkout | None |
| `--timeout`, `-t` | Auto-stop after duration (e.g., 4h, 30m) | 4h |
| `--machine`, `-m` | GCE machine type | e2-medium |
| `--spot` | Use spot/preemptible instance | False |
| `--prompt-file`, `-f` | Read prompt from file | None |
| `--edit` | Open prompt in $EDITOR | False |
| `--screenshot-interval` | Seconds between screenshots (0 to disable) | 300 |
| `--screenshot-retention` | How long to keep screenshots (e.g., 24h, 7d, all) | 24h |
| `--allow-internal-network` | Allow agent to access internal VPC (security risk, use sparingly) | False |

**Examples:**
```bash
# Simple prompt
agentctl run "Build a REST API for a todo app in Python using FastAPI"

# With options
agentctl run \
  --name todo-api \
  --engine claude \
  --repo https://github.com/me/myproject \
  --branch feature/todo-api \
  --timeout 2h \
  --spot \
  "Add a todo API with CRUD operations"

# From a file
agentctl run --prompt-file ./specs/detailed-spec.md --name big-project

# Interactive editor
agentctl run --edit --name research-agent

# Disable screenshots
agentctl run --screenshot-interval 0 "Quick task"

# Keep all screenshots
agentctl run --screenshot-retention all "Important task"

# Allow internal network access (use with caution!)
agentctl run --allow-internal-network "Task that needs to access internal DB"
```

> ⚠️ **Security Note:** By default, agents are network-sandboxed and cannot access your internal VPC. Use `--allow-internal-network` only for trusted workloads. See SECURITY.md for details.

---

### `agentctl list`

List all agents.

```bash
agentctl list [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--status`, `-s` | Filter by status: running, stopped, failed | All |
| `--format`, `-o` | Output format: table, json, csv | table |

**Example:**
```bash
agentctl list

# Output:
# NAME          ENGINE   STATUS    UPTIME    COST      REPO
# todo-api      claude   running   2h 34m    $0.42     github.com/me/myproject
# research-bot  codex    running   45m       $0.15     -
# old-task      claude   stopped   -         $1.20     github.com/me/other

agentctl list --status running --format json
```

---

### `agentctl status`

Get detailed status of a specific agent.

```bash
agentctl status <AGENT_ID>
```

**Example:**
```bash
agentctl status todo-api

# Output:
# Agent: todo-api
# Status: running
# Engine: claude
# Machine: e2-medium (spot)
# 
# Started: 2025-01-15 10:30:00 UTC
# Uptime: 2h 34m
# Timeout: 4h (1h 26m remaining)
# 
# Repository: github.com/me/myproject
# Branch: feature/todo-api
# Commits: 12
# Last commit: 5 minutes ago - "Add DELETE endpoint"
# 
# External IP: 34.123.45.67
# Estimated Cost: $0.42
```

---

### `agentctl logs`

View agent logs.

```bash
agentctl logs <AGENT_ID> [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--follow`, `-f` | Stream logs continuously | False |
| `--tail`, `-n` | Number of lines to show | 100 |
| `--since` | Show logs since timestamp or duration (e.g., 1h) | All |

**Examples:**
```bash
# View recent logs
agentctl logs todo-api

# Stream live logs
agentctl logs todo-api --follow

# Last 50 lines
agentctl logs todo-api --tail 50

# Last hour
agentctl logs todo-api --since 1h
```

---

### `agentctl ssh`

SSH into an agent's VM.

```bash
agentctl ssh <AGENT_ID> [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--command`, `-c` | Run a command instead of interactive shell | None |

**Examples:**
```bash
# Interactive shell
agentctl ssh todo-api

# Run a command
agentctl ssh todo-api -c "ls -la /workspace"
agentctl ssh todo-api -c "cat /workspace/repo/README.md"
```

---

### `agentctl tell`

Send additional instructions to a running agent.

```bash
agentctl tell <AGENT_ID> <INSTRUCTION>
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--file`, `-f` | Read instruction from file | None |

**Examples:**
```bash
# Quick instruction
agentctl tell todo-api "Also add input validation to all endpoints"

# From file
agentctl tell todo-api --file ./additional-requirements.md
```

---

### `agentctl stop`

Stop a running agent.

```bash
agentctl stop <AGENT_ID> [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--all` | Stop all running agents | False |
| `--force` | Skip confirmation | False |
| `--direct` | Bypass master server, call GCP directly (emergency use) | False |

**Examples:**
```bash
# Stop one agent
agentctl stop todo-api

# Stop all agents
agentctl stop --all

# Force stop without confirmation
agentctl stop todo-api --force

# Emergency stop when master server is down
agentctl stop todo-api --direct
```

> **Note:** The `--direct` flag should only be used when the master server is unavailable. It stops the VM directly via GCP but doesn't update the database.

---

### `agentctl delete`

Delete an agent and clean up its resources.

```bash
agentctl delete <AGENT_ID> [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--keep-artifacts` | Don't delete GCS artifacts | False |
| `--force` | Skip confirmation | False |

**Examples:**
```bash
# Delete agent and all artifacts
agentctl delete old-task

# Keep the screenshots and outputs
agentctl delete old-task --keep-artifacts
```

---

### `agentctl git`

View git information for an agent.

```bash
agentctl git <AGENT_ID> <SUBCOMMAND>
```

**Subcommands:**
| Subcommand | Description |
|------------|-------------|
| `status` | Show git status |
| `log` | Show commit history |
| `diff` | Show uncommitted changes |
| `show <commit>` | Show a specific commit |

**Examples:**
```bash
agentctl git todo-api status
agentctl git todo-api log --oneline -10
agentctl git todo-api diff
agentctl git todo-api show HEAD
```

---

### `agentctl screenshots`

Manage agent screenshots.

```bash
agentctl screenshots <AGENT_ID> [SUBCOMMAND]
```

**Subcommands:**
| Subcommand | Description |
|------------|-------------|
| `list` | List available screenshots (default) |
| `download` | Download screenshots |
| `open` | Open latest screenshot |

**Options for `list`:**
| Option | Description | Default |
|--------|-------------|---------|
| `--limit`, `-n` | Number of screenshots to list | 10 |

**Options for `download`:**
| Option | Description | Default |
|--------|-------------|---------|
| `--output`, `-o` | Output directory | ./screenshots |
| `--limit`, `-n` | Number to download | 10 |
| `--all` | Download all screenshots | False |

**Examples:**
```bash
# List recent screenshots
agentctl screenshots todo-api

# Download last 5
agentctl screenshots todo-api download --limit 5

# Download all to specific directory
agentctl screenshots todo-api download --all --output ./todo-api-screenshots

# Open latest in default viewer
agentctl screenshots todo-api open
```

---

### `agentctl artifacts`

Browse and download agent artifacts.

```bash
agentctl artifacts <AGENT_ID> [SUBCOMMAND]
```

**Subcommands:**
| Subcommand | Description |
|------------|-------------|
| `list` | List artifacts (default) |
| `download` | Download artifact(s) |
| `browse` | Open GCS bucket in browser |

**Examples:**
```bash
# List artifacts
agentctl artifacts todo-api

# Download specific file
agentctl artifacts todo-api download output/report.pdf

# Download all
agentctl artifacts todo-api download --all

# Open in browser
agentctl artifacts todo-api browse
```

---

### `agentctl secrets`

Manage secrets in GCP Secret Manager.

```bash
agentctl secrets <SUBCOMMAND>
```

**Subcommands:**
| Subcommand | Description |
|------------|-------------|
| `list` | List all secrets |
| `set` | Set a secret value |
| `get` | Get a secret value |
| `delete` | Delete a secret |

**Examples:**
```bash
# List secrets
agentctl secrets list

# Set a secret (prompts for value)
agentctl secrets set anthropic-api-key

# Set from stdin
echo "sk-..." | agentctl secrets set openai-api-key --stdin

# Get a secret
agentctl secrets get anthropic-api-key

# Delete a secret
agentctl secrets delete old-key
```

---

### `agentctl cost`

View cost information.

```bash
agentctl cost [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--period` | Time period: today, week, month | month |
| `--breakdown` | Show per-agent breakdown | False |

**Examples:**
```bash
# This month's cost
agentctl cost

# Today with breakdown
agentctl cost --period today --breakdown
```

---

### `agentctl reconcile`

Sync local database with actual GCP state. Use when state gets out of sync (e.g., after master server crash).

```bash
agentctl reconcile [OPTIONS]
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Show what would change without making changes | False |
| `--force` | Don't prompt for confirmation | False |

**What it does:**
1. Lists all GCE VMs with `agentctl` label
2. Compares with database records
3. Adds missing agents to database
4. Marks non-existent VMs as stopped
5. Updates IP addresses and status

**Examples:**
```bash
# See what would change
agentctl reconcile --dry-run

# Actually sync
agentctl reconcile

# Output:
# Found 3 VMs in GCP, 2 agents in database
# + agent-abc123: VM exists but not in database (will add)
# ~ agent-def456: Status mismatch, VM running but DB says stopped (will update)
# - agent-ghi789: In database but VM not found (will mark stopped)
# 
# Apply changes? [y/N]
```

---

### `agentctl server`

Manage the master server.

```bash
agentctl server <SUBCOMMAND>
```

**Subcommands:**
| Subcommand | Description |
|------------|-------------|
| `status` | Check server status |
| `logs` | View server logs |
| `restart` | Restart the server |
| `deploy` | Deploy/update the server |

**Examples:**
```bash
agentctl server status
agentctl server logs --follow
agentctl server restart
agentctl server deploy
```

---

### `agentctl config`

Manage local configuration.

```bash
agentctl config <SUBCOMMAND>
```

**Subcommands:**
| Subcommand | Description |
|------------|-------------|
| `show` | Show current config |
| `set` | Set a config value |
| `edit` | Open config in editor |

**Examples:**
```bash
agentctl config show
agentctl config set default_engine codex
agentctl config set default_timeout 2h
agentctl config edit
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AGENTCTL_CONFIG` | Path to config file (default: ~/.agentctl/config.yaml) |
| `AGENTCTL_MASTER_URL` | Override master server URL |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account key file |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Agent not found |
| 4 | GCP authentication error |
| 5 | Master server unreachable |

---

## Configuration File

Location: `~/.agentctl/config.yaml`

```yaml
# GCP settings
gcp_project: my-project-id
gcp_region: us-central1
gcp_zone: us-central1-a

# Master server
master_server_url: http://34.123.45.67:8080

# Storage
gcs_bucket: agentctl-artifacts-abc123

# Defaults
default_machine_type: e2-medium
default_timeout: 4h
default_engine: claude
screenshot_interval: 300  # seconds, 0 to disable
screenshot_retention: 24h  # or "7d", "all"
```
