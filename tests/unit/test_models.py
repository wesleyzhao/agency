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
