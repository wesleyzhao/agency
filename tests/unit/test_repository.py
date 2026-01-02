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
