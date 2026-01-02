"""Agent data access layer."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from agentctl.server.database import get_db
from agentctl.shared.models import Agent, AgentConfig, AgentStatus, EngineType


def _utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_id() -> str:
    """Generate a short unique ID."""
    return f"agent-{uuid.uuid4().hex[:8]}"


def create_agent(config: AgentConfig) -> Agent:
    """Create a new agent in the database."""
    agent_id = config.name or generate_id()
    now = _utcnow().isoformat()

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
    now = _utcnow().isoformat()
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
