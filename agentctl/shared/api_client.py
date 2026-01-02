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
