"""Railway provider implementation for agency-quickdeploy.

This module implements the BaseProvider interface using Railway's
GraphQL API to deploy Claude agents as containerized services.

Railway API Reference:
- Endpoint: https://backboard.railway.com/graphql/v2
- Auth: Bearer token in Authorization header
- Docs: https://docs.railway.com/guides/public-api
"""

import json
import re
from typing import Optional, Any, Tuple

import requests

from agency_quickdeploy.providers.base import BaseProvider, DeploymentResult
from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import Credentials


# Railway API endpoint
RAILWAY_API_URL = "https://backboard.railway.com/graphql/v2"


class RailwayError(Exception):
    """Railway-specific error with actionable messages.

    Use factory methods to create errors with consistent, helpful messages
    that guide users toward resolution.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    @classmethod
    def invalid_token(cls) -> "RailwayError":
        """Create error for invalid/expired token."""
        return cls(
            "Invalid Railway token. "
            "Get a new token at railway.com/account/tokens and set RAILWAY_TOKEN environment variable."
        )

    @classmethod
    def rate_limited(cls) -> "RailwayError":
        """Create error for rate limit exceeded."""
        return cls(
            "Railway API rate limit exceeded. "
            "Wait a few minutes and retry your request."
        )

    @classmethod
    def project_not_found(cls, project_id: str) -> "RailwayError":
        """Create error for project not found."""
        return cls(
            f"Railway project '{project_id}' not found. "
            "Check RAILWAY_PROJECT_ID or let agency-quickdeploy create a new project automatically."
        )

    @classmethod
    def service_not_found(cls, agent_id: str) -> "RailwayError":
        """Create error for service/agent not found."""
        return cls(
            f"Agent '{agent_id}' not found. "
            "Run 'agency-quickdeploy list --provider railway' to see available agents."
        )

    @classmethod
    def api_error(cls, message: str, suggestion: str) -> "RailwayError":
        """Create error with custom message and suggestion."""
        return cls(f"{message}. {suggestion}")


# UUID pattern for Railway tokens
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def validate_railway_token_format(token: Optional[str]) -> bool:
    """Validate Railway token format.

    Railway tokens are UUIDs (e.g., 3fca9fef-8953-486f-b772-af5f34417ef7).

    Args:
        token: The token to validate

    Returns:
        True if token matches UUID format, False otherwise
    """
    if not token:
        return False
    return bool(UUID_PATTERN.match(token))


def validate_railway_token_api(token: str) -> Tuple[bool, Optional[str]]:
    """Validate Railway token by testing API connectivity.

    Makes a minimal GraphQL query to verify the token works.

    Args:
        token: Railway API token

    Returns:
        Tuple of (success, error_message). If success is True, error is None.
    """
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        # Minimal query to test token validity
        query = {"query": "query { me { id email } }"}

        response = requests.post(RAILWAY_API_URL, headers=headers, json=query, timeout=10)
        response.raise_for_status()

        result = response.json()

        if result.get("errors"):
            error_msg = result["errors"][0].get("message", "Unknown error")
            return False, f"Invalid token: {error_msg}. Get a new token at railway.com/account/tokens"

        if result.get("data", {}).get("me"):
            return True, None

        return False, "Invalid token: No user data returned"

    except requests.exceptions.ConnectionError:
        return False, "Network error: Cannot connect to Railway API. Check your internet connection."
    except requests.exceptions.Timeout:
        return False, "Network error: Railway API request timed out. Try again."
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error: {e}. Check your token at railway.com/account/tokens"
    except Exception as e:
        return False, f"Unexpected error: {e}"


# Default Docker image for Claude agent
# This image should contain: Node.js, Python, claude-code CLI, claude-agent-sdk
# Users can override via environment variable RAILWAY_AGENT_IMAGE
DEFAULT_AGENT_IMAGE = "ghcr.io/anthropics/agency-quickdeploy-agent:latest"


class RailwayProvider(BaseProvider):
    """Railway provider using containerized services.

    This provider deploys Claude agents as Railway services using
    a pre-built Docker image that runs the agent loop.
    """

    API_URL = "https://backboard.railway.com/graphql/v2"

    def __init__(self, config: QuickDeployConfig):
        """Initialize Railway provider.

        Args:
            config: QuickDeploy configuration with Railway settings
        """
        self.config = config
        self.token = config.railway_token
        self.project_id = config.railway_project_id
        self._environment_id: Optional[str] = None
        # Maps agent_id -> service_id for status/stop operations
        self._service_map: dict[str, str] = {}

    @property
    def api_url(self) -> str:
        """Railway GraphQL API URL."""
        return self.API_URL

    def _graphql(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query against Railway API.

        Args:
            query: GraphQL query or mutation
            variables: Query variables

        Returns:
            Response data dict

        Raises:
            requests.HTTPError: If request fails
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def _ensure_project(self) -> str:
        """Ensure a Railway project exists, creating one if needed.

        Returns:
            Project ID
        """
        if self.project_id:
            # Fetch environment ID for existing project
            if not self._environment_id:
                result = self._graphql(
                    """
                    query getProject($id: String!) {
                        project(id: $id) {
                            environments {
                                edges {
                                    node {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                    }
                    """,
                    {"id": self.project_id}
                )
                if result.get("data", {}).get("project"):
                    envs = result["data"]["project"]["environments"]["edges"]
                    if envs:
                        # Use first environment (usually "production")
                        self._environment_id = envs[0]["node"]["id"]
            return self.project_id

        # Create a new project
        result = self._graphql(
            """
            mutation projectCreate($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    id
                    name
                    environments {
                        edges {
                            node {
                                id
                                name
                            }
                        }
                    }
                }
            }
            """,
            {"input": {"name": "agency-quickdeploy"}}
        )

        if result.get("errors"):
            raise RuntimeError(f"Failed to create project: {result['errors']}")

        project_data = result["data"]["projectCreate"]
        self.project_id = project_data["id"]
        envs = project_data["environments"]["edges"]
        if envs:
            self._environment_id = envs[0]["node"]["id"]

        return self.project_id

    def launch(
        self,
        agent_id: str,
        prompt: str,
        credentials: Optional[Credentials],
        **kwargs: Any,
    ) -> DeploymentResult:
        """Launch an agent on Railway.

        Creates a new Railway service from a Docker image and starts
        the deployment with the agent configuration.

        Args:
            agent_id: Unique identifier for the agent
            prompt: Task prompt for the agent
            credentials: Authentication credentials
            **kwargs: Additional options (repo, branch, max_iterations, no_shutdown)

        Returns:
            DeploymentResult with launch status
        """
        try:
            # Ensure project exists
            project_id = self._ensure_project()

            # Build environment variables for the agent
            env_vars = {
                "AGENT_ID": agent_id,
                "AGENT_PROMPT": prompt,
                "MAX_ITERATIONS": str(kwargs.get("max_iterations", 0)),
                "NO_SHUTDOWN": "true" if kwargs.get("no_shutdown") else "false",
            }

            # Add repo/branch if provided
            if kwargs.get("repo"):
                env_vars["REPO_URL"] = kwargs["repo"]
            if kwargs.get("branch"):
                env_vars["REPO_BRANCH"] = kwargs["branch"]

            # Add credentials
            if credentials:
                cred_vars = credentials.get_env_vars()
                env_vars.update(cred_vars)

            # Get agent image from environment or use default
            import os
            agent_image = os.environ.get("RAILWAY_AGENT_IMAGE", DEFAULT_AGENT_IMAGE)

            # Create service with Docker image
            service_input = {
                "name": agent_id,
                "projectId": project_id,
                "source": {"image": agent_image},
                "variables": env_vars,
            }

            if self._environment_id:
                service_input["environmentId"] = self._environment_id

            result = self._graphql(
                """
                mutation serviceCreate($input: ServiceCreateInput!) {
                    serviceCreate(input: $input) {
                        id
                        name
                    }
                }
                """,
                {"input": service_input}
            )

            if result.get("errors"):
                error_msg = result["errors"][0].get("message", "Unknown error")
                return DeploymentResult(
                    agent_id=agent_id,
                    provider="railway",
                    status="failed",
                    error=error_msg,
                )

            service_data = result["data"]["serviceCreate"]
            self._service_map[agent_id] = service_data["id"]

            return DeploymentResult(
                agent_id=agent_id,
                provider="railway",
                status="launching",
            )

        except requests.HTTPError as e:
            return DeploymentResult(
                agent_id=agent_id,
                provider="railway",
                status="failed",
                error=f"Railway API error: {str(e)}",
            )
        except Exception as e:
            return DeploymentResult(
                agent_id=agent_id,
                provider="railway",
                status="failed",
                error=str(e),
            )

    def _get_service_id(self, agent_id: str) -> Optional[str]:
        """Get Railway service ID for an agent.

        First checks local cache, then queries Railway API.

        Args:
            agent_id: Agent identifier

        Returns:
            Service ID or None if not found
        """
        if agent_id in self._service_map:
            return self._service_map[agent_id]

        # Query Railway for service by name
        if not self.project_id:
            return None

        try:
            result = self._graphql(
                """
                query getProject($id: String!) {
                    project(id: $id) {
                        services {
                            edges {
                                node {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
                """,
                {"id": self.project_id}
            )

            services = result.get("data", {}).get("project", {}).get("services", {}).get("edges", [])
            for edge in services:
                service = edge["node"]
                if service["name"] == agent_id:
                    self._service_map[agent_id] = service["id"]
                    return service["id"]

        except Exception:
            pass

        return None

    def status(self, agent_id: str) -> dict:
        """Get agent status from Railway.

        Args:
            agent_id: Agent identifier

        Returns:
            Status dict with agent info
        """
        service_id = self._get_service_id(agent_id)
        if not service_id:
            return {
                "agent_id": agent_id,
                "status": "not_found",
            }

        try:
            result = self._graphql(
                """
                query deployments($serviceId: String!) {
                    deployments(
                        first: 1
                        input: { serviceId: $serviceId }
                    ) {
                        edges {
                            node {
                                id
                                status
                                staticUrl
                            }
                        }
                    }
                }
                """,
                {"serviceId": service_id}
            )

            deployments = result.get("data", {}).get("deployments", {}).get("edges", [])
            if not deployments:
                return {
                    "agent_id": agent_id,
                    "status": "no_deployment",
                }

            deployment = deployments[0]["node"]
            status = deployment.get("status", "UNKNOWN")

            # Map Railway statuses to our status vocabulary
            status_map = {
                "SUCCESS": "running",
                "BUILDING": "launching",
                "DEPLOYING": "launching",
                "CRASHED": "failed",
                "REMOVED": "stopped",
                "SLEEPING": "stopped",
            }

            return {
                "agent_id": agent_id,
                "status": status_map.get(status, status),
                "railway_status": status,
                "deployment_id": deployment.get("id"),
                "url": deployment.get("staticUrl"),
            }

        except Exception as e:
            return {
                "agent_id": agent_id,
                "status": "error",
                "error": str(e),
            }

    def logs(self, agent_id: str) -> Optional[str]:
        """Get agent logs from Railway.

        Note: Railway's log API may require different handling.
        For now, this provides basic functionality.

        Args:
            agent_id: Agent identifier

        Returns:
            Log content as string, or None if not available
        """
        service_id = self._get_service_id(agent_id)
        if not service_id:
            return None

        try:
            # First get the latest deployment
            result = self._graphql(
                """
                query deployments($serviceId: String!) {
                    deployments(
                        first: 1
                        input: { serviceId: $serviceId }
                    ) {
                        edges {
                            node {
                                id
                            }
                        }
                    }
                }
                """,
                {"serviceId": service_id}
            )

            deployments = result.get("data", {}).get("deployments", {}).get("edges", [])
            if not deployments:
                return None

            deployment_id = deployments[0]["node"]["id"]

            # Try to get logs (Railway API may vary)
            # Note: Railway's log API is streaming-based, this is a simplified version
            result = self._graphql(
                """
                query deploymentLogs($deploymentId: String!) {
                    deploymentLogs(deploymentId: $deploymentId) {
                        logs {
                            message
                            timestamp
                        }
                    }
                }
                """,
                {"deploymentId": deployment_id}
            )

            logs_data = result.get("data", {}).get("deploymentLogs", {}).get("logs", [])
            if logs_data:
                return "\n".join(log.get("message", "") for log in logs_data)

            return None

        except Exception:
            return None

    def stop(self, agent_id: str) -> bool:
        """Stop an agent by deleting its Railway service.

        Args:
            agent_id: Agent identifier

        Returns:
            True if stopped successfully
        """
        service_id = self._get_service_id(agent_id)
        if not service_id:
            return False

        try:
            result = self._graphql(
                """
                mutation serviceDelete($id: String!) {
                    serviceDelete(id: $id)
                }
                """,
                {"id": service_id}
            )

            if result.get("errors"):
                return False

            # Remove from cache
            self._service_map.pop(agent_id, None)
            return True

        except Exception:
            return False

    def list_agents(self) -> list[dict]:
        """List all agents in the Railway project.

        Returns:
            List of agent dicts with name, status, etc.
        """
        if not self.project_id:
            return []

        try:
            result = self._graphql(
                """
                query getProject($id: String!) {
                    project(id: $id) {
                        services {
                            edges {
                                node {
                                    id
                                    name
                                    deployments(first: 1) {
                                        edges {
                                            node {
                                                status
                                                staticUrl
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                """,
                {"id": self.project_id}
            )

            services = result.get("data", {}).get("project", {}).get("services", {}).get("edges", [])
            agents = []

            for edge in services:
                service = edge["node"]
                deployments = service.get("deployments", {}).get("edges", [])

                status = "unknown"
                url = None
                if deployments:
                    deployment = deployments[0]["node"]
                    status = deployment.get("status", "unknown")
                    url = deployment.get("staticUrl")

                agents.append({
                    "name": service["name"],
                    "service_id": service["id"],
                    "status": status,
                    "url": url,
                })

                # Update cache
                self._service_map[service["name"]] = service["id"]

            return agents

        except Exception:
            return []
