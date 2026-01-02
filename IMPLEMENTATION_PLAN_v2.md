# AgentCtl - Implementation Plan (Revised)

## Overview

This document provides a **detailed, test-driven, incremental** implementation plan. Each task is small enough to complete in one focused session, includes explicit test criteria, and builds on previous work.

**Key Principles:**
1. **Test First** - Write tests before or alongside implementation
2. **Small Steps** - Each task is 30-60 minutes of work
3. **Local First** - Test everything locally before deploying to GCP
4. **Explicit Interfaces** - Define function signatures before implementing

---

## Pre-Implementation Setup

### Task 0.1: Repository Creation

**Time:** 10 minutes

```bash
mkdir agentctl
cd agentctl
git init

# Create structure
mkdir -p agentctl/{cli,server,agent,shared,engines}
mkdir -p agentctl/server/{routes,services,models}
mkdir -p tests/{unit,integration}
mkdir -p scripts docs

# Create files
touch agentctl/__init__.py
touch agentctl/cli/__init__.py
touch agentctl/server/__init__.py
touch agentctl/agent/__init__.py
touch agentctl/shared/__init__.py
touch agentctl/engines/__init__.py
touch tests/__init__.py

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.env
.venv
venv/
*.db
.pytest_cache/
.coverage
htmlcov/
EOF

git add .
git commit -m "Initial repository structure"
```

**Verification:** `ls -la agentctl/` shows all directories

---

### Task 0.2: Package Configuration

**Time:** 15 minutes

**File: `pyproject.toml`**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "agentctl"
version = "0.1.0"
description = "CLI for managing autonomous AI coding agents"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "httpx>=0.24",
    "pyyaml>=6.0",
    "rich>=13.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
server = [
    "fastapi>=0.100",
    "uvicorn>=0.23",
    "google-cloud-compute>=1.14",
    "google-cloud-secret-manager>=2.16",
    "google-cloud-storage>=2.10",
]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[project.scripts]
agentctl = "agentctl.cli.main:cli"

[tool.setuptools.packages.find]
where = ["."]
```

**File: `requirements.txt`**
```
click>=8.0
httpx>=0.24
pyyaml>=6.0
rich>=13.0
pydantic>=2.0
```

**File: `requirements-dev.txt`**
```
-r requirements.txt
pytest>=7.0
pytest-asyncio>=0.21
fastapi>=0.100
uvicorn>=0.23
```

**Test:**
```bash
pip install -e ".[dev]"
python -c "import agentctl; print('OK')"
```

**Commit:** `git commit -am "Add package configuration"`

---

## Phase 1: Core CLI (Local Only)

**Goal:** Working CLI that can talk to a local server. No GCP yet.

---

### Task 1.0: Provider Interface (Critical for Extensibility)

**Time:** 25 minutes

Define the cloud provider abstraction that allows future AWS/Azure support and local development.

**File: `agentctl/providers/__init__.py`**
```python
"""Cloud provider implementations."""
from agentctl.providers.base import CloudProvider
from agentctl.providers.gcp import GCPProvider
from agentctl.providers.local import LocalProvider

__all__ = ["CloudProvider", "GCPProvider", "LocalProvider"]
```

**File: `agentctl/providers/base.py`**
```python
"""Abstract cloud provider interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class VMConfig:
    """Configuration for creating a VM."""
    name: str
    machine_type: str
    startup_script: str
    spot: bool = False
    labels: dict = None


@dataclass  
class VMInstance:
    """Represents a running VM."""
    name: str
    status: str  # "running", "stopped", "terminated"
    external_ip: Optional[str]
    provider_id: str  # Provider-specific ID


class CloudProvider(ABC):
    """Abstract interface for cloud operations.
    
    Implement this to add support for new cloud providers.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'gcp', 'aws', 'local')."""
        pass
    
    @abstractmethod
    def create_vm(self, config: VMConfig) -> VMInstance:
        """Create a new VM instance."""
        pass
    
    @abstractmethod
    def delete_vm(self, name: str) -> bool:
        """Delete a VM instance. Returns True if deleted."""
        pass
    
    @abstractmethod
    def get_vm(self, name: str) -> Optional[VMInstance]:
        """Get VM details. Returns None if not found."""
        pass
    
    @abstractmethod
    def list_vms(self, label_filter: dict = None) -> list[VMInstance]:
        """List VMs, optionally filtered by labels."""
        pass
    
    @abstractmethod
    def get_secret(self, name: str) -> Optional[str]:
        """Get a secret value. Returns None if not found."""
        pass
    
    @abstractmethod
    def set_secret(self, name: str, value: str) -> None:
        """Set a secret value."""
        pass
    
    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload file to cloud storage. Returns the cloud URL."""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download file from cloud storage."""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str) -> list[str]:
        """List files in cloud storage with given prefix."""
        pass
```

**File: `agentctl/providers/local.py`**
```python
"""Local provider for development without cloud."""
from pathlib import Path
from typing import Optional
import json
import subprocess

from agentctl.providers.base import CloudProvider, VMConfig, VMInstance


class LocalProvider(CloudProvider):
    """Local development provider using Docker.
    
    This allows testing without a GCP account.
    """
    
    name = "local"
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path.home() / ".agentctl" / "local"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_file = self.data_dir / "secrets.json"
        self.storage_dir = self.data_dir / "storage"
        self.storage_dir.mkdir(exist_ok=True)
    
    def create_vm(self, config: VMConfig) -> VMInstance:
        """Create a Docker container as a 'VM'."""
        # For local dev, we might just run in a subprocess
        # or use Docker. Keeping simple for now.
        return VMInstance(
            name=config.name,
            status="running",
            external_ip="127.0.0.1",
            provider_id=f"local-{config.name}"
        )
    
    def delete_vm(self, name: str) -> bool:
        return True  # No-op for local
    
    def get_vm(self, name: str) -> Optional[VMInstance]:
        return None  # Would check Docker
    
    def list_vms(self, label_filter: dict = None) -> list[VMInstance]:
        return []
    
    def get_secret(self, name: str) -> Optional[str]:
        if not self.secrets_file.exists():
            return None
        secrets = json.loads(self.secrets_file.read_text())
        return secrets.get(name)
    
    def set_secret(self, name: str, value: str) -> None:
        secrets = {}
        if self.secrets_file.exists():
            secrets = json.loads(self.secrets_file.read_text())
        secrets[name] = value
        self.secrets_file.write_text(json.dumps(secrets, indent=2))
    
    def upload_file(self, local_path: Path, remote_path: str) -> str:
        dest = self.storage_dir / remote_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(local_path.read_bytes())
        return f"local://{remote_path}"
    
    def download_file(self, remote_path: str, local_path: Path) -> None:
        src = self.storage_dir / remote_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(src.read_bytes())
    
    def list_files(self, prefix: str) -> list[str]:
        prefix_path = self.storage_dir / prefix
        if not prefix_path.exists():
            return []
        return [str(p.relative_to(self.storage_dir)) for p in prefix_path.rglob("*") if p.is_file()]
```

**File: `tests/unit/test_providers.py`**
```python
"""Tests for provider interface."""
import pytest
from pathlib import Path
from agentctl.providers.base import CloudProvider, VMConfig
from agentctl.providers.local import LocalProvider


def test_local_provider_secrets(tmp_path):
    """LocalProvider should store and retrieve secrets."""
    provider = LocalProvider(data_dir=tmp_path)
    
    provider.set_secret("test-key", "test-value")
    assert provider.get_secret("test-key") == "test-value"
    assert provider.get_secret("nonexistent") is None


def test_local_provider_files(tmp_path):
    """LocalProvider should store and retrieve files."""
    provider = LocalProvider(data_dir=tmp_path)
    
    # Create a test file
    local_file = tmp_path / "test.txt"
    local_file.write_text("hello")
    
    # Upload
    url = provider.upload_file(local_file, "bucket/test.txt")
    assert "local://" in url
    
    # Download
    download_path = tmp_path / "downloaded.txt"
    provider.download_file("bucket/test.txt", download_path)
    assert download_path.read_text() == "hello"
    
    # List
    files = provider.list_files("bucket/")
    assert "bucket/test.txt" in files
```

**Test:**
```bash
pytest tests/unit/test_providers.py -v
```

**Commit:** `git commit -am "Add cloud provider interface for extensibility"`

**Why this matters:** This abstraction allows:
1. Local development without GCP
2. Future AWS/Azure support
3. Easy mocking in tests
4. Clear separation of concerns

---

### Task 1.1: Define Core Data Models

**Time:** 20 minutes

**File: `agentctl/shared/models.py`**
```python
"""Core data models used across CLI and server."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AgentStatus(str, Enum):
    """Possible agent states."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    TIMEOUT = "timeout"


class EngineType(str, Enum):
    """Supported AI engines."""
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass
class AgentConfig:
    """Configuration for creating an agent."""
    prompt: str
    name: Optional[str] = None
    engine: EngineType = EngineType.CLAUDE
    repo: Optional[str] = None
    branch: Optional[str] = None
    timeout_seconds: int = 14400  # 4 hours
    machine_type: str = "e2-medium"
    spot: bool = False
    screenshot_interval: int = 300  # 0 to disable
    screenshot_retention: str = "24h"


@dataclass
class Agent:
    """Represents an agent instance."""
    id: str
    status: AgentStatus
    config: AgentConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    external_ip: Optional[str] = None
    gce_instance: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "prompt": self.config.prompt,
            "engine": self.config.engine.value,
            "repo": self.config.repo,
            "branch": self.config.branch,
            "timeout_seconds": self.config.timeout_seconds,
            "machine_type": self.config.machine_type,
            "spot": self.config.spot,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "external_ip": self.external_ip,
        }
```

**File: `tests/unit/test_models.py`**
```python
"""Tests for core data models."""
import pytest
from agentctl.shared.models import AgentConfig, Agent, AgentStatus, EngineType


def test_agent_config_defaults():
    """AgentConfig should have sensible defaults."""
    config = AgentConfig(prompt="Test prompt")
    assert config.prompt == "Test prompt"
    assert config.engine == EngineType.CLAUDE
    assert config.timeout_seconds == 14400
    assert config.spot is False


def test_agent_status_values():
    """AgentStatus should have expected values."""
    assert AgentStatus.PENDING.value == "pending"
    assert AgentStatus.RUNNING.value == "running"


def test_agent_to_dict():
    """Agent.to_dict() should serialize correctly."""
    config = AgentConfig(prompt="Test")
    agent = Agent(id="test-123", status=AgentStatus.PENDING, config=config)
    d = agent.to_dict()
    assert d["id"] == "test-123"
    assert d["status"] == "pending"
    assert d["prompt"] == "Test"
```

**Test:**
```bash
pytest tests/unit/test_models.py -v
```

**Commit:** `git commit -am "Add core data models with tests"`

---

### Task 1.2: Configuration Module

**Time:** 25 minutes

**File: `agentctl/shared/config.py`**
```python
"""Configuration management."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


CONFIG_DIR = Path.home() / ".agentctl"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


@dataclass
class Config:
    """Application configuration."""
    # GCP settings
    gcp_project: Optional[str] = None
    gcp_region: str = "us-central1"
    gcp_zone: str = "us-central1-a"
    
    # Server settings
    master_server_url: Optional[str] = None
    
    # Storage
    gcs_bucket: Optional[str] = None
    
    # Defaults
    default_machine_type: str = "e2-medium"
    default_timeout: str = "4h"
    default_engine: str = "claude"
    screenshot_interval: int = 300
    screenshot_retention: str = "24h"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """Load config from file, with env var overrides."""
        path = path or CONFIG_FILE
        config = cls()
        
        # Load from file if exists
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Environment variable overrides
        env_mappings = {
            "AGENTCTL_GCP_PROJECT": "gcp_project",
            "AGENTCTL_GCP_REGION": "gcp_region",
            "AGENTCTL_GCP_ZONE": "gcp_zone",
            "AGENTCTL_MASTER_URL": "master_server_url",
        }
        for env_var, attr in env_mappings.items():
            if env_var in os.environ:
                setattr(config, attr, os.environ[env_var])
        
        return config

    def save(self, path: Optional[Path] = None) -> None:
        """Save config to file."""
        path = path or CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "gcp_project": self.gcp_project,
            "gcp_region": self.gcp_region,
            "gcp_zone": self.gcp_zone,
            "master_server_url": self.master_server_url,
            "gcs_bucket": self.gcs_bucket,
            "default_machine_type": self.default_machine_type,
            "default_timeout": self.default_timeout,
            "default_engine": self.default_engine,
            "screenshot_interval": self.screenshot_interval,
            "screenshot_retention": self.screenshot_retention,
        }
        
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if not self.master_server_url:
            errors.append("master_server_url is required")
        return errors


def parse_duration(duration: str) -> int:
    """Parse duration string (e.g., '4h', '30m') to seconds."""
    duration = duration.strip().lower()
    if duration.endswith("h"):
        return int(duration[:-1]) * 3600
    elif duration.endswith("m"):
        return int(duration[:-1]) * 60
    elif duration.endswith("s"):
        return int(duration[:-1])
    else:
        return int(duration)
```

**File: `tests/unit/test_config.py`**
```python
"""Tests for configuration module."""
import os
import pytest
from pathlib import Path
from agentctl.shared.config import Config, parse_duration


def test_config_defaults():
    """Config should have sensible defaults."""
    config = Config()
    assert config.gcp_region == "us-central1"
    assert config.default_timeout == "4h"


def test_config_load_from_file(tmp_path):
    """Config should load from YAML file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("gcp_project: my-project\ngcp_region: us-west1\n")
    
    config = Config.load(config_file)
    assert config.gcp_project == "my-project"
    assert config.gcp_region == "us-west1"


def test_config_env_override(tmp_path, monkeypatch):
    """Environment variables should override file values."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("gcp_project: file-project\n")
    
    monkeypatch.setenv("AGENTCTL_GCP_PROJECT", "env-project")
    config = Config.load(config_file)
    assert config.gcp_project == "env-project"


def test_config_save(tmp_path):
    """Config should save to YAML file."""
    config_file = tmp_path / "config.yaml"
    config = Config(gcp_project="test-project")
    config.save(config_file)
    
    loaded = Config.load(config_file)
    assert loaded.gcp_project == "test-project"


def test_parse_duration():
    """parse_duration should handle various formats."""
    assert parse_duration("4h") == 14400
    assert parse_duration("30m") == 1800
    assert parse_duration("60s") == 60
    assert parse_duration("3600") == 3600
```

**Test:**
```bash
pytest tests/unit/test_config.py -v
```

**Commit:** `git commit -am "Add configuration module with tests"`

---

### Task 1.3: CLI Framework Setup

**Time:** 20 minutes

**File: `agentctl/cli/main.py`**
```python
"""Main CLI entry point."""
import click
from rich.console import Console

console = Console()

# Version
VERSION = "0.1.0"


@click.group()
@click.version_option(version=VERSION)
@click.pass_context
def cli(ctx):
    """AgentCtl - Manage autonomous AI coding agents."""
    ctx.ensure_object(dict)


# Import and register command groups
# These will be added in subsequent tasks
def register_commands():
    """Register all CLI commands."""
    # Will be populated as we add commands
    pass


register_commands()


if __name__ == "__main__":
    cli()
```

**File: `agentctl/__main__.py`**
```python
"""Allow running as python -m agentctl."""
from agentctl.cli.main import cli

if __name__ == "__main__":
    cli()
```

**File: `tests/unit/test_cli_main.py`**
```python
"""Tests for CLI main module."""
from click.testing import CliRunner
from agentctl.cli.main import cli


def test_cli_help():
    """CLI should show help text."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "AgentCtl" in result.output


def test_cli_version():
    """CLI should show version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

**Test:**
```bash
pytest tests/unit/test_cli_main.py -v
agentctl --help
agentctl --version
```

**Commit:** `git commit -am "Add CLI framework with tests"`

---

### Task 1.4: API Client Module

**Time:** 25 minutes

**File: `agentctl/shared/api_client.py`**
```python
"""HTTP client for master server API."""
from typing import Optional, Any
import httpx
from .config import Config
from .models import Agent, AgentConfig, AgentStatus


class APIError(Exception):
    """API request failed."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    """Client for the AgentCtl master server API."""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make HTTP request and handle errors."""
        url = f"{self.base_url}{path}"
        try:
            response = self._client.request(method, url, **kwargs)
            if response.status_code >= 400:
                try:
                    error_detail = response.json().get("detail", response.text)
                except:
                    error_detail = response.text
                raise APIError(f"API error: {error_detail}", response.status_code)
            return response.json() if response.content else None
        except httpx.RequestError as e:
            raise APIError(f"Connection failed: {e}")
    
    def health_check(self) -> bool:
        """Check if server is healthy."""
        try:
            result = self._request("GET", "/health")
            return result.get("status") == "healthy"
        except APIError:
            return False
    
    def create_agent(self, config: AgentConfig) -> dict:
        """Create a new agent."""
        payload = {
            "prompt": config.prompt,
            "name": config.name,
            "engine": config.engine.value,
            "repo": config.repo,
            "branch": config.branch,
            "timeout_seconds": config.timeout_seconds,
            "machine_type": config.machine_type,
            "spot": config.spot,
            "screenshot_interval": config.screenshot_interval,
            "screenshot_retention": config.screenshot_retention,
        }
        return self._request("POST", "/agents", json=payload)
    
    def list_agents(self, status: Optional[str] = None) -> list[dict]:
        """List all agents."""
        params = {}
        if status:
            params["status"] = status
        result = self._request("GET", "/agents", params=params)
        return result.get("agents", [])
    
    def get_agent(self, agent_id: str) -> dict:
        """Get agent details."""
        return self._request("GET", f"/agents/{agent_id}")
    
    def stop_agent(self, agent_id: str) -> dict:
        """Stop a running agent."""
        return self._request("POST", f"/agents/{agent_id}/stop")
    
    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent."""
        self._request("DELETE", f"/agents/{agent_id}")
    
    def tell_agent(self, agent_id: str, instruction: str) -> dict:
        """Send instruction to agent."""
        return self._request(
            "POST", 
            f"/agents/{agent_id}/tell",
            json={"instruction": instruction}
        )
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()


def get_client(config: Optional[Config] = None) -> APIClient:
    """Get API client from config."""
    if config is None:
        config = Config.load()
    if not config.master_server_url:
        raise APIError("master_server_url not configured. Run 'agentctl init' first.")
    return APIClient(config.master_server_url)
```

**File: `tests/unit/test_api_client.py`**
```python
"""Tests for API client module."""
import pytest
from unittest.mock import Mock, patch
from agentctl.shared.api_client import APIClient, APIError
from agentctl.shared.models import AgentConfig, EngineType


def test_api_client_health_check_success():
    """Health check should return True when server is healthy."""
    with patch("httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "healthy"}'
        mock_response.json.return_value = {"status": "healthy"}
        mock_client.return_value.request.return_value = mock_response
        
        client = APIClient("http://localhost:8080")
        assert client.health_check() is True


def test_api_client_health_check_failure():
    """Health check should return False when server is down."""
    with patch("httpx.Client") as mock_client:
        mock_client.return_value.request.side_effect = Exception("Connection refused")
        
        client = APIClient("http://localhost:8080")
        assert client.health_check() is False


def test_api_client_create_agent():
    """Create agent should POST to /agents."""
    with patch("httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "test-123"}'
        mock_response.json.return_value = {"id": "test-123"}
        mock_client.return_value.request.return_value = mock_response
        
        client = APIClient("http://localhost:8080")
        config = AgentConfig(prompt="Test prompt")
        result = client.create_agent(config)
        
        assert result["id"] == "test-123"
        mock_client.return_value.request.assert_called_once()
        call_args = mock_client.return_value.request.call_args
        assert call_args[0][0] == "POST"
        assert "/agents" in call_args[0][1]


def test_api_client_error_handling():
    """API errors should raise APIError."""
    with patch("httpx.Client") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b'{"detail": "Not found"}'
        mock_response.json.return_value = {"detail": "Not found"}
        mock_response.text = "Not found"
        mock_client.return_value.request.return_value = mock_response
        
        client = APIClient("http://localhost:8080")
        with pytest.raises(APIError) as exc:
            client.get_agent("nonexistent")
        assert exc.value.status_code == 404
```

**Test:**
```bash
pytest tests/unit/test_api_client.py -v
```

**Commit:** `git commit -am "Add API client module with tests"`

---

### Task 1.5: Run Command

**Time:** 25 minutes

**File: `agentctl/cli/run.py`**
```python
"""Run command - create and start an agent."""
import click
from rich.console import Console
from rich.table import Table

from agentctl.shared.config import Config, parse_duration
from agentctl.shared.api_client import get_client, APIError
from agentctl.shared.models import AgentConfig, EngineType

console = Console()


@click.command()
@click.argument("prompt", required=False)
@click.option("--name", "-n", help="Agent name (auto-generated if not provided)")
@click.option("--engine", "-e", type=click.Choice(["claude", "codex"]), default="claude", help="AI engine")
@click.option("--repo", "-r", help="Git repository URL to clone")
@click.option("--branch", "-b", help="Git branch to create/checkout")
@click.option("--timeout", "-t", default="4h", help="Auto-stop after duration (e.g., 4h, 30m)")
@click.option("--machine", "-m", default="e2-medium", help="GCE machine type")
@click.option("--spot", is_flag=True, help="Use spot/preemptible instance")
@click.option("--prompt-file", "-f", type=click.Path(exists=True), help="Read prompt from file")
@click.option("--screenshot-interval", type=int, default=300, help="Seconds between screenshots (0 to disable)")
@click.option("--screenshot-retention", default="24h", help="How long to keep screenshots")
def run(prompt, name, engine, repo, branch, timeout, machine, spot, prompt_file, screenshot_interval, screenshot_retention):
    """Start a new agent with the given PROMPT."""
    # Get prompt from file if specified
    if prompt_file:
        with open(prompt_file) as f:
            prompt = f.read()
    
    if not prompt:
        console.print("[red]Error:[/red] Prompt is required. Provide as argument or use --prompt-file")
        raise SystemExit(1)
    
    # Build config
    config = AgentConfig(
        prompt=prompt,
        name=name,
        engine=EngineType(engine),
        repo=repo,
        branch=branch,
        timeout_seconds=parse_duration(timeout),
        machine_type=machine,
        spot=spot,
        screenshot_interval=screenshot_interval,
        screenshot_retention=screenshot_retention,
    )
    
    # Call API
    try:
        client = get_client()
        console.print("[yellow]Creating agent...[/yellow]")
        result = client.create_agent(config)
        client.close()
        
        agent_id = result.get("id", "unknown")
        console.print(f"\n[green]✓ Agent created:[/green] {agent_id}")
        console.print(f"\n[dim]Monitor with:[/dim]")
        console.print(f"  agentctl logs {agent_id} --follow")
        console.print(f"  agentctl status {agent_id}")
        console.print(f"  agentctl ssh {agent_id}")
        
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Update `agentctl/cli/main.py`:**
```python
"""Main CLI entry point."""
import click
from rich.console import Console

console = Console()
VERSION = "0.1.0"


@click.group()
@click.version_option(version=VERSION)
@click.pass_context
def cli(ctx):
    """AgentCtl - Manage autonomous AI coding agents."""
    ctx.ensure_object(dict)


def register_commands():
    """Register all CLI commands."""
    from agentctl.cli.run import run
    cli.add_command(run)


register_commands()


if __name__ == "__main__":
    cli()
```

**File: `tests/unit/test_cli_run.py`**
```python
"""Tests for run command."""
from click.testing import CliRunner
from unittest.mock import patch, Mock
from agentctl.cli.main import cli


def test_run_requires_prompt():
    """Run should fail without prompt."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "Prompt is required" in result.output


def test_run_with_prompt():
    """Run should create agent with prompt."""
    with patch("agentctl.cli.run.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.create_agent.return_value = {"id": "test-agent-123"}
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "Build a todo app"])
        
        assert result.exit_code == 0
        assert "test-agent-123" in result.output
        mock_client.create_agent.assert_called_once()


def test_run_with_options():
    """Run should pass options to API."""
    with patch("agentctl.cli.run.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.create_agent.return_value = {"id": "test-123"}
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", 
            "--name", "my-agent",
            "--engine", "claude",
            "--timeout", "2h",
            "--spot",
            "Build something"
        ])
        
        assert result.exit_code == 0
        call_args = mock_client.create_agent.call_args[0][0]
        assert call_args.name == "my-agent"
        assert call_args.timeout_seconds == 7200
        assert call_args.spot is True


def test_run_with_prompt_file(tmp_path):
    """Run should read prompt from file."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Build from file")
    
    with patch("agentctl.cli.run.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.create_agent.return_value = {"id": "test-123"}
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--prompt-file", str(prompt_file)])
        
        assert result.exit_code == 0
        call_args = mock_client.create_agent.call_args[0][0]
        assert call_args.prompt == "Build from file"
```

**Test:**
```bash
pytest tests/unit/test_cli_run.py -v
```

**Commit:** `git commit -am "Add run command with tests"`

---

### Task 1.6: List Command

**Time:** 20 minutes

**File: `agentctl/cli/agents.py`**
```python
"""Agent management commands."""
import click
from rich.console import Console
from rich.table import Table

from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command("list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--format", "-o", "output_format", type=click.Choice(["table", "json"]), default="table")
def list_agents(status, output_format):
    """List all agents."""
    try:
        client = get_client()
        agents = client.list_agents(status=status)
        client.close()
        
        if output_format == "json":
            import json
            console.print(json.dumps(agents, indent=2))
            return
        
        if not agents:
            console.print("[dim]No agents found.[/dim]")
            return
        
        table = Table(title="Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Status")
        table.add_column("Engine")
        table.add_column("Created")
        table.add_column("IP")
        
        for agent in agents:
            status_style = {
                "running": "green",
                "stopped": "dim",
                "failed": "red",
                "starting": "yellow",
            }.get(agent.get("status", ""), "")
            
            table.add_row(
                agent.get("id", ""),
                f"[{status_style}]{agent.get('status', '')}[/{status_style}]",
                agent.get("engine", ""),
                agent.get("created_at", "")[:19] if agent.get("created_at") else "",
                agent.get("external_ip", "") or "-",
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@click.command()
@click.argument("agent_id")
def status(agent_id):
    """Get detailed status of an agent."""
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()
        
        console.print(f"\n[bold]Agent:[/bold] {agent.get('id')}")
        console.print(f"[bold]Status:[/bold] {agent.get('status')}")
        console.print(f"[bold]Engine:[/bold] {agent.get('engine')}")
        console.print(f"[bold]Prompt:[/bold] {agent.get('prompt', '')[:100]}...")
        
        if agent.get("repo"):
            console.print(f"[bold]Repo:[/bold] {agent.get('repo')}")
        if agent.get("branch"):
            console.print(f"[bold]Branch:[/bold] {agent.get('branch')}")
        if agent.get("external_ip"):
            console.print(f"[bold]IP:[/bold] {agent.get('external_ip')}")
        
        console.print(f"[bold]Created:[/bold] {agent.get('created_at')}")
        if agent.get("started_at"):
            console.print(f"[bold]Started:[/bold] {agent.get('started_at')}")
        
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@click.command()
@click.argument("agent_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def stop(agent_id, force):
    """Stop a running agent."""
    if not force:
        if not click.confirm(f"Stop agent {agent_id}?"):
            return
    
    try:
        client = get_client()
        result = client.stop_agent(agent_id)
        client.close()
        console.print(f"[green]✓ Agent {agent_id} stopped[/green]")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@click.command()
@click.argument("agent_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def delete(agent_id, force):
    """Delete an agent and its resources."""
    if not force:
        if not click.confirm(f"Delete agent {agent_id}? This cannot be undone."):
            return
    
    try:
        client = get_client()
        client.delete_agent(agent_id)
        client.close()
        console.print(f"[green]✓ Agent {agent_id} deleted[/green]")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Update `agentctl/cli/main.py` to add commands:**
```python
def register_commands():
    """Register all CLI commands."""
    from agentctl.cli.run import run
    from agentctl.cli.agents import list_agents, status, stop, delete
    
    cli.add_command(run)
    cli.add_command(list_agents)
    cli.add_command(status)
    cli.add_command(stop)
    cli.add_command(delete)
```

**File: `tests/unit/test_cli_agents.py`**
```python
"""Tests for agent management commands."""
from click.testing import CliRunner
from unittest.mock import patch, Mock
from agentctl.cli.main import cli


def test_list_empty():
    """List should handle empty results."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.list_agents.return_value = []
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ["list"])
        
        assert result.exit_code == 0
        assert "No agents found" in result.output


def test_list_with_agents():
    """List should display agents."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.list_agents.return_value = [
            {"id": "agent-1", "status": "running", "engine": "claude", "created_at": "2025-01-01T00:00:00"}
        ]
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ["list"])
        
        assert result.exit_code == 0
        assert "agent-1" in result.output


def test_status_command():
    """Status should show agent details."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.get_agent.return_value = {
            "id": "agent-1",
            "status": "running",
            "engine": "claude",
            "prompt": "Test prompt",
            "created_at": "2025-01-01T00:00:00"
        }
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "agent-1"])
        
        assert result.exit_code == 0
        assert "agent-1" in result.output
        assert "running" in result.output


def test_stop_with_confirmation():
    """Stop should require confirmation."""
    runner = CliRunner()
    result = runner.invoke(cli, ["stop", "agent-1"], input="n\n")
    assert result.exit_code == 0
    # Should not have called API


def test_stop_with_force():
    """Stop with --force should skip confirmation."""
    with patch("agentctl.cli.agents.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.stop_agent.return_value = {}
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ["stop", "--force", "agent-1"])
        
        assert result.exit_code == 0
        mock_client.stop_agent.assert_called_once_with("agent-1")
```

**Test:**
```bash
pytest tests/unit/test_cli_agents.py -v
```

**Commit:** `git commit -am "Add list, status, stop, delete commands with tests"`

---

### Task 1.7: Tell Command

**Time:** 15 minutes

**File: `agentctl/cli/tell.py`**
```python
"""Tell command - send instructions to running agent."""
import click
from rich.console import Console
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.argument("instruction", required=False)
@click.option("--file", "-f", "instruction_file", type=click.Path(exists=True), help="Read instruction from file")
def tell(agent_id, instruction, instruction_file):
    """Send an instruction to a running agent."""
    if instruction_file:
        with open(instruction_file) as f:
            instruction = f.read()
    
    if not instruction:
        console.print("[red]Error:[/red] Instruction required as argument or via --file")
        raise SystemExit(1)
    
    try:
        client = get_client()
        result = client.tell_agent(agent_id, instruction)
        client.close()
        console.print(f"[green]✓ Instruction sent to {agent_id}[/green]")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

**Update `agentctl/cli/main.py`:**
```python
def register_commands():
    """Register all CLI commands."""
    from agentctl.cli.run import run
    from agentctl.cli.agents import list_agents, status, stop, delete
    from agentctl.cli.tell import tell
    
    cli.add_command(run)
    cli.add_command(list_agents)
    cli.add_command(status)
    cli.add_command(stop)
    cli.add_command(delete)
    cli.add_command(tell)
```

**File: `tests/unit/test_cli_tell.py`**
```python
"""Tests for tell command."""
from click.testing import CliRunner
from unittest.mock import patch, Mock
from agentctl.cli.main import cli


def test_tell_requires_instruction():
    """Tell should fail without instruction."""
    runner = CliRunner()
    result = runner.invoke(cli, ["tell", "agent-1"])
    assert result.exit_code != 0
    assert "Instruction required" in result.output


def test_tell_with_instruction():
    """Tell should send instruction."""
    with patch("agentctl.cli.tell.get_client") as mock_get_client:
        mock_client = Mock()
        mock_client.tell_agent.return_value = {}
        mock_get_client.return_value = mock_client
        
        runner = CliRunner()
        result = runner.invoke(cli, ["tell", "agent-1", "Add tests"])
        
        assert result.exit_code == 0
        mock_client.tell_agent.assert_called_once_with("agent-1", "Add tests")
```

**Test:**
```bash
pytest tests/unit/test_cli_tell.py -v
```

**Commit:** `git commit -am "Add tell command with tests"`

---

## Phase 1 Checkpoint

At this point you should have:
- ✅ Core data models
- ✅ Configuration management
- ✅ CLI framework with commands: run, list, status, stop, delete, tell
- ✅ API client (mock-tested)
- ✅ All unit tests passing

**Run all tests:**
```bash
pytest tests/unit/ -v
```

**Verify CLI:**
```bash
agentctl --help
agentctl run --help
agentctl list --help
```

---

## Phase 2: Local Server

**Goal:** FastAPI server running locally that the CLI can talk to.

---

### Task 2.1: Server Skeleton

**Time:** 20 minutes

**File: `agentctl/server/app.py`**
```python
"""FastAPI application."""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from agentctl.server.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup."""
    init_db()
    yield


app = FastAPI(
    title="AgentCtl Master",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
```

**File: `agentctl/server/database.py`**
```python
"""SQLite database setup."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("agentctl.db")


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                engine TEXT NOT NULL,
                prompt TEXT NOT NULL,
                repo TEXT,
                branch TEXT,
                machine_type TEXT NOT NULL,
                spot INTEGER NOT NULL DEFAULT 0,
                timeout_seconds INTEGER,
                screenshot_interval INTEGER,
                screenshot_retention TEXT,
                gce_instance TEXT,
                external_ip TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                stopped_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS instructions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                instruction TEXT NOT NULL,
                delivered INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            );
        """)


@contextmanager
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
```

**File: `tests/unit/test_server_app.py`**
```python
"""Tests for server app."""
import pytest
from fastapi.testclient import TestClient
from agentctl.server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """Health endpoint should return healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

**Test:**
```bash
pytest tests/unit/test_server_app.py -v
```

**Commit:** `git commit -am "Add server skeleton with health endpoint"`

---

### Task 2.2: Agent Repository

**Time:** 25 minutes

**File: `agentctl/server/repository.py`**
```python
"""Agent data access layer."""
from datetime import datetime
from typing import Optional
import uuid

from agentctl.server.database import get_db
from agentctl.shared.models import Agent, AgentConfig, AgentStatus, EngineType


def generate_id() -> str:
    """Generate a short unique ID."""
    return f"agent-{uuid.uuid4().hex[:8]}"


def create_agent(config: AgentConfig) -> Agent:
    """Create a new agent in the database."""
    agent_id = config.name or generate_id()
    now = datetime.utcnow().isoformat()
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO agents (
                id, status, engine, prompt, repo, branch, 
                machine_type, spot, timeout_seconds,
                screenshot_interval, screenshot_retention, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            AgentStatus.PENDING.value,
            config.engine.value,
            config.prompt,
            config.repo,
            config.branch,
            config.machine_type,
            1 if config.spot else 0,
            config.timeout_seconds,
            config.screenshot_interval,
            config.screenshot_retention,
            now,
        ))
    
    return Agent(
        id=agent_id,
        status=AgentStatus.PENDING,
        config=config,
        created_at=datetime.fromisoformat(now),
    )


def get_agent(agent_id: str) -> Optional[Agent]:
    """Get agent by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
    
    if not row:
        return None
    
    return _row_to_agent(row)


def list_agents(status: Optional[str] = None) -> list[Agent]:
    """List all agents, optionally filtered by status."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM agents WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agents ORDER BY created_at DESC"
            ).fetchall()
    
    return [_row_to_agent(row) for row in rows]


def update_agent_status(agent_id: str, status: AgentStatus, **kwargs) -> bool:
    """Update agent status and optional fields."""
    updates = ["status = ?"]
    values = [status.value]
    
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(value)
    
    values.append(agent_id)
    
    with get_db() as conn:
        result = conn.execute(
            f"UPDATE agents SET {', '.join(updates)} WHERE id = ?",
            values
        )
        return result.rowcount > 0


def delete_agent(agent_id: str) -> bool:
    """Delete an agent."""
    with get_db() as conn:
        # Delete instructions first
        conn.execute("DELETE FROM instructions WHERE agent_id = ?", (agent_id,))
        result = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        return result.rowcount > 0


def add_instruction(agent_id: str, instruction: str) -> int:
    """Add instruction for an agent."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO instructions (agent_id, instruction, created_at) VALUES (?, ?, ?)",
            (agent_id, instruction, now)
        )
        return cursor.lastrowid


def _row_to_agent(row) -> Agent:
    """Convert database row to Agent object."""
    config = AgentConfig(
        prompt=row["prompt"],
        name=row["id"],
        engine=EngineType(row["engine"]),
        repo=row["repo"],
        branch=row["branch"],
        timeout_seconds=row["timeout_seconds"] or 14400,
        machine_type=row["machine_type"],
        spot=bool(row["spot"]),
        screenshot_interval=row["screenshot_interval"] or 300,
        screenshot_retention=row["screenshot_retention"] or "24h",
    )
    
    return Agent(
        id=row["id"],
        status=AgentStatus(row["status"]),
        config=config,
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        stopped_at=datetime.fromisoformat(row["stopped_at"]) if row["stopped_at"] else None,
        external_ip=row["external_ip"],
        gce_instance=row["gce_instance"],
    )
```

**File: `tests/unit/test_repository.py`**
```python
"""Tests for agent repository."""
import pytest
from pathlib import Path
from agentctl.server import database
from agentctl.server.repository import (
    create_agent, get_agent, list_agents, 
    update_agent_status, delete_agent
)
from agentctl.shared.models import AgentConfig, AgentStatus


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Use temporary database for tests."""
    database.DB_PATH = tmp_path / "test.db"
    database.init_db()
    yield
    database.DB_PATH.unlink(missing_ok=True)


def test_create_agent():
    """Create agent should insert into database."""
    config = AgentConfig(prompt="Test prompt")
    agent = create_agent(config)
    
    assert agent.id.startswith("agent-")
    assert agent.status == AgentStatus.PENDING
    assert agent.config.prompt == "Test prompt"


def test_create_agent_with_name():
    """Create agent should use provided name."""
    config = AgentConfig(prompt="Test", name="my-agent")
    agent = create_agent(config)
    assert agent.id == "my-agent"


def test_get_agent():
    """Get agent should retrieve from database."""
    config = AgentConfig(prompt="Test")
    created = create_agent(config)
    
    retrieved = get_agent(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.config.prompt == "Test"


def test_get_agent_not_found():
    """Get nonexistent agent should return None."""
    assert get_agent("nonexistent") is None


def test_list_agents():
    """List agents should return all agents."""
    create_agent(AgentConfig(prompt="Test 1"))
    create_agent(AgentConfig(prompt="Test 2"))
    
    agents = list_agents()
    assert len(agents) == 2


def test_list_agents_by_status():
    """List agents should filter by status."""
    create_agent(AgentConfig(prompt="Test 1"))
    
    running = list_agents(status="running")
    assert len(running) == 0
    
    pending = list_agents(status="pending")
    assert len(pending) == 1


def test_update_agent_status():
    """Update should change agent status."""
    config = AgentConfig(prompt="Test")
    agent = create_agent(config)
    
    update_agent_status(agent.id, AgentStatus.RUNNING, external_ip="1.2.3.4")
    
    updated = get_agent(agent.id)
    assert updated.status == AgentStatus.RUNNING
    assert updated.external_ip == "1.2.3.4"


def test_delete_agent():
    """Delete should remove agent."""
    config = AgentConfig(prompt="Test")
    agent = create_agent(config)
    
    result = delete_agent(agent.id)
    assert result is True
    assert get_agent(agent.id) is None
```

**Test:**
```bash
pytest tests/unit/test_repository.py -v
```

**Commit:** `git commit -am "Add agent repository with tests"`

---

### Task 2.3: Agent Routes

**Time:** 30 minutes

**File: `agentctl/server/routes/agents.py`**
```python
"""Agent API routes."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agentctl.server import repository
from agentctl.shared.models import AgentStatus, EngineType, AgentConfig

router = APIRouter()


class CreateAgentRequest(BaseModel):
    prompt: str
    name: Optional[str] = None
    engine: str = "claude"
    repo: Optional[str] = None
    branch: Optional[str] = None
    timeout_seconds: int = 14400
    machine_type: str = "e2-medium"
    spot: bool = False
    screenshot_interval: int = 300
    screenshot_retention: str = "24h"


class TellRequest(BaseModel):
    instruction: str


class AgentResponse(BaseModel):
    id: str
    status: str
    engine: str
    prompt: str
    repo: Optional[str]
    branch: Optional[str]
    machine_type: str
    spot: bool
    timeout_seconds: int
    external_ip: Optional[str]
    created_at: str
    started_at: Optional[str]
    stopped_at: Optional[str]

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(request: CreateAgentRequest):
    """Create a new agent."""
    config = AgentConfig(
        prompt=request.prompt,
        name=request.name,
        engine=EngineType(request.engine),
        repo=request.repo,
        branch=request.branch,
        timeout_seconds=request.timeout_seconds,
        machine_type=request.machine_type,
        spot=request.spot,
        screenshot_interval=request.screenshot_interval,
        screenshot_retention=request.screenshot_retention,
    )
    
    agent = repository.create_agent(config)
    
    # TODO: In later tasks, this will trigger VM creation
    # For now, just mark as "starting" to simulate
    repository.update_agent_status(agent.id, AgentStatus.STARTING)
    
    return _agent_to_response(agent)


@router.get("", response_model=AgentListResponse)
async def list_agents(status: Optional[str] = None):
    """List all agents."""
    agents = repository.list_agents(status=status)
    return AgentListResponse(
        agents=[_agent_to_response(a) for a in agents],
        total=len(agents)
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent details."""
    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return _agent_to_response(agent)


@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop a running agent."""
    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    if agent.status not in [AgentStatus.RUNNING, AgentStatus.STARTING]:
        raise HTTPException(status_code=400, detail=f"Agent is not running (status: {agent.status.value})")
    
    # TODO: In later tasks, this will stop the VM
    stopped_at = datetime.utcnow().isoformat()
    repository.update_agent_status(agent.id, AgentStatus.STOPPED, stopped_at=stopped_at)
    
    return {"id": agent_id, "status": "stopped", "stopped_at": stopped_at}


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    """Delete an agent."""
    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    # TODO: In later tasks, clean up GCS artifacts
    repository.delete_agent(agent_id)


@router.post("/{agent_id}/tell")
async def tell_agent(agent_id: str, request: TellRequest):
    """Send instruction to agent."""
    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    if agent.status != AgentStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Agent is not running")
    
    instruction_id = repository.add_instruction(agent_id, request.instruction)
    return {"agent_id": agent_id, "instruction_id": instruction_id, "status": "queued"}


def _agent_to_response(agent) -> AgentResponse:
    """Convert Agent model to response."""
    return AgentResponse(
        id=agent.id,
        status=agent.status.value,
        engine=agent.config.engine.value,
        prompt=agent.config.prompt,
        repo=agent.config.repo,
        branch=agent.config.branch,
        machine_type=agent.config.machine_type,
        spot=agent.config.spot,
        timeout_seconds=agent.config.timeout_seconds,
        external_ip=agent.external_ip,
        created_at=agent.created_at.isoformat(),
        started_at=agent.started_at.isoformat() if agent.started_at else None,
        stopped_at=agent.stopped_at.isoformat() if agent.stopped_at else None,
    )
```

**Update `agentctl/server/app.py`:**
```python
"""FastAPI application."""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from agentctl.server.database import init_db
from agentctl.server.routes import agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup."""
    init_db()
    yield


app = FastAPI(
    title="AgentCtl Master",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# Register routes
app.include_router(agents.router, prefix="/agents", tags=["agents"])
```

**File: `tests/integration/test_api.py`**
```python
"""Integration tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from agentctl.server import database
from agentctl.server.app import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Use temporary database."""
    database.DB_PATH = tmp_path / "test.db"
    database.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_create_and_get_agent(client):
    """Full create/get cycle."""
    # Create
    response = client.post("/agents", json={
        "prompt": "Build something",
        "engine": "claude"
    })
    assert response.status_code == 201
    data = response.json()
    agent_id = data["id"]
    
    # Get
    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["prompt"] == "Build something"


def test_list_agents(client):
    """List should return created agents."""
    client.post("/agents", json={"prompt": "Test 1"})
    client.post("/agents", json={"prompt": "Test 2"})
    
    response = client.get("/agents")
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_stop_agent(client):
    """Stop should change status."""
    # Create
    response = client.post("/agents", json={"prompt": "Test"})
    agent_id = response.json()["id"]
    
    # Update to running (simulate VM started)
    from agentctl.server import repository
    from agentctl.shared.models import AgentStatus
    repository.update_agent_status(agent_id, AgentStatus.RUNNING)
    
    # Stop
    response = client.post(f"/agents/{agent_id}/stop")
    assert response.status_code == 200
    
    # Verify stopped
    response = client.get(f"/agents/{agent_id}")
    assert response.json()["status"] == "stopped"


def test_delete_agent(client):
    """Delete should remove agent."""
    response = client.post("/agents", json={"prompt": "Test"})
    agent_id = response.json()["id"]
    
    response = client.delete(f"/agents/{agent_id}")
    assert response.status_code == 204
    
    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 404


def test_agent_not_found(client):
    """Should return 404 for nonexistent agent."""
    response = client.get("/agents/nonexistent")
    assert response.status_code == 404
```

**Test:**
```bash
pytest tests/integration/test_api.py -v
```

**Commit:** `git commit -am "Add agent routes with integration tests"`

---

## Phase 2 Checkpoint

At this point:
- ✅ FastAPI server with /health and /agents endpoints
- ✅ SQLite persistence
- ✅ CLI commands work against local server

**Manual test:**
```bash
# Terminal 1: Start server
uvicorn agentctl.server.app:app --reload

# Terminal 2: Test CLI
export AGENTCTL_MASTER_URL=http://localhost:8000
agentctl run "Test prompt"
agentctl list
agentctl stop <agent-id> --force
```

---

## Phase 3: GCP Integration

**Goal:** Connect to real GCP services - Secret Manager, GCS, and Compute Engine.

---

### Task 3.1: GCP Client Utilities

**Time:** 20 minutes

**File: `agentctl/shared/gcp.py`**
```python
"""GCP client utilities."""
import subprocess
from typing import Optional


class GCPError(Exception):
    """GCP operation failed."""
    pass


def get_project_id() -> Optional[str]:
    """Get current GCP project from gcloud config."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True
        )
        project = result.stdout.strip()
        return project if project else None
    except subprocess.CalledProcessError:
        return None


def verify_auth() -> bool:
    """Verify gcloud authentication."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


def enable_api(project: str, api: str) -> None:
    """Enable a GCP API."""
    try:
        subprocess.run(
            ["gcloud", "services", "enable", api, f"--project={project}"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        raise GCPError(f"Failed to enable {api}: {e.stderr}")
```

**File: `tests/unit/test_gcp.py`**
```python
"""Tests for GCP utilities."""
import pytest
from unittest.mock import patch, Mock
from agentctl.shared.gcp import get_project_id, verify_auth


def test_get_project_id_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="my-project\n", returncode=0)
        assert get_project_id() == "my-project"


def test_verify_auth_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(stdout="user@example.com\n", returncode=0)
        assert verify_auth() is True
```

**Test:** `pytest tests/unit/test_gcp.py -v`

**Commit:** `git commit -am "Add GCP client utilities"`

---

### Task 3.2: Secret Manager Service

**Time:** 25 minutes

**File: `agentctl/server/services/secret_manager.py`**
```python
"""GCP Secret Manager service."""
from typing import Optional
from google.cloud import secretmanager
from google.api_core import exceptions


class SecretManagerService:
    """Manage secrets in GCP Secret Manager."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        self.parent = f"projects/{project_id}"
    
    def set_secret(self, secret_id: str, value: str) -> str:
        """Create or update a secret."""
        secret_name = f"{self.parent}/secrets/{secret_id}"
        
        # Create secret if doesn't exist
        try:
            self.client.create_secret(
                request={
                    "parent": self.parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except exceptions.AlreadyExists:
            pass
        
        # Add new version
        version = self.client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": value.encode("utf-8")},
            }
        )
        return version.name
    
    def get_secret(self, secret_id: str) -> Optional[str]:
        """Get latest secret value."""
        try:
            name = f"{self.parent}/secrets/{secret_id}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("utf-8")
        except exceptions.NotFound:
            return None
    
    def list_secrets(self) -> list[str]:
        """List all secret names."""
        secrets = self.client.list_secrets(request={"parent": self.parent})
        return [s.name.split("/")[-1] for s in secrets]
```

**Test:** Manual test with real GCP project (integration)

**Commit:** `git commit -am "Add Secret Manager service"`

---

### Task 3.3: Storage Manager Service

**Time:** 25 minutes

**File: `agentctl/server/services/storage_manager.py`**
```python
"""GCP Cloud Storage service."""
from pathlib import Path
from typing import Optional
from google.cloud import storage
from google.api_core import exceptions


class StorageManager:
    """Manage GCS bucket for agent artifacts."""
    
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket_name = bucket_name
        self._bucket = None
    
    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket
    
    def create_bucket(self, location: str = "us-central1") -> bool:
        """Create the bucket if it doesn't exist."""
        try:
            self.client.create_bucket(self.bucket_name, location=location)
            return True
        except exceptions.Conflict:
            return False  # Already exists
    
    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload a file to GCS."""
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket_name}/{remote_path}"
    
    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download a file from GCS."""
        blob = self.bucket.blob(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))
    
    def list_files(self, prefix: str = "") -> list[str]:
        """List files with given prefix."""
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
    
    def delete_files(self, prefix: str) -> int:
        """Delete all files with prefix. Returns count deleted."""
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        for blob in blobs:
            blob.delete()
        return len(blobs)
```

**Commit:** `git commit -am "Add Storage Manager service"`

---

### Task 3.4: VM Manager Service

**Time:** 40 minutes

**File: `agentctl/server/services/vm_manager.py`**
```python
"""GCP Compute Engine VM management."""
import time
from typing import Optional
from google.cloud import compute_v1


class VMManager:
    """Manage GCE VM instances for agents."""
    
    def __init__(self, project: str, zone: str):
        self.project = project
        self.zone = zone
        self.client = compute_v1.InstancesClient()
        self.ops_client = compute_v1.ZoneOperationsClient()
    
    def create_instance(
        self,
        name: str,
        machine_type: str,
        startup_script: str,
        spot: bool = False,
        service_account: Optional[str] = None,
        labels: Optional[dict] = None,
    ) -> dict:
        """Create a new VM instance."""
        instance = compute_v1.Instance()
        instance.name = name
        instance.machine_type = f"zones/{self.zone}/machineTypes/{machine_type}"
        
        # Boot disk - Ubuntu 22.04
        disk = compute_v1.AttachedDisk()
        disk.boot = True
        disk.auto_delete = True
        init_params = compute_v1.AttachedDiskInitializeParams()
        init_params.source_image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
        init_params.disk_size_gb = 50
        disk.initialize_params = init_params
        instance.disks = [disk]
        
        # Network with external IP
        network = compute_v1.NetworkInterface()
        network.network = "global/networks/default"
        access = compute_v1.AccessConfig()
        access.name = "External NAT"
        access.type_ = "ONE_TO_ONE_NAT"
        network.access_configs = [access]
        instance.network_interfaces = [network]
        
        # Startup script
        metadata = compute_v1.Metadata()
        metadata.items = [compute_v1.Items(key="startup-script", value=startup_script)]
        instance.metadata = metadata
        
        # Service account
        if service_account:
            sa = compute_v1.ServiceAccount()
            sa.email = service_account
            sa.scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            instance.service_accounts = [sa]
        
        # Labels
        instance.labels = labels or {}
        instance.labels["agentctl"] = "true"
        
        # Spot instance
        if spot:
            sched = compute_v1.Scheduling()
            sched.preemptible = True
            sched.automatic_restart = False
            instance.scheduling = sched
        
        # Create and wait
        op = self.client.insert(project=self.project, zone=self.zone, instance_resource=instance)
        self._wait_for_operation(op.name)
        
        # Return instance info
        return self.get_instance(name)
    
    def get_instance(self, name: str) -> Optional[dict]:
        """Get instance details."""
        try:
            inst = self.client.get(project=self.project, zone=self.zone, instance=name)
            return {
                "name": inst.name,
                "status": inst.status,
                "external_ip": self._get_external_ip(inst),
                "machine_type": inst.machine_type.split("/")[-1],
            }
        except Exception:
            return None
    
    def delete_instance(self, name: str) -> bool:
        """Delete a VM instance."""
        try:
            op = self.client.delete(project=self.project, zone=self.zone, instance=name)
            self._wait_for_operation(op.name)
            return True
        except Exception:
            return False
    
    def _get_external_ip(self, instance) -> Optional[str]:
        """Extract external IP from instance."""
        for iface in instance.network_interfaces:
            for config in iface.access_configs:
                if config.nat_i_p:
                    return config.nat_i_p
        return None
    
    def _wait_for_operation(self, operation_name: str, timeout: int = 300):
        """Wait for a zone operation to complete."""
        start = time.time()
        while time.time() - start < timeout:
            op = self.ops_client.get(project=self.project, zone=self.zone, operation=operation_name)
            if op.status == compute_v1.Operation.Status.DONE:
                if op.error:
                    raise Exception(f"Operation failed: {op.error}")
                return
            time.sleep(2)
        raise TimeoutError(f"Operation {operation_name} timed out")
```

**Commit:** `git commit -am "Add VM Manager service"`

---

### Task 3.5: Init Command

**Time:** 35 minutes

**File: `agentctl/cli/init_cmd.py`**
```python
"""Init command - set up GCP project."""
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from getpass import getpass
import secrets

from agentctl.shared.config import Config, CONFIG_DIR
from agentctl.shared.gcp import get_project_id, verify_auth, enable_api, GCPError

console = Console()


@click.command()
@click.option("--project", "-p", help="GCP project ID")
@click.option("--region", default="us-central1", help="GCP region")
@click.option("--zone", default="us-central1-a", help="GCP zone")
def init(project, region, zone):
    """Initialize AgentCtl in a GCP project."""
    
    # Step 1: Verify gcloud auth
    console.print("\n[bold]Initializing AgentCtl[/bold]\n")
    
    if not verify_auth():
        console.print("[red]Error:[/red] Not authenticated. Run 'gcloud auth login' first.")
        raise SystemExit(1)
    console.print("[green]✓[/green] GCP authentication verified")
    
    # Step 2: Get project
    if not project:
        project = get_project_id()
        if not project:
            project = click.prompt("GCP Project ID")
    console.print(f"[green]✓[/green] Using project: {project}")
    
    # Step 3: Enable APIs
    apis = [
        "compute.googleapis.com",
        "secretmanager.googleapis.com", 
        "storage.googleapis.com",
    ]
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Enabling APIs...", total=len(apis))
        for api in apis:
            try:
                enable_api(project, api)
            except GCPError as e:
                console.print(f"[yellow]Warning:[/yellow] {e}")
            progress.advance(task)
    console.print("[green]✓[/green] APIs enabled")
    
    # Step 4: Create GCS bucket
    bucket_name = f"agentctl-{project}-{secrets.token_hex(4)}"
    try:
        from agentctl.server.services.storage_manager import StorageManager
        storage = StorageManager(bucket_name)
        storage.create_bucket(location=region)
        console.print(f"[green]✓[/green] Created bucket: {bucket_name}")
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not create bucket: {e}")
        bucket_name = click.prompt("Enter existing bucket name")
    
    # Step 5: Store API keys
    console.print("\n[bold]API Keys[/bold]")
    console.print("[dim]These will be stored in GCP Secret Manager[/dim]\n")
    
    from agentctl.server.services.secret_manager import SecretManagerService
    secrets_svc = SecretManagerService(project)
    
    anthropic_key = getpass("Anthropic API Key: ")
    if anthropic_key:
        secrets_svc.set_secret("anthropic-api-key", anthropic_key)
        console.print("[green]✓[/green] Anthropic key saved")
    
    github_token = getpass("GitHub Token (optional, press Enter to skip): ")
    if github_token:
        secrets_svc.set_secret("github-token", github_token)
        console.print("[green]✓[/green] GitHub token saved")
    
    # Step 6: Save config
    config = Config(
        gcp_project=project,
        gcp_region=region,
        gcp_zone=zone,
        gcs_bucket=bucket_name,
        master_server_url="http://localhost:8000",  # Default to local for now
    )
    config.save()
    console.print(f"[green]✓[/green] Config saved to {CONFIG_DIR / 'config.yaml'}")
    
    # Done
    console.print("\n[bold green]✓ AgentCtl initialized![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Start the server: uvicorn agentctl.server.app:app")
    console.print("  2. Run an agent: agentctl run 'Build something cool'")
```

**Update `agentctl/cli/main.py`:**
```python
def register_commands():
    from agentctl.cli.run import run
    from agentctl.cli.agents import list_agents, status, stop, delete
    from agentctl.cli.tell import tell
    from agentctl.cli.init_cmd import init
    
    cli.add_command(init)
    cli.add_command(run)
    cli.add_command(list_agents)
    cli.add_command(status)
    cli.add_command(stop)
    cli.add_command(delete)
    cli.add_command(tell)
```

**Test:** Manual test with real GCP project

**Commit:** `git commit -am "Add init command"`

---

### Task 3.6: Wire Up VM Creation

**Time:** 30 minutes

Update the server to actually create VMs when agents are created.

**File: `agentctl/server/services/startup_script.py`**
```python
"""Generate VM startup scripts."""

STARTUP_SCRIPT_TEMPLATE = '''#!/bin/bash
set -e

# --- Configuration ---
AGENT_ID="{agent_id}"
MASTER_URL="{master_url}"
PROJECT="{project}"
ENGINE="{engine}"
PROMPT_FILE="/workspace/.prompt"

echo "=== AgentCtl Agent Starting ==="
echo "Agent ID: $AGENT_ID"

# --- Install Dependencies ---
apt-get update
apt-get install -y git curl python3 python3-pip nodejs npm jq

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# --- Fetch Secrets ---
ANTHROPIC_KEY=$(gcloud secrets versions access latest --secret=anthropic-api-key)
export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"

# GitHub token (optional)
GITHUB_TOKEN=$(gcloud secrets versions access latest --secret=github-token 2>/dev/null || echo "")
if [ -n "$GITHUB_TOKEN" ]; then
    export GITHUB_TOKEN
fi

# --- Setup Workspace ---
mkdir -p /workspace
cd /workspace

# Clone repo if specified
REPO="{repo}"
BRANCH="{branch}"
if [ -n "$REPO" ]; then
    if [ -n "$GITHUB_TOKEN" ]; then
        git clone "https://${{GITHUB_TOKEN}}@${{REPO#https://}}" repo
    else
        git clone "$REPO" repo
    fi
    cd repo
    if [ -n "$BRANCH" ]; then
        git checkout -B "$BRANCH"
    fi
fi

# --- Save Prompt ---
cat > "$PROMPT_FILE" << 'PROMPT_END'
{prompt}
PROMPT_END

# --- Report Ready ---
curl -X POST "$MASTER_URL/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "running"}}' || true

# --- Run Agent ---
echo "Starting $ENGINE..."
if [ "$ENGINE" = "claude" ]; then
    cd /workspace/repo 2>/dev/null || cd /workspace
    timeout {timeout}s claude --dangerously-skip-permissions --print "$(cat $PROMPT_FILE)" || true
fi

# --- Cleanup ---
echo "Agent finished"
curl -X POST "$MASTER_URL/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "completed"}}' || true

# Final git commit
cd /workspace/repo 2>/dev/null && git add -A && git commit -m "Final auto-commit" && git push || true

# Shutdown
shutdown -h now
'''


def generate_startup_script(
    agent_id: str,
    prompt: str,
    engine: str,
    master_url: str,
    project: str,
    repo: str = "",
    branch: str = "",
    timeout: int = 14400,
) -> str:
    """Generate startup script for agent VM."""
    return STARTUP_SCRIPT_TEMPLATE.format(
        agent_id=agent_id,
        prompt=prompt.replace("'", "'\"'\"'"),  # Escape single quotes
        engine=engine,
        master_url=master_url,
        project=project,
        repo=repo or "",
        branch=branch or "",
        timeout=timeout,
    )
```

**Update `agentctl/server/routes/agents.py` - modify create_agent:**
```python
@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(request: CreateAgentRequest):
    """Create a new agent."""
    from agentctl.shared.config import Config
    
    config = AgentConfig(
        prompt=request.prompt,
        name=request.name,
        engine=EngineType(request.engine),
        repo=request.repo,
        branch=request.branch,
        timeout_seconds=request.timeout_seconds,
        machine_type=request.machine_type,
        spot=request.spot,
    )
    
    agent = repository.create_agent(config)
    
    # Load app config for GCP settings
    app_config = Config.load()
    
    if app_config.gcp_project:
        # Create actual VM
        from agentctl.server.services.vm_manager import VMManager
        from agentctl.server.services.startup_script import generate_startup_script
        
        startup_script = generate_startup_script(
            agent_id=agent.id,
            prompt=config.prompt,
            engine=config.engine.value,
            master_url=app_config.master_server_url or "http://localhost:8000",
            project=app_config.gcp_project,
            repo=config.repo or "",
            branch=config.branch or "",
            timeout=config.timeout_seconds,
        )
        
        vm = VMManager(app_config.gcp_project, app_config.gcp_zone)
        instance_name = f"agent-{agent.id}"
        
        try:
            result = vm.create_instance(
                name=instance_name,
                machine_type=config.machine_type,
                startup_script=startup_script,
                spot=config.spot,
                labels={"agent-id": agent.id},
            )
            
            repository.update_agent_status(
                agent.id, 
                AgentStatus.STARTING,
                gce_instance=instance_name,
                external_ip=result.get("external_ip"),
            )
        except Exception as e:
            repository.update_agent_status(agent.id, AgentStatus.FAILED)
            raise HTTPException(500, f"Failed to create VM: {e}")
    else:
        # No GCP configured, just mark as starting (for local dev)
        repository.update_agent_status(agent.id, AgentStatus.STARTING)
    
    return _agent_to_response(repository.get_agent(agent.id))
```

**Commit:** `git commit -am "Wire up VM creation in agent routes"`

---

### Task 3.7: SSH Command

**Time:** 20 minutes

**File: `agentctl/cli/ssh.py`**
```python
"""SSH command - connect to agent VM."""
import subprocess
import click
from rich.console import Console

from agentctl.shared.config import Config
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--command", "-c", "remote_cmd", help="Command to run instead of interactive shell")
def ssh(agent_id, remote_cmd):
    """SSH into an agent's VM."""
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    
    if not agent.get("external_ip"):
        console.print(f"[red]Error:[/red] Agent {agent_id} has no external IP")
        raise SystemExit(1)
    
    config = Config.load()
    instance_name = f"agent-{agent_id}"
    
    cmd = [
        "gcloud", "compute", "ssh", instance_name,
        f"--zone={config.gcp_zone}",
        f"--project={config.gcp_project}",
    ]
    
    if remote_cmd:
        cmd.extend(["--command", remote_cmd])
    
    # Execute SSH
    subprocess.run(cmd)
```

**Update `agentctl/cli/main.py` to add ssh command**

**Commit:** `git commit -am "Add SSH command"`

---

### Task 3.8: Logs Command

**Time:** 25 minutes

**File: `agentctl/cli/logs.py`**
```python
"""Logs command - view agent output."""
import subprocess
import click
from rich.console import Console

from agentctl.shared.config import Config
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--follow", "-f", is_flag=True, help="Stream logs continuously")
@click.option("--tail", "-n", default=100, help="Number of lines to show")
def logs(agent_id, follow, tail):
    """View agent logs."""
    try:
        client = get_client()
        agent = client.get_agent(agent_id)
        client.close()
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    
    config = Config.load()
    instance_name = f"agent-{agent_id}"
    
    # Use gcloud to get serial console output (startup script logs)
    cmd = [
        "gcloud", "compute", "instances", "get-serial-port-output",
        instance_name,
        f"--zone={config.gcp_zone}",
        f"--project={config.gcp_project}",
    ]
    
    if follow:
        # For follow mode, SSH in and tail the log file
        ssh_cmd = [
            "gcloud", "compute", "ssh", instance_name,
            f"--zone={config.gcp_zone}",
            f"--project={config.gcp_project}",
            "--command", f"tail -f /var/log/syslog | grep -v CRON"
        ]
        subprocess.run(ssh_cmd)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines[-tail:]:
                console.print(line)
        else:
            console.print(f"[red]Error:[/red] {result.stderr}")
```

**Update `agentctl/cli/main.py` to add logs command**

**Commit:** `git commit -am "Add logs command"`

---

## Phase 3 Checkpoint

At this point:
- ✅ GCP utilities (auth, project detection)
- ✅ Secret Manager integration
- ✅ GCS bucket management  
- ✅ VM creation/deletion
- ✅ Init command sets up GCP
- ✅ SSH and logs commands work

**Manual test with real GCP:**
```bash
agentctl init
agentctl run --timeout 10m "Create a hello.py that prints hello world"
agentctl list
agentctl logs <agent-id>
agentctl ssh <agent-id>
agentctl stop <agent-id>
```

---

## Phase 4: Agent VM & Runner

**Goal:** The agent VM runs Claude Code and manages itself properly.

---

### Task 4.1: Improved Startup Script

**Time:** 30 minutes

Enhance the startup script with git auto-commit and proper cleanup.

**Update `agentctl/server/services/startup_script.py`:**
```python
STARTUP_SCRIPT_TEMPLATE = '''#!/bin/bash
set -e

# === Configuration ===
AGENT_ID="{agent_id}"
MASTER_URL="{master_url}"
PROJECT="{project}"
ENGINE="{engine}"
TIMEOUT={timeout}
SCREENSHOT_INTERVAL={screenshot_interval}

log() {{ echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }}

log "=== AgentCtl Agent Starting ==="
log "Agent ID: $AGENT_ID"

# === Install Dependencies ===
log "Installing dependencies..."
apt-get update -qq
apt-get install -y -qq git curl python3 python3-pip nodejs npm jq scrot xvfb

# Install Claude Code
npm install -g @anthropic-ai/claude-code 2>/dev/null || true

# === Fetch Secrets from Instance Metadata ===
# NOTE: Secrets are injected by master server via metadata, NOT fetched from Secret Manager.
# This means agent VMs don't need secretmanager IAM permissions (more secure).
log "Loading secrets from metadata..."
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
METADATA_HEADER="Metadata-Flavor: Google"

export ANTHROPIC_API_KEY=$(curl -s "$METADATA_URL/anthropic-api-key" -H "$METADATA_HEADER" || echo "")
GITHUB_TOKEN=$(curl -s "$METADATA_URL/github-token" -H "$METADATA_HEADER" 2>/dev/null || echo "")

if [ -z "$ANTHROPIC_API_KEY" ]; then
    log "ERROR: No Anthropic API key found in metadata!"
    exit 1
fi

if [ -n "$GITHUB_TOKEN" ]; then
    export GITHUB_TOKEN
    git config --global credential.helper store
    echo "https://$GITHUB_TOKEN:x-oauth-basic@github.com" > ~/.git-credentials
fi

# === Setup Workspace ===
mkdir -p /workspace
cd /workspace

REPO="{repo}"
BRANCH="{branch}"
if [ -n "$REPO" ]; then
    log "Cloning $REPO..."
    git clone "$REPO" repo 2>/dev/null || git clone "https://$GITHUB_TOKEN@${{REPO#https://}}" repo
    cd repo
    git config user.email "agent@agentctl.local"
    git config user.name "AgentCtl Agent"
    if [ -n "$BRANCH" ]; then
        git checkout -B "$BRANCH"
        git push -u origin "$BRANCH" 2>/dev/null || true
    fi
fi

# === Save Prompt ===
cat > /workspace/.prompt << 'PROMPT_END'
{prompt}
PROMPT_END

# === Auto-commit Function ===
auto_commit() {{
    cd /workspace/repo 2>/dev/null || return
    if [ -n "$(git status --porcelain)" ]; then
        git add -A
        git commit -m "Auto-commit: $(date '+%Y-%m-%d %H:%M:%S')" || true
        git push || true
    fi
}}

# === Screenshot Function ===
take_screenshot() {{
    mkdir -p /workspace/screenshots
    DISPLAY=:99 scrot "/workspace/screenshots/$(date +%s).png" 2>/dev/null || true
}}

# === Start Background Services ===
# Virtual display for screenshots
Xvfb :99 -screen 0 1280x720x24 &
export DISPLAY=:99

# Auto-commit every 5 minutes
while true; do sleep 300; auto_commit; done &
AUTOCOMMIT_PID=$!

# Screenshots (if enabled)
if [ "$SCREENSHOT_INTERVAL" -gt 0 ]; then
    while true; do sleep $SCREENSHOT_INTERVAL; take_screenshot; done &
fi

# === Report Ready ===
log "Reporting ready status..."
curl -s -X POST "$MASTER_URL/v1/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "running"}}' || true

# === Run Agent ===
log "Starting $ENGINE with timeout ${{TIMEOUT}}s..."
cd /workspace/repo 2>/dev/null || cd /workspace

PROMPT=$(cat /workspace/.prompt)

if [ "$ENGINE" = "claude" ]; then
    timeout $TIMEOUT claude --dangerously-skip-permissions --print "$PROMPT" 2>&1 | tee /workspace/agent.log || true
fi

# === Cleanup ===
log "Agent task completed"

# Kill background jobs
kill $AUTOCOMMIT_PID 2>/dev/null || true

# Final commit
auto_commit
log "Final commit done"

# Upload screenshots to GCS
gsutil -m cp /workspace/screenshots/* gs://{bucket}/$AGENT_ID/screenshots/ 2>/dev/null || true

# Report completion
curl -s -X POST "$MASTER_URL/internal/heartbeat" \
    -H "Content-Type: application/json" \
    -d '{{"agent_id": "'"$AGENT_ID"'", "status": "completed"}}' || true

log "Shutting down..."
shutdown -h now
'''
```

**Commit:** `git commit -am "Improve startup script with auto-commit and screenshots"`

---

### Task 4.2: Internal Heartbeat Endpoint

**Time:** 20 minutes

Add endpoint for agents to report status.

**File: `agentctl/server/routes/internal.py`**
```python
"""Internal endpoints for agent communication."""
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from agentctl.server import repository
from agentctl.shared.models import AgentStatus

router = APIRouter()


class HeartbeatRequest(BaseModel):
    agent_id: str
    status: str
    message: str = ""


@router.post("/heartbeat")
async def heartbeat(request: HeartbeatRequest):
    """Receive heartbeat from agent."""
    status_map = {
        "running": AgentStatus.RUNNING,
        "completed": AgentStatus.STOPPED,
        "failed": AgentStatus.FAILED,
    }
    
    new_status = status_map.get(request.status)
    if new_status:
        updates = {}
        if new_status == AgentStatus.RUNNING:
            updates["started_at"] = datetime.utcnow().isoformat()
        elif new_status in [AgentStatus.STOPPED, AgentStatus.FAILED]:
            updates["stopped_at"] = datetime.utcnow().isoformat()
        
        repository.update_agent_status(request.agent_id, new_status, **updates)
    
    return {"status": "ok"}
```

**Update `agentctl/server/app.py`:**
```python
from agentctl.server.routes import agents, internal

app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(internal.router, prefix="/internal", tags=["internal"])
```

**Commit:** `git commit -am "Add internal heartbeat endpoint"`

---

### Task 4.3: Screenshots CLI Command

**Time:** 20 minutes

**File: `agentctl/cli/screenshots.py`**
```python
"""Screenshots command - view agent screenshots."""
import click
from pathlib import Path
from rich.console import Console

from agentctl.shared.config import Config
from agentctl.shared.api_client import get_client, APIError

console = Console()


@click.command()
@click.argument("agent_id")
@click.option("--download", "-d", is_flag=True, help="Download screenshots")
@click.option("--output", "-o", default="./screenshots", help="Download directory")
@click.option("--limit", "-n", default=10, help="Number of screenshots to list/download")
def screenshots(agent_id, download, output, limit):
    """List or download agent screenshots."""
    config = Config.load()
    
    if not config.gcs_bucket:
        console.print("[red]Error:[/red] Not initialized. Run 'agentctl init' first.")
        raise SystemExit(1)
    
    from agentctl.server.services.storage_manager import StorageManager
    storage = StorageManager(config.gcs_bucket)
    
    prefix = f"{agent_id}/screenshots/"
    files = storage.list_files(prefix)
    
    if not files:
        console.print("[dim]No screenshots found.[/dim]")
        return
    
    # Sort by name (timestamp) descending
    files = sorted(files, reverse=True)[:limit]
    
    if download:
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for f in files:
            filename = f.split("/")[-1]
            local_path = output_path / filename
            storage.download_file(f, local_path)
            console.print(f"[green]✓[/green] Downloaded {filename}")
        
        console.print(f"\nScreenshots saved to {output_path}")
    else:
        console.print(f"[bold]Screenshots for {agent_id}:[/bold]\n")
        for f in files:
            filename = f.split("/")[-1]
            console.print(f"  {filename}")
        console.print(f"\nUse --download to save locally")
```

**Update `agentctl/cli/main.py` to add screenshots command**

**Commit:** `git commit -am "Add screenshots command"`

---

### Task 4.4: Stop Command - Delete VM

**Time:** 15 minutes

Update stop to actually delete the VM.

**Update `agentctl/server/routes/agents.py`:**
```python
@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop a running agent."""
    from agentctl.shared.config import Config
    
    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    if agent.status not in [AgentStatus.RUNNING, AgentStatus.STARTING]:
        raise HTTPException(status_code=400, detail=f"Agent is not running")
    
    # Delete VM if exists
    config = Config.load()
    if config.gcp_project and agent.gce_instance:
        from agentctl.server.services.vm_manager import VMManager
        vm = VMManager(config.gcp_project, config.gcp_zone)
        vm.delete_instance(agent.gce_instance)
    
    stopped_at = datetime.utcnow().isoformat()
    repository.update_agent_status(agent.id, AgentStatus.STOPPED, stopped_at=stopped_at)
    
    return {"id": agent_id, "status": "stopped"}
```

**Commit:** `git commit -am "Update stop command to delete VM"`

---

## Phase 4 Checkpoint

At this point:
- ✅ Improved startup script with auto-commit
- ✅ Agent heartbeat reporting
- ✅ Screenshots capture and download
- ✅ Proper VM cleanup on stop

---

## Final Integration Test

Run this complete workflow:

```bash
# 1. Initialize
agentctl init

# 2. Start server (in separate terminal)
uvicorn agentctl.server.app:app --host 0.0.0.0 --port 8000

# 3. Create agent
agentctl run \
  --name test-agent \
  --timeout 15m \
  --repo https://github.com/YOUR_USER/test-repo \
  --branch feature/ai-test \
  "Create a Python script that prints 'Hello from AgentCtl'"

# 4. Monitor
agentctl list
agentctl status test-agent
agentctl logs test-agent --follow

# 5. Check screenshots
agentctl screenshots test-agent

# 6. SSH in
agentctl ssh test-agent

# 7. Send instruction
agentctl tell test-agent "Also add a docstring to the script"

# 8. Stop
agentctl stop test-agent

# 9. Cleanup
agentctl delete test-agent
```

---

## Summary of Changes from Original Plan

1. **Smaller tasks** - Each task is 15-30 minutes, not hours
2. **Tests first** - Every task includes test code
3. **Local first** - Phase 1-2 work without GCP
4. **Explicit interfaces** - Data models defined upfront
5. **No Web UI in MVP** - Moved to post-MVP backlog
6. **Clear dependencies** - Tasks build on each other explicitly
7. **Integration tests** - API tested end-to-end
8. **Removed hand-wavy items** - "Research Codex" replaced with concrete steps

Would you like me to continue with Phase 3 (GCP Integration) and Phase 4 (Agent VM) in similar detail?
