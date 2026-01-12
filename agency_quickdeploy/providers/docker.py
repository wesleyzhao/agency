"""Docker provider implementation for agency-quickdeploy.

This module implements the BaseProvider interface using the local Docker
daemon to run Claude agents in containers for 24/7 local operation.

No cloud credentials required - agents run entirely on the user's machine.
State is stored in the local filesystem (~/.agency/agents/{agent_id}/).
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Any

try:
    import docker
    from docker.errors import NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
    NotFound = Exception
    APIError = Exception

from agency_quickdeploy.providers.base import BaseProvider, DeploymentResult
from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import Credentials


def get_platform() -> str:
    """Get the current platform: 'macos', 'linux', or 'windows'."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    return system


def get_docker_install_instructions() -> str:
    """Get platform-specific Docker installation instructions."""
    plat = get_platform()

    if plat == "macos":
        # Check if Homebrew is available
        has_brew = shutil.which("brew") is not None
        if has_brew:
            return (
                "Docker is not installed. Install it with Homebrew:\n"
                "  brew install --cask docker\n\n"
                "Then open Docker Desktop from Applications to start it.\n\n"
                "Or download Docker Desktop from: https://docker.com/products/docker-desktop"
            )
        return (
            "Docker is not installed.\n"
            "Download Docker Desktop from: https://docker.com/products/docker-desktop\n\n"
            "Or install Homebrew first, then run:\n"
            "  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"\n"
            "  brew install --cask docker"
        )

    elif plat == "linux":
        # Detect distro for specific instructions
        distro = ""
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("ID="):
                        distro = line.strip().split("=")[1].strip('"').lower()
                        break
        except Exception:
            pass

        if distro in ("ubuntu", "debian"):
            return (
                "Docker is not installed. Install it with:\n"
                "  curl -fsSL https://get.docker.com | sh\n"
                "  sudo usermod -aG docker $USER\n"
                "  newgrp docker\n\n"
                "Or use apt:\n"
                "  sudo apt-get update\n"
                "  sudo apt-get install -y docker.io\n"
                "  sudo usermod -aG docker $USER\n"
                "  newgrp docker"
            )
        elif distro in ("fedora", "centos", "rhel"):
            return (
                "Docker is not installed. Install it with:\n"
                "  curl -fsSL https://get.docker.com | sh\n"
                "  sudo usermod -aG docker $USER\n"
                "  newgrp docker\n\n"
                "Or use dnf:\n"
                "  sudo dnf install -y docker\n"
                "  sudo systemctl enable --now docker\n"
                "  sudo usermod -aG docker $USER\n"
                "  newgrp docker"
            )
        else:
            return (
                "Docker is not installed. Install it with:\n"
                "  curl -fsSL https://get.docker.com | sh\n"
                "  sudo usermod -aG docker $USER\n"
                "  newgrp docker\n\n"
                "See https://docs.docker.com/engine/install/ for your distribution."
            )

    elif plat == "windows":
        return (
            "Docker is not installed.\n"
            "Download Docker Desktop from: https://docker.com/products/docker-desktop\n\n"
            "Or install with winget:\n"
            "  winget install Docker.DockerDesktop"
        )

    return (
        "Docker is not installed.\n"
        "Visit https://docs.docker.com/get-docker/ for installation instructions."
    )


def is_docker_running() -> bool:
    """Check if Docker daemon is running."""
    docker_cmd = shutil.which("docker")
    if not docker_cmd:
        return False
    try:
        result = subprocess.run(
            [docker_cmd, "info"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def is_docker_installed() -> bool:
    """Check if Docker CLI is installed."""
    return shutil.which("docker") is not None


class DockerError(Exception):
    """Docker-specific error with actionable messages."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    @classmethod
    def not_installed(cls) -> "DockerError":
        """Create error for missing docker package."""
        return cls(
            "Docker Python package not installed. "
            "Install it with: pip install docker"
        )

    @classmethod
    def docker_not_installed(cls) -> "DockerError":
        """Create error when Docker itself is not installed."""
        return cls(get_docker_install_instructions())

    @classmethod
    def daemon_not_running(cls) -> "DockerError":
        """Create error for Docker daemon not running."""
        plat = get_platform()
        if plat == "macos":
            return cls(
                "Docker daemon is not running.\n"
                "Open Docker Desktop from your Applications folder to start it.\n\n"
                "Or start from command line:\n"
                "  open -a Docker"
            )
        elif plat == "linux":
            return cls(
                "Docker daemon is not running.\n"
                "Start it with:\n"
                "  sudo systemctl start docker\n\n"
                "To start automatically on boot:\n"
                "  sudo systemctl enable docker"
            )
        elif plat == "windows":
            return cls(
                "Docker daemon is not running.\n"
                "Open Docker Desktop from the Start menu to start it."
            )
        return cls(
            "Docker daemon is not running. "
            "Start Docker Desktop or run 'sudo systemctl start docker'"
        )

    @classmethod
    def container_not_found(cls, agent_id: str) -> "DockerError":
        """Create error for container not found."""
        return cls(
            f"Container '{agent_id}' not found. "
            "Run 'agency-quickdeploy list --provider docker' to see available agents."
        )

    @classmethod
    def image_not_found(cls, image: str) -> "DockerError":
        """Create error for image not found."""
        return cls(
            f"Docker image '{image}' not found. "
            "Run 'docker pull {image}' or 'agency-quickdeploy init --provider docker'"
        )

    @classmethod
    def permission_denied(cls) -> "DockerError":
        """Create error for Docker permission denied."""
        plat = get_platform()
        if plat == "macos":
            # macOS with Docker Desktop shouldn't have permission issues
            return cls(
                "Permission denied connecting to Docker.\n"
                "Make sure Docker Desktop is running.\n\n"
                "Open Docker Desktop from Applications, or run:\n"
                "  open -a Docker"
            )
        elif plat == "linux":
            return cls(
                "Permission denied connecting to Docker daemon.\n"
                "Fix this by adding your user to the docker group:\n"
                "  sudo usermod -aG docker $USER\n"
                "  newgrp docker\n\n"
                "Or log out and back in for the change to take effect."
            )
        return cls(
            "Permission denied connecting to Docker daemon.\n"
            "Fix this by adding your user to the docker group:\n"
            "  sudo usermod -aG docker $USER\n"
            "Then log out and back in (or run: newgrp docker)\n\n"
            "Alternatively, run with sudo (not recommended for regular use)."
        )


class DockerProvider(BaseProvider):
    """Local Docker provider for 24/7 agents on user's machine.

    This provider runs Claude agents in Docker containers on the local
    machine. No cloud infrastructure is required - state is stored in
    the local filesystem.

    Attributes:
        data_dir: Local directory for agent data (~/.agency by default)
        image: Docker image to use for agent containers
    """

    def __init__(self, config: QuickDeployConfig):
        """Initialize Docker provider.

        Args:
            config: QuickDeploy configuration with Docker settings
        """
        # Check for docker Python package first
        if not DOCKER_AVAILABLE:
            raise DockerError.not_installed()

        # Check if Docker CLI is installed on the system
        if not is_docker_installed():
            raise DockerError.docker_not_installed()

        self.config = config
        self.data_dir = Path(config.docker_data_dir or "~/.agency").expanduser()
        self.agents_dir = self.data_dir / "agents"
        self.image = config.docker_image
        self._docker: Optional[docker.DockerClient] = None
        self._platform = get_platform()

    @property
    def docker(self) -> "docker.DockerClient":
        """Lazy-initialize Docker client."""
        if self._docker is None:
            try:
                self._docker = docker.from_env()
                # Test connection
                self._docker.ping()
            except PermissionError:
                raise DockerError.permission_denied()
            except Exception as e:
                error_str = str(e)
                if "Permission denied" in error_str or "PermissionError" in error_str:
                    raise DockerError.permission_denied()
                if "Connection refused" in error_str or "Cannot connect" in error_str:
                    # Check if Docker is installed but not running
                    if is_docker_installed():
                        raise DockerError.daemon_not_running()
                    else:
                        raise DockerError.docker_not_installed()
                raise
        return self._docker

    def _ensure_image(self) -> bool:
        """Ensure the agent image is available locally.

        Returns:
            True if image is available, raises exception otherwise
        """
        try:
            self.docker.images.get(self.image)
            return True
        except NotFound:
            # Try to pull the image
            try:
                self.docker.images.pull(self.image)
                return True
            except Exception:
                raise DockerError.image_not_found(self.image)

    def launch(
        self,
        agent_id: str,
        prompt: str,
        credentials: Optional[Credentials],
        **kwargs: Any,
    ) -> DeploymentResult:
        """Launch an agent in a local Docker container.

        Args:
            agent_id: Unique identifier for the agent
            prompt: Task prompt for the agent
            credentials: Authentication credentials
            **kwargs: Additional options (repo, branch, max_iterations, no_shutdown)

        Returns:
            DeploymentResult with launch status
        """
        try:
            # Ensure image is available
            self._ensure_image()

            # Create agents directory - mount the parent so agent_id paths work correctly
            # Agent-runner creates /workspace/{agent_id}/project inside container
            self.agents_dir.mkdir(parents=True, exist_ok=True)

            # Build environment variables for the container
            env = {
                "AGENT_ID": agent_id,
                "AGENT_PROMPT": prompt,
                "MAX_ITERATIONS": str(kwargs.get("max_iterations", 0)),
                "NO_SHUTDOWN": "true" if kwargs.get("no_shutdown") else "false",
                # Set HOME to workspace since we run as host UID
                # which may not have a home directory in the container
                "HOME": "/workspace",
            }

            # Add repo/branch if provided
            if kwargs.get("repo"):
                env["REPO_URL"] = kwargs["repo"]
            if kwargs.get("branch"):
                env["REPO_BRANCH"] = kwargs["branch"]

            # Add credentials from environment or passed credentials
            if credentials:
                cred_vars = credentials.get_env_vars()
                env.update(cred_vars)
            else:
                # Fall back to environment variables
                if os.environ.get("ANTHROPIC_API_KEY"):
                    env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
                if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
                    env["CLAUDE_CODE_OAUTH_TOKEN"] = os.environ["CLAUDE_CODE_OAUTH_TOKEN"]
                env["AUTH_TYPE"] = os.environ.get("QUICKDEPLOY_AUTH_TYPE", "api_key")

            # Check for existing container with same name
            try:
                existing = self.docker.containers.get(agent_id)
                existing.remove(force=True)
            except NotFound:
                pass

            # Build container run parameters
            run_params = {
                "image": self.image,
                "name": agent_id,
                "detach": True,
                "environment": env,
                "volumes": {
                    str(self.agents_dir): {"bind": "/workspace", "mode": "rw"},
                },
                "labels": {
                    "agency.agent": "true",
                    "agency.agent-id": agent_id,
                    "agency.provider": "docker",
                },
                "restart_policy": {"Name": "unless-stopped"},
            }

            # Set user for container - needed for Claude CLI (refuses to run as root)
            # On Linux: run as host user to match volume permissions
            # On macOS: Docker Desktop handles file permissions automatically via file sharing,
            #           but we still need non-root user for Claude CLI
            # On Windows: Docker Desktop with WSL2 handles permissions, use default user
            if self._platform in ("linux", "macos"):
                user_id = os.getuid()
                group_id = os.getgid()
                run_params["user"] = f"{user_id}:{group_id}"
            # Windows with Docker Desktop uses WSL2 which handles permissions differently
            # We don't set user, letting the container use its default non-root user

            # Run the container
            # Mount agents_dir to /workspace so agent-runner creates /workspace/{agent_id}/project
            # This maps to ~/.agency/agents/{agent_id}/project on the host
            container = self.docker.containers.run(**run_params)

            return DeploymentResult(
                agent_id=agent_id,
                provider="docker",
                status="launching",
            )

        except DockerError:
            raise
        except Exception as e:
            return DeploymentResult(
                agent_id=agent_id,
                provider="docker",
                status="failed",
                error=str(e),
            )

    def status(self, agent_id: str) -> dict:
        """Get agent status from Docker container.

        Args:
            agent_id: Agent identifier

        Returns:
            Status dict with agent info
        """
        try:
            container = self.docker.containers.get(agent_id)

            # Map Docker status to our status vocabulary
            docker_status = container.status
            status_map = {
                "running": "running",
                "created": "launching",
                "restarting": "launching",
                "paused": "stopped",
                "exited": "completed",
                "dead": "failed",
            }

            # Check if container exited with error
            if docker_status == "exited":
                exit_code = container.attrs.get("State", {}).get("ExitCode", 0)
                if exit_code != 0:
                    status_map["exited"] = "failed"

            # Get agent directory for local state
            # Agent-runner creates /workspace/{agent_id}/project which maps to agents_dir/{agent_id}/project
            agent_dir = self.agents_dir / agent_id

            # Check for feature_list.json to determine progress
            feature_list_path = agent_dir / "project" / "feature_list.json"
            features_status = None
            if feature_list_path.exists():
                try:
                    import json
                    with open(feature_list_path) as f:
                        data = json.load(f)
                        features = data.get("features", [])
                        completed = sum(1 for f in features if f.get("status") == "completed")
                        total = len(features)
                        features_status = f"{completed}/{total} features completed"
                except Exception:
                    pass

            result = {
                "agent_id": agent_id,
                "status": status_map.get(docker_status, docker_status),
                "docker_status": docker_status,
                "container_id": container.short_id,
                "logs_command": f"docker logs -f {agent_id}",
                "ssh_command": f"docker exec -it {agent_id} bash",
            }

            if features_status:
                result["features"] = features_status

            return result

        except NotFound:
            return {
                "agent_id": agent_id,
                "status": "not_found",
            }
        except Exception as e:
            return {
                "agent_id": agent_id,
                "status": "error",
                "error": str(e),
            }

    def logs(self, agent_id: str) -> Optional[str]:
        """Get agent logs from Docker container.

        Args:
            agent_id: Agent identifier

        Returns:
            Log content as string, or None if not available
        """
        try:
            container = self.docker.containers.get(agent_id)
            return container.logs(tail=500).decode("utf-8", errors="replace")
        except NotFound:
            # Try to get logs from local file
            log_path = self.agents_dir / agent_id / "agent.log"
            if log_path.exists():
                return log_path.read_text()
            return None
        except Exception:
            return None

    def stop(self, agent_id: str) -> bool:
        """Stop an agent by removing its Docker container.

        Args:
            agent_id: Agent identifier

        Returns:
            True if stopped successfully
        """
        try:
            container = self.docker.containers.get(agent_id)
            container.remove(force=True)
            return True
        except NotFound:
            return True  # Already stopped/removed
        except Exception:
            return False

    def list_agents(self) -> list[dict]:
        """List all Docker agents.

        Returns:
            List of agent dicts with name, status, etc.
        """
        try:
            containers = self.docker.containers.list(
                all=True,
                filters={"label": "agency.agent=true"}
            )

            agents = []
            for container in containers:
                agent_id = container.labels.get("agency.agent-id", container.name)

                # Only include agents from this provider
                if container.labels.get("agency.provider") != "docker":
                    continue

                agents.append({
                    "name": agent_id,
                    "status": container.status,
                    "container_id": container.short_id,
                })

            return agents
        except Exception:
            return []

    def pull_image(self) -> bool:
        """Pull the agent Docker image.

        Returns:
            True if image was pulled successfully
        """
        try:
            self.docker.images.pull(self.image)
            return True
        except Exception:
            return False
