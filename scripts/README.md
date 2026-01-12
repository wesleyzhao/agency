# Scripts

Developer tools for testing and development.

**Note:** Both scripts currently use Google Cloud Platform (GCP) only.
TODO: Add support for AWS, Docker, and other providers.

---

## ci_test.py - CI Integration Test

Simulates the "new user experience" by spinning up a fresh GCP VM and verifying the codebase works from scratch. Tests can optionally verify actual agent deployment.

### Test Levels

| Level | Name | What it tests | Duration |
|-------|------|---------------|----------|
| 1 | Build/Test | Fresh VM, clone/upload code, pip install, pytest | ~1 min |
| 2 | Deploy Startup | Level 1 + deploy agent, verify reaches "running" | ~2 min |
| 3 | Full Deploy | Level 1 + agent runs to completion | ~5-10 min |

### Code Sources

- **GitHub (default)**: Clone from GitHub, auto-detect current branch
- **Local**: SCP local code to VM (for testing uncommitted changes)

### Prerequisites

1. gcloud CLI authenticated: `gcloud auth login`
2. `.env` file with `QUICKDEPLOY_PROJECT` set
3. GCP project with Compute Engine API enabled

### Usage

```bash
# Default: Level 1, GitHub current branch
python scripts/ci_test.py

# Specific level
python scripts/ci_test.py --level 2

# Specific branch
python scripts/ci_test.py --branch main

# Test local (uncommitted) code
python scripts/ci_test.py --source local

# Keep resources for debugging
python scripts/ci_test.py --no-cleanup

# Use a larger machine
python scripts/ci_test.py --machine-type e2-standard-2
```

### How it works

**Level 1 (Build/Test):**
1. Creates a fresh GCP VM (Ubuntu 22.04, e2-medium)
2. Clones from GitHub OR SCPs local code
3. Installs Python 3.11 via deadsnakes PPA
4. Runs `pip install -e ".[server,dev]"`
5. Runs `python -m pytest`
6. Reports pass/fail and cleans up

**Level 2 (Deploy Startup):**
1. Runs Level 1 (build/test)
2. Runs `agency-quickdeploy launch "Create hello.txt" --no-shutdown`
3. Polls status until agent reaches "running" state
4. Stops agent and cleans up

**Level 3 (Full Deploy):**
1. Runs Level 1 (build/test)
2. Launches agent with simple task: "Create ci-test-output.txt"
3. Waits for agent to reach "completed" status (up to 10 min)
4. Verifies agent ran to completion
5. Cleans up

---

## dev_server.py - Dev Server Management

Launch interactive development VMs with all tooling pre-installed.

**Note:** Currently GCP only. TODO: Add AWS, Docker, Railway support.

### How is this different from agency-quickdeploy?

| Aspect | agency-quickdeploy | dev_server.py |
|--------|-------------------|---------------|
| Purpose | Autonomous AI agent | Your dev environment |
| Who works | Claude (autonomous) | You (interactive SSH) |
| VM lifetime | Temporary (auto-cleanup) | Long-running (manual cleanup) |
| Claude Code | Runs automatically | You run manually |

### Use cases

- Development when you need more compute
- Testing on a clean machine
- Running Claude Code in the cloud
- Debugging agent issues

### Prerequisites

1. gcloud CLI authenticated: `gcloud auth login`
2. `.env` file with `QUICKDEPLOY_PROJECT` set
3. (Optional) `ANTHROPIC_API_KEY` in `.env` for Claude Code

### Usage

```bash
# Launch a dev server (clones from GitHub main branch)
python scripts/dev_server.py launch

# Launch with your LOCAL code (uploads via GCS)
python scripts/dev_server.py launch --local

# Launch with a custom name
python scripts/dev_server.py launch --name my-dev-box

# Launch with specific GitHub branch
python scripts/dev_server.py launch --branch feature/my-feature

# Use spot instance (cheaper, but can be preempted)
python scripts/dev_server.py launch --spot

# List running dev servers
python scripts/dev_server.py list

# SSH into a dev server
python scripts/dev_server.py ssh my-dev-box

# Stop a dev server
python scripts/dev_server.py stop my-dev-box

# Stop all dev servers
python scripts/dev_server.py stop --all
```

### SSH Options

You can SSH in two ways:

```bash
# Option 1: Via this script
python scripts/dev_server.py ssh my-dev-box

# Option 2: Directly via gcloud
gcloud compute ssh my-dev-box --zone=us-central1-a --project=YOUR_PROJECT
```

### What you get

The dev server comes with:

- Ubuntu 22.04 LTS
- Python 3.11 with virtualenv
- Node.js 20.x
- Claude Code CLI (`claude` command)
- The repo cloned and dependencies installed
- tmux, vim, htop, and other dev tools
- If you set `ANTHROPIC_API_KEY` in `.env`, it's configured on the VM

When you SSH in, you'll be in `/root/agency` with the virtualenv activated.

### Tips

```bash
# Run tests
pytest

# Start Claude Code
claude

# Run agency-quickdeploy commands
agency-quickdeploy --help

# Check setup logs if something went wrong
cat /var/log/dev-server-setup.log
```

---

## Environment Variables

Both scripts read from `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `QUICKDEPLOY_PROJECT` | GCP project ID | (required) |
| `QUICKDEPLOY_ZONE` | GCP zone | us-central1-a |
| `QUICKDEPLOY_BUCKET` | GCS bucket | agency-ci-{project} |
| `ANTHROPIC_API_KEY` | For Claude Code on dev server | (optional) |
| `DEV_SERVER_MACHINE_TYPE` | Machine type for dev servers | e2-standard-4 |

## Authentication

Both scripts use your local `gcloud` authentication. Make sure you're logged in:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

The VMs get GCS access automatically via their service account.

## Troubleshooting

### CI test times out

- Try a larger machine: `--machine-type e2-standard-2`
- Increase timeout: `--timeout 30`
- Run with `--no-cleanup` to debug

### Dev server setup incomplete

SSH in and check the setup log:
```bash
gcloud compute ssh YOUR_SERVER --zone=us-central1-a --project=YOUR_PROJECT
cat /var/log/dev-server-setup.log
```

### Agent deployment fails (Level 2/3)

1. SSH into the CI VM with `--no-cleanup`
2. Check agent logs: `agency-quickdeploy logs AGENT_ID`
3. Check Secret Manager has the required secrets configured
