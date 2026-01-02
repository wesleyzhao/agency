"""Core data models used across CLI and server."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def _utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


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
    created_at: datetime = field(default_factory=_utcnow)
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
