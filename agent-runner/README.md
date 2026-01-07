# Agent Runner

This directory contains the agent runner code used by multiple providers:
- **Docker**: `agency-quickdeploy launch --provider docker`
- **Railway**: `agency-quickdeploy launch --provider railway`

The same Docker image (`ghcr.io/wesleyzhao/agency-agent:latest`) is used by both providers.

## How It Works

1. When you run `agency-quickdeploy launch "task" --provider docker|railway`, the CLI
   pulls/deploys this Docker image.

2. The `main.py` entry point reads environment variables passed by the launcher
   and runs the autonomous agent loop.

## Environment Variables

These are set automatically by the launcher:

| Variable | Description |
|----------|-------------|
| `AGENT_ID` | Unique identifier for the agent |
| `AGENT_PROMPT` | Task specification |
| `ANTHROPIC_API_KEY` | API key (for api_key auth) |
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token (for oauth auth) |
| `AUTH_TYPE` | `api_key` or `oauth` |
| `MAX_ITERATIONS` | Loop limit (0 = unlimited) |
| `REPO_URL` | Git repo to clone (optional) |
| `REPO_BRANCH` | Git branch (optional) |
| `NO_SHUTDOWN` | Keep running after completion |

## Local Testing

To test locally:

```bash
cd agent-runner
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code

export AGENT_ID="test-agent"
export AGENT_PROMPT="Create a hello world Python script"
export ANTHROPIC_API_KEY="sk-ant-..."
python main.py
```

## Customization

Fork this repo and modify the agent runner to customize behavior.
Set `RAILWAY_AGENT_REPO` or `AGENCY_DOCKER_IMAGE` environment variable to your fork/custom image.
