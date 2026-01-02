"""Agent API routes."""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agentctl.server import repository
from agentctl.shared.models import AgentStatus, EngineType, AgentConfig

router = APIRouter()


def _utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


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
        screenshot_interval=request.screenshot_interval,
        screenshot_retention=request.screenshot_retention,
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
    from agentctl.shared.config import Config

    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    if agent.status not in [AgentStatus.RUNNING, AgentStatus.STARTING]:
        raise HTTPException(status_code=400, detail=f"Agent is not running (status: {agent.status.value})")

    # Stop the VM if GCP is configured
    app_config = Config.load()
    if app_config.gcp_project and agent.gce_instance:
        from agentctl.server.services.vm_manager import VMManager
        vm = VMManager(app_config.gcp_project, app_config.gcp_zone)
        try:
            vm.delete_instance(agent.gce_instance)
        except Exception:
            pass  # Continue even if VM deletion fails

    stopped_at = _utcnow().isoformat()
    repository.update_agent_status(agent.id, AgentStatus.STOPPED, stopped_at=stopped_at)

    return {"id": agent_id, "status": "stopped", "stopped_at": stopped_at}


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    """Delete an agent."""
    from agentctl.shared.config import Config

    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Delete VM and clean up GCS artifacts if GCP is configured
    app_config = Config.load()
    if app_config.gcp_project:
        # Delete VM if it exists
        if agent.gce_instance:
            from agentctl.server.services.vm_manager import VMManager
            vm = VMManager(app_config.gcp_project, app_config.gcp_zone)
            try:
                vm.delete_instance(agent.gce_instance)
            except Exception:
                pass  # Continue even if VM deletion fails

        # Delete GCS artifacts
        if app_config.gcs_bucket:
            from agentctl.server.services.storage_manager import StorageManager
            storage = StorageManager(app_config.gcs_bucket)
            try:
                storage.delete_files(f"agents/{agent_id}/")
            except Exception:
                pass  # Continue even if cleanup fails

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
