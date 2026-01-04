# AgentCtl - Technical Specification

## 1. Overview

This document provides implementation details for the AgentCtl system. It is intended for Claude Code or developers implementing the system.

### 1.1 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| CLI | Python 3.11+ with Click | Widely available, good GCP SDK |
| Master Server | Python 3.11+ with FastAPI | Async support, good performance |
| Database | SQLite | Simple, no separate service needed |
| Agent Runner | Bash + Python | Simple, reliable |
| Infrastructure | GCP (GCE, Secret Manager, GCS, Cloud Logging) | Cost-effective, good APIs |
| IaC | Terraform (optional) or gcloud CLI | Reproducible setup |

### 1.2 Repository Structure

```
agentctl/
├── README.md
├── LICENSE                    # MIT
├── setup.py                   # Package installation
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
│
├── docs/
│   ├── PRD.md
│   ├── TECHNICAL_SPEC.md
│   ├── COMMANDS.md
│   ├── API.md
│   └── DEPLOYMENT.md
│
├── scripts/
│   ├── install.sh             # User installation script
│   └── setup-gcp.sh           # GCP project setup
│
├── agentctl/                  # Main Python package
│   ├── __init__.py
│   ├── __main__.py            # Entry point
│   │
│   ├── cli/                   # CLI commands
│   │   ├── __init__.py
│   │   ├── main.py            # Click app
│   │   ├── init.py            # agentctl init
│   │   ├── run.py             # agentctl run
│   │   ├── agents.py          # list, stop, delete, ssh
│   │   ├── logs.py            # log streaming
│   │   ├── secrets.py         # secret management
│   │   ├── git.py             # git operations
│   │   └── screenshots.py     # screenshot retrieval
│   │
│   ├── server/                # Master server
│   │   ├── __init__.py
│   │   ├── app.py             # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py
│   │   │   ├── logs.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── vm_manager.py  # GCE operations
│   │   │   ├── secret_manager.py
│   │   │   ├── storage_manager.py
│   │   │   └── agent_registry.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   └── database.py
│   │   └── websocket/
│   │       ├── __init__.py
│   │       └── terminal.py
│   │
│   ├── agent/                 # Agent-side code (runs on VMs)
│   │   ├── __init__.py
│   │   ├── runner.py          # Main agent runner
│   │   ├── heartbeat.py       # Status reporting
│   │   ├── screenshot.py      # Screenshot capture
│   │   ├── git_manager.py     # Auto-commit logic
│   │   └── instruction_watcher.py
│   │
│   ├── shared/                # Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── gcp.py             # GCP client utilities
│   │   └── logging.py
│   │
│   └── engines/               # AI engine abstraction
│       ├── __init__.py
│       ├── base.py            # Abstract base class
│       ├── claude.py          # Claude Code implementation
│       └── codex.py           # Codex implementation
│
├── web/                       # Local web UI (Phase 3)
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   └── api/
│   └── public/
│
├── terraform/                 # Optional IaC
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_cli/
    ├── test_server/
    └── test_agent/
```

## 2. Component Specifications

### 2.1 CLI (`agentctl/cli/`)

#### 2.1.1 Configuration

The CLI uses a configuration file at `~/.agentctl/config.yaml`:

```yaml
# ~/.agentctl/config.yaml
gcp_project: my-project-id
gcp_region: us-central1
gcp_zone: us-central1-a
master_server_url: http://34.123.45.67:8080  # Set after deploy
gcs_bucket: agentctl-artifacts-abc123
default_machine_type: e2-medium
default_timeout: 4h
default_engine: claude
screenshot_interval: 300  # seconds, 0 to disable
screenshot_retention: 24h  # keep last 24h, or "all" to keep everything
```

#### 2.1.2 Command Implementations

**`agentctl init`**

```python
# Pseudocode
def init():
    # 1. Check gcloud auth
    verify_gcloud_auth()
    
    # 2. Prompt for or detect project
    project = prompt_or_detect_project()
    
    # 3. Enable required APIs
    enable_apis([
        "compute.googleapis.com",
        "secretmanager.googleapis.com",
        "storage.googleapis.com",
        "logging.googleapis.com"
    ])
    
    # 4. Create GCS bucket
    bucket = create_bucket(f"agentctl-{project}-{random_suffix()}")
    
    # 5. Create service accounts
    create_service_account("agentctl-master")
    create_service_account("agentctl-agent")
    
    # 6. Set IAM policies
    grant_roles("agentctl-master", [
        "roles/compute.admin",
        "roles/secretmanager.secretAccessor",
        "roles/storage.admin",
        "roles/logging.viewer"
    ])
    grant_roles("agentctl-agent", [
        "roles/secretmanager.secretAccessor",
        "roles/storage.objectAdmin",
        "roles/logging.logWriter"
    ])
    
    # 7. Prompt for API keys and store
    anthropic_key = prompt_secret("Anthropic API Key")
    store_secret("anthropic-api-key", anthropic_key)
    
    github_token = prompt_secret("GitHub Token (optional)")
    if github_token:
        store_secret("github-token", github_token)
    
    # 8. Deploy master server
    deploy_master_server()
    
    # 9. Save config
    save_config({...})
    
    print("✓ AgentCtl initialized successfully!")
```

**`agentctl run`**

```python
def run(prompt, name, engine, repo, branch, timeout, machine, spot, prompt_file):
    # 1. Load prompt from file if specified
    if prompt_file:
        prompt = read_file(prompt_file)
    
    # 2. Generate agent ID if name not provided
    agent_id = name or generate_id()
    
    # 3. Call master server API
    response = api_post("/agents", {
        "id": agent_id,
        "prompt": prompt,
        "engine": engine,
        "repo": repo,
        "branch": branch,
        "timeout": parse_duration(timeout),
        "machine_type": machine,
        "spot": spot
    })
    
    # 4. Stream initial logs
    print(f"Agent {agent_id} starting...")
    stream_logs(agent_id, until="ready")
    
    print(f"Agent {agent_id} is running")
    print(f"  SSH: agentctl ssh {agent_id}")
    print(f"  Logs: agentctl logs {agent_id}")
```

### 2.2 Master Server (`agentctl/server/`)

#### 2.2.1 Database Schema

```sql
-- SQLite schema

CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,  -- 'starting', 'running', 'stopped', 'failed', 'timeout'
    engine TEXT NOT NULL,  -- 'claude', 'codex'
    prompt TEXT NOT NULL,
    repo TEXT,
    branch TEXT,
    machine_type TEXT NOT NULL,
    spot BOOLEAN NOT NULL DEFAULT FALSE,
    zone TEXT NOT NULL,
    
    gce_instance_name TEXT,
    external_ip TEXT,
    
    timeout_seconds INTEGER,
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_instructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    instruction TEXT NOT NULL,
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE agent_heartbeats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
```

#### 2.2.2 API Endpoints

```python
# FastAPI route definitions

from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AgentCtl Master", version="0.1.0")

# --- Models ---

class CreateAgentRequest(BaseModel):
    id: str
    prompt: str
    engine: str = "claude"
    repo: Optional[str] = None
    branch: Optional[str] = None
    timeout: Optional[int] = 14400  # 4 hours default
    machine_type: str = "e2-medium"
    spot: bool = False

class AgentResponse(BaseModel):
    id: str
    status: str
    engine: str
    repo: Optional[str]
    branch: Optional[str]
    external_ip: Optional[str]
    started_at: Optional[datetime]
    uptime_seconds: Optional[int]
    estimated_cost: Optional[float]

class TellRequest(BaseModel):
    instruction: str

# --- Routes ---

@app.post("/agents", response_model=AgentResponse)
async def create_agent(request: CreateAgentRequest):
    """Create and start a new agent."""
    pass

@app.get("/agents", response_model=List[AgentResponse])
async def list_agents(status: Optional[str] = None):
    """List all agents, optionally filtered by status."""
    pass

@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get details of a specific agent."""
    pass

@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop a running agent."""
    pass

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent and clean up resources."""
    pass

@app.post("/agents/{agent_id}/tell")
async def tell_agent(agent_id: str, request: TellRequest):
    """Send an instruction to a running agent."""
    pass

@app.get("/agents/{agent_id}/logs")
async def get_logs(agent_id: str, follow: bool = False):
    """Get or stream agent logs."""
    pass

@app.get("/agents/{agent_id}/screenshots")
async def list_screenshots(agent_id: str, limit: int = 10):
    """List available screenshots."""
    pass

@app.get("/agents/{agent_id}/screenshots/{filename}")
async def get_screenshot(agent_id: str, filename: str):
    """Download a specific screenshot."""
    pass

@app.websocket("/agents/{agent_id}/terminal")
async def terminal_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket for live terminal access."""
    pass

@app.post("/internal/heartbeat")
async def receive_heartbeat(agent_id: str, status: str, message: str = None):
    """Receive heartbeat from agent (internal API)."""
    pass

@app.get("/internal/instructions/{agent_id}")
async def get_pending_instructions(agent_id: str):
    """Get pending instructions for agent (internal API)."""
    pass

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

#### 2.2.3 VM Manager Service

```python
# agentctl/server/services/vm_manager.py

class VMManager:
    """Manages GCE VM lifecycle for agents."""
    
    def __init__(self, project: str, zone: str):
        self.project = project
        self.zone = zone
        self.compute = googleapiclient.discovery.build('compute', 'v1')
    
    async def create_instance(
        self,
        agent_id: str,
        machine_type: str,
        spot: bool,
        startup_script: str
    ) -> dict:
        """Create a new GCE instance for an agent."""
        instance_name = f"agent-{agent_id}"
        
        config = {
            "name": instance_name,
            "machineType": f"zones/{self.zone}/machineTypes/{machine_type}",
            "disks": [{
                "boot": True,
                "autoDelete": True,
                "initializeParams": {
                    "sourceImage": "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts",
                    "diskSizeGb": "50"
                }
            }],
            "networkInterfaces": [{
                "network": "global/networks/default",
                "accessConfigs": [{"type": "ONE_TO_ONE_NAT", "name": "External NAT"}]
            }],
            "serviceAccounts": [{
                "email": f"agentctl-agent@{self.project}.iam.gserviceaccount.com",
                "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
            }],
            "metadata": {
                "items": [
                    {"key": "startup-script", "value": startup_script},
                    {"key": "agent-id", "value": agent_id}
                ]
            },
            "labels": {
                "agentctl": "true",
                "agent-id": agent_id
            }
        }
        
        if spot:
            config["scheduling"] = {
                "preemptible": True,
                "automaticRestart": False
            }
        
        operation = self.compute.instances().insert(
            project=self.project,
            zone=self.zone,
            body=config
        ).execute()
        
        await self._wait_for_operation(operation["name"])
        
        # Get instance details including external IP
        instance = self.compute.instances().get(
            project=self.project,
            zone=self.zone,
            instance=instance_name
        ).execute()
        
        return instance
    
    async def delete_instance(self, agent_id: str) -> None:
        """Delete a GCE instance."""
        instance_name = f"agent-{agent_id}"
        operation = self.compute.instances().delete(
            project=self.project,
            zone=self.zone,
            instance=instance_name
        ).execute()
        await self._wait_for_operation(operation["name"])
    
    async def get_instance_ip(self, agent_id: str) -> Optional[str]:
        """Get external IP of an instance."""
        try:
            instance = self.compute.instances().get(
                project=self.project,
                zone=self.zone,
                instance=f"agent-{agent_id}"
            ).execute()
            return instance["networkInterfaces"][0]["accessConfigs"][0].get("natIP")
        except Exception:
            return None
```

### 2.3 Agent Runner (`agentctl/agent/`)

The agent runner is the code that executes on each agent VM. It's responsible for:
1. Setting up the environment
2. Running the AI engine
3. Managing git commits
4. Capturing screenshots
5. Reporting status to master

#### 2.3.1 Startup Script

This script is passed to the VM as metadata and runs on boot:

```bash
#!/bin/bash
# startup-script for agent VMs

set -e

# --- Configuration from metadata ---
AGENT_ID=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/agent-id" -H "Metadata-Flavor: Google")
PROJECT=$(curl -s "http://metadata.google.internal/computeMetadata/v1/project/project-id" -H "Metadata-Flavor: Google")

export AGENT_ID PROJECT

echo "Starting agent: $AGENT_ID"

# --- Install dependencies ---
apt-get update
apt-get install -y \
    git \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    jq \
    scrot \
    xvfb \
    tmux

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# --- Fetch secrets ---
mkdir -p /etc/agentctl

gcloud secrets versions access latest --secret="anthropic-api-key" > /etc/agentctl/anthropic-key
export ANTHROPIC_API_KEY=$(cat /etc/agentctl/anthropic-key)

# GitHub token (optional)
if gcloud secrets versions access latest --secret="github-token" > /etc/agentctl/github-token 2>/dev/null; then
    export GITHUB_TOKEN=$(cat /etc/agentctl/github-token)
fi

# OpenAI key for Codex (optional)
if gcloud secrets versions access latest --secret="openai-api-key" > /etc/agentctl/openai-key 2>/dev/null; then
    export OPENAI_API_KEY=$(cat /etc/agentctl/openai-key)
fi

# --- Fetch agent config from master ---
MASTER_URL=$(gcloud secrets versions access latest --secret="master-server-url")
AGENT_CONFIG=$(curl -s "$MASTER_URL/agents/$AGENT_ID")

PROMPT=$(echo "$AGENT_CONFIG" | jq -r '.prompt')
ENGINE=$(echo "$AGENT_CONFIG" | jq -r '.engine')
REPO=$(echo "$AGENT_CONFIG" | jq -r '.repo // empty')
BRANCH=$(echo "$AGENT_CONFIG" | jq -r '.branch // empty')
TIMEOUT=$(echo "$AGENT_CONFIG" | jq -r '.timeout_seconds // 14400')
SCREENSHOT_INTERVAL=$(echo "$AGENT_CONFIG" | jq -r '.screenshot_interval // 300')
SCREENSHOT_RETENTION=$(echo "$AGENT_CONFIG" | jq -r '.screenshot_retention // "24h"')

# --- Setup workspace ---
mkdir -p /workspace
cd /workspace

if [ -n "$REPO" ]; then
    echo "Cloning $REPO..."
    if [ -n "$GITHUB_TOKEN" ]; then
        git clone "https://$GITHUB_TOKEN@${REPO#https://}" repo
    else
        git clone "$REPO" repo
    fi
    cd repo
    
    if [ -n "$BRANCH" ]; then
        git checkout -B "$BRANCH"
    fi
fi

# --- Install agent runner ---
pip3 install agentctl

# --- Start services ---

# Screenshot capture (if enabled)
if [ "$SCREENSHOT_INTERVAL" -gt 0 ]; then
    Xvfb :99 -screen 0 1920x1080x24 &
    export DISPLAY=:99
    
    python3 -m agentctl.agent.screenshot \
        --interval "$SCREENSHOT_INTERVAL" \
        --retention "$SCREENSHOT_RETENTION" \
        --output /workspace/screenshots \
        --bucket "gs://$PROJECT-agentctl/$AGENT_ID/screenshots" &
fi

# Heartbeat reporter
python3 -m agentctl.agent.heartbeat \
    --master-url "$MASTER_URL" \
    --agent-id "$AGENT_ID" &

# Git auto-commit (every 15 minutes)
python3 -m agentctl.agent.git_manager \
    --interval 900 \
    --workspace /workspace/repo &

# Instruction watcher
python3 -m agentctl.agent.instruction_watcher \
    --master-url "$MASTER_URL" \
    --agent-id "$AGENT_ID" \
    --output /workspace/.instructions &

# --- Run the agent ---
cd /workspace/repo 2>/dev/null || cd /workspace

# Save prompt to file
echo "$PROMPT" > /workspace/.prompt

# Create wrapper script that handles timeouts and instructions
cat > /workspace/run_agent.sh << 'SCRIPT'
#!/bin/bash
PROMPT_FILE="/workspace/.prompt"
INSTRUCTION_FILE="/workspace/.instructions"

# Build the full prompt including any new instructions
build_prompt() {
    cat "$PROMPT_FILE"
    if [ -f "$INSTRUCTION_FILE" ] && [ -s "$INSTRUCTION_FILE" ]; then
        echo ""
        echo "--- Additional Instructions ---"
        cat "$INSTRUCTION_FILE"
        > "$INSTRUCTION_FILE"  # Clear after reading
    fi
}

if [ "$ENGINE" = "claude" ]; then
    # Run Claude Code with the prompt
    build_prompt | claude-code --dangerously-skip-permissions
elif [ "$ENGINE" = "codex" ]; then
    # Run Codex (implementation depends on specific Codex CLI)
    build_prompt | codex --dangerously-skip-permissions
fi
SCRIPT
chmod +x /workspace/run_agent.sh

# Run with timeout
timeout "$TIMEOUT" /workspace/run_agent.sh || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "Agent timed out after ${TIMEOUT}s"
        # Do final commit
        cd /workspace/repo 2>/dev/null && git add -A && git commit -m "Auto-commit before timeout" && git push || true
    fi
}

# Report completion
curl -X POST "$MASTER_URL/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d "{\"agent_id\": \"$AGENT_ID\", \"status\": \"completed\"}"

# Shutdown
shutdown -h now
```

#### 2.3.2 Screenshot Service

```python
# agentctl/agent/screenshot.py

import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from google.cloud import storage

class ScreenshotService:
    def __init__(
        self,
        interval: int,
        retention: str,  # "24h", "7d", "all"
        output_dir: Path,
        gcs_path: str
    ):
        self.interval = interval
        self.retention = self._parse_retention(retention)
        self.output_dir = output_dir
        self.gcs_path = gcs_path
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.storage_client = storage.Client()
        bucket_name, prefix = self._parse_gcs_path(gcs_path)
        self.bucket = self.storage_client.bucket(bucket_name)
        self.prefix = prefix
    
    def _parse_retention(self, retention: str) -> Optional[timedelta]:
        if retention == "all":
            return None
        if retention.endswith("h"):
            return timedelta(hours=int(retention[:-1]))
        if retention.endswith("d"):
            return timedelta(days=int(retention[:-1]))
        return timedelta(hours=24)  # default
    
    def capture(self) -> Optional[Path]:
        """Capture a screenshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = self.output_dir / filename
        
        try:
            # Try scrot first (for X11)
            subprocess.run(
                ["scrot", str(filepath)],
                check=True,
                capture_output=True
            )
            return filepath
        except subprocess.CalledProcessError:
            # Fall back to terminal capture with script/asciinema
            # or just skip if no display
            return None
    
    def upload(self, filepath: Path) -> str:
        """Upload screenshot to GCS."""
        blob_name = f"{self.prefix}/{filepath.name}"
        blob = self.bucket.blob(blob_name)
        blob.upload_from_filename(str(filepath))
        return f"gs://{self.bucket.name}/{blob_name}"
    
    def cleanup_old(self):
        """Remove screenshots older than retention period."""
        if self.retention is None:
            return
        
        cutoff = datetime.now() - self.retention
        
        # Clean local files
        for f in self.output_dir.glob("screenshot_*.png"):
            # Parse timestamp from filename
            try:
                ts_str = f.stem.replace("screenshot_", "")
                ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                if ts < cutoff:
                    f.unlink()
            except ValueError:
                pass
        
        # Clean GCS files
        blobs = self.bucket.list_blobs(prefix=self.prefix)
        for blob in blobs:
            if blob.time_created.replace(tzinfo=None) < cutoff:
                blob.delete()
    
    def run(self):
        """Main loop."""
        while True:
            filepath = self.capture()
            if filepath:
                self.upload(filepath)
            self.cleanup_old()
            time.sleep(self.interval)
```

### 2.4 Engine Abstraction (`agentctl/engines/`)

```python
# agentctl/engines/base.py

from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator

class EngineBase(ABC):
    """Abstract base class for AI coding engines."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name (e.g., 'claude', 'codex')."""
        pass
    
    @property
    @abstractmethod
    def required_secrets(self) -> list[str]:
        """List of required secret names."""
        pass
    
    @abstractmethod
    def get_command(
        self,
        prompt: str,
        workspace: str,
        dangerous_mode: bool = True
    ) -> list[str]:
        """Return the command to execute this engine."""
        pass
    
    @abstractmethod
    async def stream_output(self, process) -> AsyncGenerator[str, None]:
        """Stream output from the running engine."""
        pass


# agentctl/engines/claude.py

class ClaudeEngine(EngineBase):
    name = "claude"
    required_secrets = ["anthropic-api-key"]
    
    def get_command(
        self,
        prompt: str,
        workspace: str,
        dangerous_mode: bool = True
    ) -> list[str]:
        cmd = ["claude-code"]
        if dangerous_mode:
            cmd.append("--dangerously-skip-permissions")
        cmd.extend(["--prompt", prompt])
        return cmd


# agentctl/engines/codex.py

class CodexEngine(EngineBase):
    name = "codex"
    required_secrets = ["openai-api-key"]
    
    def get_command(
        self,
        prompt: str,
        workspace: str,
        dangerous_mode: bool = True
    ) -> list[str]:
        # Note: Codex CLI specifics TBD based on actual tool
        cmd = ["codex"]
        if dangerous_mode:
            cmd.append("--dangerously-skip-permissions")
        cmd.extend(["--prompt", prompt])
        return cmd
```

## 3. Infrastructure Setup

### 3.1 Required GCP Resources

1. **Compute Engine API** - For VMs
2. **Secret Manager API** - For credentials
3. **Cloud Storage** - For artifacts
4. **Cloud Logging API** - For logs
5. **Service Accounts**:
   - `agentctl-master@PROJECT.iam.gserviceaccount.com`
   - `agentctl-agent@PROJECT.iam.gserviceaccount.com`

### 3.2 IAM Roles

```yaml
# Master server service account (PRIVILEGED)
agentctl-master:
  - roles/compute.admin                # Manage VMs
  - roles/secretmanager.secretAccessor # Read secrets (to inject into VMs)
  - roles/storage.admin                # Manage GCS
  - roles/logging.viewer               # Read logs

# Agent VM service account (MINIMAL - no secret access!)
agentctl-agent:
  - roles/storage.objectCreator        # Upload to GCS only (can't read/delete)
  - roles/logging.logWriter            # Write logs
  # NOTE: No secretmanager access! Secrets are injected via instance metadata.
```

### 3.3 Secrets Structure

```
Secret Manager:
├── anthropic-api-key     # Required for Claude
├── openai-api-key        # Required for Codex (post-MVP)
├── github-token          # Optional, for private repos
└── master-server-url     # Set during init
```

**Secret Injection Flow:**
1. Master Server reads secrets from Secret Manager
2. Master creates VM with secrets in instance metadata (encrypted at rest)
3. Agent reads secrets from metadata service (no IAM needed)

```bash
# Inside agent VM - how secrets are accessed:
ANTHROPIC_KEY=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/anthropic-api-key" \
    -H "Metadata-Flavor: Google")
export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
```

### 3.4 Network Configuration

**Default: Agents are network-sandboxed**

```yaml
# Firewall rules created during init:

# Allow agents to reach internet
agentctl-agent-allow-internet:
  direction: EGRESS
  priority: 900
  action: ALLOW
  destination: 0.0.0.0/0
  target-tags: [agentctl-agent]

# Block agents from internal networks (RFC1918)
agentctl-agent-deny-internal:
  direction: EGRESS
  priority: 1000
  action: DENY
  destination: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]
  target-tags: [agentctl-agent]
```

**Optional: Allow internal network access**
```bash
# Per-agent override (skips the deny-internal rule)
agentctl run --allow-internal-network "Task needing internal access"
```

### 3.5 GCS Bucket Structure

```
gs://agentctl-{project}-{suffix}/
├── {agent-id}/
│   ├── screenshots/
│   │   ├── screenshot_20250101_120000.png
│   │   └── ...
│   ├── artifacts/
│   │   └── ... (any files agent wants to save)
│   └── logs/
│       └── terminal.log
```

## 4. Security Considerations

### 4.1 Credential Handling (Secret Injection Model)

**Principle:** Agents should never have IAM access to Secret Manager.

- API keys stored in Secret Manager
- Master Server fetches secrets and injects via instance metadata
- Agent reads from metadata service (no IAM needed)
- Secrets never appear in startup script text (visible in GCP Console)
- GitHub tokens are optional; public repos work without them

### 4.2 Network Security (Sandbox Model)

**Principle:** Treat agents as untrusted code.

- **Internet egress allowed** - Agents need to reach APIs, package managers, git
- **Internal VPC blocked by default** - Agents cannot reach your other infrastructure
- **No VPC peering** - Agents are isolated from other networks
- **Configurable** - Use `--allow-internal-network` for trusted workloads
- Master server exposed on public IP (restrict via firewall)
- SSH access via standard GCP SSH (IAP or direct)

### 4.3 VM Isolation

- Each agent runs in its own VM
- No shared filesystems between agents
- Minimal IAM permissions (can only upload to GCS and write logs)
- Network sandboxed from internal resources
- Spot instances automatically terminate (no orphaned VMs)

### 4.4 Cost Controls

- Timeout enforced at OS level (VM shuts down)
- Spot instances for cost savings
- GCP Budget Alerts configured during init

## 5. Testing Strategy

### 5.1 Unit Tests

- CLI command parsing
- Database operations
- GCS path handling
- Duration parsing

### 5.2 Integration Tests

- Create/delete VM (use small machine, short timeout)
- Secret read/write
- GCS upload/download

### 5.3 End-to-End Tests

- Full agent lifecycle with mock prompt
- Screenshot capture and retrieval
- Git commit and push

## 6. Deployment

### 6.1 Master Server Deployment

Option A: GCE Instance (simpler)
```bash
gcloud compute instances create agentctl-master \
    --machine-type=e2-small \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --service-account=agentctl-master@PROJECT.iam.gserviceaccount.com \
    --scopes=cloud-platform \
    --tags=http-server \
    --metadata-from-file=startup-script=scripts/master-startup.sh
```

Option B: Cloud Run (auto-scaling, but more complex for WebSockets)
```bash
gcloud run deploy agentctl-master \
    --source=. \
    --allow-unauthenticated \
    --service-account=agentctl-master@PROJECT.iam.gserviceaccount.com
```

### 6.2 CLI Distribution

```bash
# Install from PyPI (once published)
pip install agentctl

# Or install from source
git clone https://github.com/you/agentctl
cd agentctl
pip install -e .
```

## 7. Future Enhancements (Out of Scope for MVP)

1. **Authentication**: Add API keys or OAuth to master server
2. **Task Queuing**: Redis-based job queue for agent tasks
3. **Auto-PR Creation**: Agents create GitHub PRs automatically
4. **Slack/Discord Integration**: Notifications when agents complete
5. **Custom VM Images**: Baked images for faster startup
6. **Multi-region**: Run agents in different regions
7. **Agent Templates**: Pre-configured agent types (researcher, builder, tester)
