"""Tests for the provider abstraction layer.

TDD: These tests are written first, before the implementation.
"""

import pytest
from abc import ABC
from dataclasses import dataclass

from agency_quickdeploy.providers import (
    BaseProvider,
    DeploymentResult,
    ProviderType,
)
from agency_quickdeploy.auth import Credentials


class TestProviderType:
    """Tests for ProviderType enum."""

    def test_gcp_provider_type(self):
        """ProviderType should have GCP option."""
        assert ProviderType.GCP.value == "gcp"

    def test_railway_provider_type(self):
        """ProviderType should have Railway option."""
        assert ProviderType.RAILWAY.value == "railway"

    def test_provider_type_from_string(self):
        """Should be able to get ProviderType from string."""
        assert ProviderType("gcp") == ProviderType.GCP
        assert ProviderType("railway") == ProviderType.RAILWAY


class TestDeploymentResult:
    """Tests for DeploymentResult dataclass."""

    def test_deployment_result_required_fields(self):
        """DeploymentResult should require agent_id, provider, status."""
        result = DeploymentResult(
            agent_id="test-agent-123",
            provider="gcp",
            status="launching",
        )
        assert result.agent_id == "test-agent-123"
        assert result.provider == "gcp"
        assert result.status == "launching"

    def test_deployment_result_optional_fields(self):
        """DeploymentResult should have optional url and error fields."""
        result = DeploymentResult(
            agent_id="test-agent-123",
            provider="railway",
            status="running",
            external_url="https://example.railway.app",
        )
        assert result.external_url == "https://example.railway.app"
        assert result.error is None

    def test_deployment_result_with_error(self):
        """DeploymentResult should support error field."""
        result = DeploymentResult(
            agent_id="test-agent-123",
            provider="gcp",
            status="failed",
            error="VM creation failed",
        )
        assert result.status == "failed"
        assert result.error == "VM creation failed"

    def test_deployment_result_is_dataclass(self):
        """DeploymentResult should be a dataclass."""
        assert hasattr(DeploymentResult, "__dataclass_fields__")


class TestBaseProvider:
    """Tests for BaseProvider ABC."""

    def test_base_provider_is_abstract(self):
        """BaseProvider should be an abstract base class."""
        assert issubclass(BaseProvider, ABC)

    def test_base_provider_cannot_be_instantiated(self):
        """BaseProvider should not be directly instantiable."""
        with pytest.raises(TypeError):
            BaseProvider()

    def test_base_provider_requires_launch_method(self):
        """Subclasses must implement launch()."""
        class IncompleteProvider(BaseProvider):
            def status(self, agent_id): pass
            def logs(self, agent_id): pass
            def stop(self, agent_id): pass
            def list_agents(self): pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_base_provider_requires_status_method(self):
        """Subclasses must implement status()."""
        class IncompleteProvider(BaseProvider):
            def launch(self, agent_id, prompt, credentials, **kwargs): pass
            def logs(self, agent_id): pass
            def stop(self, agent_id): pass
            def list_agents(self): pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_base_provider_requires_logs_method(self):
        """Subclasses must implement logs()."""
        class IncompleteProvider(BaseProvider):
            def launch(self, agent_id, prompt, credentials, **kwargs): pass
            def status(self, agent_id): pass
            def stop(self, agent_id): pass
            def list_agents(self): pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_base_provider_requires_stop_method(self):
        """Subclasses must implement stop()."""
        class IncompleteProvider(BaseProvider):
            def launch(self, agent_id, prompt, credentials, **kwargs): pass
            def status(self, agent_id): pass
            def logs(self, agent_id): pass
            def list_agents(self): pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_base_provider_requires_list_agents_method(self):
        """Subclasses must implement list_agents()."""
        class IncompleteProvider(BaseProvider):
            def launch(self, agent_id, prompt, credentials, **kwargs): pass
            def status(self, agent_id): pass
            def logs(self, agent_id): pass
            def stop(self, agent_id): pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_complete_provider_can_be_instantiated(self):
        """A complete provider implementation should be instantiable."""
        class CompleteProvider(BaseProvider):
            def launch(self, agent_id, prompt, credentials, **kwargs):
                return DeploymentResult(
                    agent_id=agent_id,
                    provider="test",
                    status="launching",
                )

            def status(self, agent_id):
                return {"status": "running"}

            def logs(self, agent_id):
                return "some logs"

            def stop(self, agent_id):
                return True

            def list_agents(self):
                return []

        provider = CompleteProvider()
        assert provider is not None

    def test_provider_launch_returns_deployment_result(self):
        """launch() should return a DeploymentResult."""
        class TestProvider(BaseProvider):
            def launch(self, agent_id, prompt, credentials, **kwargs):
                return DeploymentResult(
                    agent_id=agent_id,
                    provider="test",
                    status="launching",
                )

            def status(self, agent_id): return {}
            def logs(self, agent_id): return None
            def stop(self, agent_id): return True
            def list_agents(self): return []

        provider = TestProvider()
        result = provider.launch("agent-1", "Build an app", None)
        assert isinstance(result, DeploymentResult)
        assert result.agent_id == "agent-1"
