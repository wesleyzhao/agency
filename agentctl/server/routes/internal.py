"""Internal endpoints for agent communication."""
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

from agentctl.server import repository
from agentctl.shared.models import AgentStatus

router = APIRouter()


def _utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


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
            updates["started_at"] = _utcnow().isoformat()
        elif new_status in [AgentStatus.STOPPED, AgentStatus.FAILED]:
            updates["stopped_at"] = _utcnow().isoformat()

        repository.update_agent_status(request.agent_id, new_status, **updates)

    return {"status": "ok"}
