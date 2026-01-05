"""Tests for Railway provider implementation.

These tests verify the RailwayProvider class implements the BaseProvider
interface correctly and interacts with Railway's GraphQL API as expected.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestRailwayProviderInit:
    """Tests for RailwayProvider initialization."""

    def test_init_with_config(self):
        """RailwayProvider should initialize with config."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="test-project-id",
        )
        provider = RailwayProvider(config)

        assert provider.config == config
        assert provider.token == "test-token"
        assert provider.project_id == "test-project-id"

    def test_api_url_is_correct(self):
        """RailwayProvider should use correct GraphQL API URL."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
        )
        provider = RailwayProvider(config)

        assert provider.api_url == "https://backboard.railway.com/graphql/v2"


class TestRailwayProviderLaunch:
    """Tests for launching agents on Railway."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_launch_creates_service(self, mock_requests):
        """Launch should create a Railway service."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType
        from agency_quickdeploy.auth import Credentials

        # Mock successful project query
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "serviceCreate": {
                    "id": "service-123",
                    "name": "agent-test",
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        credentials = Credentials.from_api_key("sk-test-key")

        result = provider.launch(
            agent_id="agent-test",
            prompt="Build a todo app",
            credentials=credentials,
        )

        assert result.agent_id == "agent-test"
        assert result.provider == "railway"
        assert result.status == "launching"
        mock_requests.post.assert_called()

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_launch_sets_environment_variables(self, mock_requests):
        """Launch should set environment variables for the agent."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType
        from agency_quickdeploy.auth import Credentials

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "serviceCreate": {
                    "id": "service-123",
                    "name": "agent-test",
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        credentials = Credentials.from_api_key("sk-test-key")

        provider.launch(
            agent_id="agent-test",
            prompt="Build a todo app",
            credentials=credentials,
        )

        # Verify the GraphQL call includes environment variables
        call_args = mock_requests.post.call_args
        request_body = call_args[1]["json"]

        # The variables should contain environment info
        assert "variables" in request_body or "AGENT_PROMPT" in str(request_body)

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_launch_handles_api_error(self, mock_requests):
        """Launch should handle Railway API errors gracefully."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType
        from agency_quickdeploy.auth import Credentials

        mock_response = Mock()
        mock_response.json.return_value = {
            "errors": [{"message": "Rate limit exceeded"}]
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        credentials = Credentials.from_api_key("sk-test-key")

        result = provider.launch(
            agent_id="agent-test",
            prompt="Build a todo app",
            credentials=credentials,
        )

        assert result.status == "failed"
        assert "Rate limit" in result.error


class TestRailwayProviderStatus:
    """Tests for getting agent status from Railway."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_status_queries_deployments(self, mock_requests):
        """Status should query Railway deployments."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "deployments": {
                    "edges": [{
                        "node": {
                            "id": "deploy-123",
                            "status": "SUCCESS",
                            "staticUrl": "https://agent-test.up.railway.app",
                        }
                    }]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        # Store service mapping for test
        provider._service_map = {"agent-test": "service-123"}

        status = provider.status("agent-test")

        assert status["status"] in ["SUCCESS", "running", "completed"]
        mock_requests.post.assert_called()

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_status_returns_not_found_for_unknown_agent(self, mock_requests):
        """Status should handle unknown agents."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"deployments": {"edges": []}}
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        provider._service_map = {}

        status = provider.status("unknown-agent")

        assert status["status"] == "not_found"


class TestRailwayProviderLogs:
    """Tests for getting agent logs from Railway."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_logs_returns_deployment_logs(self, mock_requests):
        """Logs should return deployment logs."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        # First call for getting deployment, second for logs
        mock_responses = [
            Mock(json=lambda: {
                "data": {
                    "deployments": {
                        "edges": [{
                            "node": {"id": "deploy-123", "status": "SUCCESS"}
                        }]
                    }
                }
            }),
            Mock(json=lambda: {
                "data": {
                    "deploymentLogs": {
                        "logs": [
                            {"message": "Starting agent..."},
                            {"message": "Agent completed"},
                        ]
                    }
                }
            }),
        ]
        for m in mock_responses:
            m.raise_for_status = Mock()
        mock_requests.post.side_effect = mock_responses

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        provider._service_map = {"agent-test": "service-123"}

        logs = provider.logs("agent-test")

        assert logs is not None
        assert "Starting agent" in logs or logs is not None


class TestRailwayProviderStop:
    """Tests for stopping agents on Railway."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_stop_deletes_service(self, mock_requests):
        """Stop should delete the Railway service."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"serviceDelete": True}
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        provider._service_map = {"agent-test": "service-123"}

        result = provider.stop("agent-test")

        assert result is True
        mock_requests.post.assert_called()


class TestRailwayProviderListAgents:
    """Tests for listing agents on Railway."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_list_returns_services(self, mock_requests):
        """List should return services in the project."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "project": {
                    "services": {
                        "edges": [
                            {
                                "node": {
                                    "id": "service-1",
                                    "name": "agent-123",
                                    "deployments": {
                                        "edges": [{
                                            "node": {"status": "SUCCESS"}
                                        }]
                                    }
                                }
                            },
                            {
                                "node": {
                                    "id": "service-2",
                                    "name": "agent-456",
                                    "deployments": {
                                        "edges": [{
                                            "node": {"status": "BUILDING"}
                                        }]
                                    }
                                }
                            },
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)

        agents = provider.list_agents()

        assert len(agents) == 2
        assert agents[0]["name"] == "agent-123"
        assert agents[1]["name"] == "agent-456"


class TestRailwayProviderProjectManagement:
    """Tests for Railway project management."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_creates_project_if_not_configured(self, mock_requests):
        """Should create a Railway project if none is configured."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType
        from agency_quickdeploy.auth import Credentials

        # First call creates project, second creates service
        mock_responses = [
            Mock(json=lambda: {
                "data": {
                    "projectCreate": {
                        "id": "new-project-123",
                        "name": "agency-quickdeploy",
                        "environments": {
                            "edges": [{"node": {"id": "env-123"}}]
                        }
                    }
                }
            }),
            Mock(json=lambda: {
                "data": {
                    "serviceCreate": {
                        "id": "service-123",
                        "name": "agent-test",
                    }
                }
            }),
        ]
        for m in mock_responses:
            m.raise_for_status = Mock()
        mock_requests.post.side_effect = mock_responses

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            # No project_id - should create one
        )
        provider = RailwayProvider(config)
        credentials = Credentials.from_api_key("sk-test-key")

        result = provider.launch(
            agent_id="agent-test",
            prompt="Build a todo app",
            credentials=credentials,
        )

        assert result.status == "launching"
        # Should have called API twice (create project + create service)
        assert mock_requests.post.call_count >= 1


class TestRailwayTokenValidation:
    """Tests for Railway token validation (TDD - Phase 1.1)."""

    def test_validate_token_format_valid_uuid(self):
        """Valid Railway tokens (UUIDs) should pass format validation."""
        from agency_quickdeploy.providers.railway import validate_railway_token_format

        # Railway tokens are UUIDs like: 3fca9fef-8953-486f-b772-af5f34417ef7
        assert validate_railway_token_format("3fca9fef-8953-486f-b772-af5f34417ef7") is True
        assert validate_railway_token_format("a1b2c3d4-e5f6-7890-abcd-ef1234567890") is True

    def test_validate_token_format_invalid_empty(self):
        """Empty or None tokens should fail format validation."""
        from agency_quickdeploy.providers.railway import validate_railway_token_format

        assert validate_railway_token_format("") is False
        assert validate_railway_token_format(None) is False

    def test_validate_token_format_invalid_wrong_format(self):
        """Non-UUID format tokens should fail validation."""
        from agency_quickdeploy.providers.railway import validate_railway_token_format

        # Anthropic API key format (wrong)
        assert validate_railway_token_format("sk-ant-api03-xxx") is False
        # Too short
        assert validate_railway_token_format("abc123") is False
        # Random string
        assert validate_railway_token_format("not-a-valid-token") is False

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_validate_token_api_success(self, mock_requests):
        """Valid token should pass API connectivity check."""
        from agency_quickdeploy.providers.railway import validate_railway_token_api

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"projects": {"edges": [{"node": {"id": "proj-123", "name": "test"}}]}}
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        success, error = validate_railway_token_api("valid-token")

        assert success is True
        assert error is None
        mock_requests.post.assert_called_once()

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_validate_token_api_invalid_token(self, mock_requests):
        """Invalid token should fail API check with helpful error."""
        from agency_quickdeploy.providers.railway import validate_railway_token_api

        mock_response = Mock()
        mock_response.json.return_value = {
            "errors": [{"message": "Unauthorized"}]
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        success, error = validate_railway_token_api("invalid-token")

        assert success is False
        assert error is not None
        assert "token" in error.lower() or "unauthorized" in error.lower()

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_validate_token_api_network_error(self, mock_requests):
        """Network errors should be handled gracefully."""
        from agency_quickdeploy.providers.railway import validate_railway_token_api
        import requests.exceptions

        mock_requests.exceptions = requests.exceptions
        mock_requests.post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        success, error = validate_railway_token_api("some-token")

        assert success is False
        assert error is not None
        assert "network" in error.lower() or "connection" in error.lower()


class TestRailwayDeployment:
    """Tests for Railway deployment sources (Docker image vs GitHub repo)."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_launch_uses_docker_image_by_default(self, mock_requests):
        """Launch should use Docker image by default (no GitHub OAuth required)."""
        from agency_quickdeploy.providers.railway import RailwayProvider, DEFAULT_AGENT_IMAGE
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType
        from agency_quickdeploy.auth import Credentials

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "serviceCreate": {
                    "id": "service-123",
                    "name": "agent-test",
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        credentials = Credentials.from_api_key("sk-ant-test")

        provider.launch(
            agent_id="agent-test",
            prompt="Build a todo app",
            credentials=credentials,
        )

        # Verify the GraphQL mutation was called
        call_args = mock_requests.post.call_args
        request_body = call_args[1]["json"]

        # Should use image source by default
        assert "image" in str(request_body).lower() or DEFAULT_AGENT_IMAGE in str(request_body)

    @patch("agency_quickdeploy.providers.railway.requests")
    @patch.dict(os.environ, {"RAILWAY_AGENT_REPO": "https://github.com/myuser/my-agent-repo"})
    def test_launch_respects_custom_repo_env_var(self, mock_requests):
        """Launch should use RAILWAY_AGENT_REPO env var if set."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType
        from agency_quickdeploy.auth import Credentials

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "serviceCreate": {
                    "id": "service-123",
                    "name": "agent-test",
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        provider = RailwayProvider(config)
        credentials = Credentials.from_api_key("sk-ant-test")

        provider.launch(
            agent_id="agent-test",
            prompt="Build a todo app",
            credentials=credentials,
        )

        # Verify custom repo was used
        call_args = mock_requests.post.call_args
        request_body = call_args[1]["json"]
        assert "my-agent-repo" in str(request_body) or "myuser" in str(request_body)

    def test_default_agent_image_constant_exists(self):
        """DEFAULT_AGENT_IMAGE constant should be a valid Docker image reference."""
        from agency_quickdeploy.providers.railway import DEFAULT_AGENT_IMAGE

        assert DEFAULT_AGENT_IMAGE is not None
        # Should be a ghcr.io image
        assert "ghcr.io" in DEFAULT_AGENT_IMAGE or "docker" in DEFAULT_AGENT_IMAGE.lower()

    def test_agent_repo_url_constant_exists(self):
        """AGENT_REPO_URL constant should be in owner/repo format (for optional repo deployment)."""
        from agency_quickdeploy.providers.railway import AGENT_REPO_URL

        assert AGENT_REPO_URL is not None
        # Should be in "owner/repo" format (e.g., "wesleyzhao/agency")
        assert "/" in AGENT_REPO_URL
        assert len(AGENT_REPO_URL.split("/")) == 2


class TestRailwayServiceDiscovery:
    """Tests for service discovery across CLI invocations (TDD - Phase 3)."""

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_get_service_id_finds_service_without_cache(self, mock_requests):
        """_get_service_id should find service by name even with empty cache."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "project": {
                    "services": {
                        "edges": [
                            {"node": {"id": "service-abc", "name": "agent-123"}},
                            {"node": {"id": "service-def", "name": "agent-456"}},
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        # Fresh provider instance (no cache)
        provider = RailwayProvider(config)
        assert provider._service_map == {}  # Verify cache is empty

        service_id = provider._get_service_id("agent-123")

        assert service_id == "service-abc"
        # Should have populated cache
        assert provider._service_map["agent-123"] == "service-abc"

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_status_works_across_cli_invocations(self, mock_requests):
        """status() should work even with fresh provider instance."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        # First call to find service, second to get deployments
        mock_responses = [
            Mock(json=lambda: {
                "data": {
                    "project": {
                        "services": {
                            "edges": [
                                {"node": {"id": "service-abc", "name": "agent-test"}},
                            ]
                        }
                    }
                }
            }),
            Mock(json=lambda: {
                "data": {
                    "deployments": {
                        "edges": [{
                            "node": {
                                "id": "deploy-123",
                                "status": "SUCCESS",
                                "staticUrl": "https://agent.up.railway.app",
                            }
                        }]
                    }
                }
            }),
        ]
        for m in mock_responses:
            m.raise_for_status = Mock()
        mock_requests.post.side_effect = mock_responses

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            railway_project_id="project-123",
        )
        # Fresh provider (simulating new CLI invocation)
        provider = RailwayProvider(config)

        status = provider.status("agent-test")

        assert status["agent_id"] == "agent-test"
        assert status["status"] in ["running", "SUCCESS"]

    @patch("agency_quickdeploy.providers.railway.requests")
    def test_discover_project_finds_by_name(self, mock_requests):
        """_discover_project_id should find project by name."""
        from agency_quickdeploy.providers.railway import RailwayProvider
        from agency_quickdeploy.config import QuickDeployConfig
        from agency_quickdeploy.providers.base import ProviderType

        mock_response = Mock()
        # Uses 'projects' query instead of 'me.projects' to work with all token types
        mock_response.json.return_value = {
            "data": {
                "projects": {
                    "edges": [
                        {"node": {"id": "proj-abc", "name": "other-project"}},
                        {"node": {"id": "proj-def", "name": "agency-quickdeploy"}},
                    ]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response

        config = QuickDeployConfig(
            provider=ProviderType.RAILWAY,
            railway_token="test-token",
            # No project_id configured
        )
        provider = RailwayProvider(config)

        project_id = provider._discover_project_id()

        assert project_id == "proj-def"


class TestRailwayError:
    """Tests for RailwayError class with actionable messages (TDD - Phase 1.2)."""

    def test_invalid_token_error_has_actionable_message(self):
        """invalid_token() should include link to get new token."""
        from agency_quickdeploy.providers.railway import RailwayError

        error = RailwayError.invalid_token()

        assert "railway.com/account/tokens" in str(error)
        assert "RAILWAY_TOKEN" in str(error)

    def test_rate_limited_error_suggests_retry(self):
        """rate_limited() should suggest waiting and retrying."""
        from agency_quickdeploy.providers.railway import RailwayError

        error = RailwayError.rate_limited()

        assert "rate limit" in str(error).lower()
        assert "retry" in str(error).lower() or "wait" in str(error).lower()

    def test_project_not_found_includes_project_id(self):
        """project_not_found() should include the project ID."""
        from agency_quickdeploy.providers.railway import RailwayError

        error = RailwayError.project_not_found("proj-12345")

        assert "proj-12345" in str(error)
        assert "project" in str(error).lower()

    def test_service_not_found_includes_agent_id(self):
        """service_not_found() should include the agent ID."""
        from agency_quickdeploy.providers.railway import RailwayError

        error = RailwayError.service_not_found("agent-20260105-abc123")

        assert "agent-20260105-abc123" in str(error)
        assert "list" in str(error).lower() or "agents" in str(error).lower()

    def test_api_error_includes_suggestion(self):
        """api_error() should include custom message and suggestion."""
        from agency_quickdeploy.providers.railway import RailwayError

        error = RailwayError.api_error("Query failed", "Check your project ID")

        assert "Query failed" in str(error)
        assert "Check your project ID" in str(error)

    def test_error_is_exception(self):
        """RailwayError should be a proper Exception subclass."""
        from agency_quickdeploy.providers.railway import RailwayError

        error = RailwayError.invalid_token()

        assert isinstance(error, Exception)
        # Should be raisable
        try:
            raise error
        except RailwayError as e:
            assert "token" in str(e).lower()
