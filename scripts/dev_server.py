#!/usr/bin/env python3
"""Dev Server: Launch an interactive development VM with all tooling installed.

NOTE: Currently uses Google Cloud Platform (GCP) only.
      TODO: Add support for AWS, Docker, and other providers.

This is different from agency-quickdeploy:
- agency-quickdeploy: Launches AUTONOMOUS agents that work independently
- dev_server.py: Launches INTERACTIVE VMs for YOU to SSH in and develop

The VM comes pre-configured for agency development:
- Ubuntu 22.04 with Python 3.11
- Claude Code CLI installed and ready
- Repo cloned with dependencies installed
- Ready for interactive SSH access

The VM does NOT run an agent automatically - it's meant for interactive development,
debugging, and testing.

Prerequisites:
- gcloud CLI authenticated (`gcloud auth login`)
- .env file with QUICKDEPLOY_PROJECT set
- For Claude Code: API key in Secret Manager or ANTHROPIC_API_KEY in .env

Usage:
    # Launch a new dev server (clones from GitHub)
    python scripts/dev_server.py launch

    # Launch with your LOCAL code (uploads via GCS)
    python scripts/dev_server.py launch --local

    # Launch with a name
    python scripts/dev_server.py launch --name my-dev-box

    # Launch with specific branch from GitHub
    python scripts/dev_server.py launch --branch feature/my-branch

    # List running dev servers
    python scripts/dev_server.py list

    # SSH into a dev server (two options):
    python scripts/dev_server.py ssh my-dev-box
    # OR directly via gcloud:
    gcloud compute ssh my-dev-box --zone=us-central1-a --project=YOUR_PROJECT

    # Stop and delete a dev server
    python scripts/dev_server.py stop my-dev-box

    # Stop all dev servers
    python scripts/dev_server.py stop --all
"""
import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Find project root
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent


def load_dotenv(path: str = ".env") -> None:
    """Load environment variables from a .env file."""
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


@dataclass
class DevServerConfig:
    """Configuration for dev server."""
    project: str
    zone: str = "us-central1-a"
    machine_type: str = "e2-standard-4"
    repo_url: str = "https://github.com/anthropics/agency.git"
    branch: str = "main"
    disk_size_gb: int = 50
    spot: bool = False
    anthropic_api_key: Optional[str] = None
    use_local_code: bool = False
    bucket: Optional[str] = None

    def __post_init__(self):
        if self.bucket is None:
            self.bucket = f"agency-ci-{self.project}"

    @classmethod
    def from_env(cls, args: argparse.Namespace) -> "DevServerConfig":
        """Load config from environment and CLI args."""
        project = os.environ.get("QUICKDEPLOY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError(
                "GCP project not configured. Set QUICKDEPLOY_PROJECT in .env or environment."
            )

        zone = args.zone or os.environ.get("QUICKDEPLOY_ZONE", "us-central1-a")
        machine_type = args.machine_type or os.environ.get("DEV_SERVER_MACHINE_TYPE", "e2-standard-4")
        bucket = os.environ.get("QUICKDEPLOY_BUCKET")

        # Get API key if available (for Claude Code on the VM)
        api_key = os.environ.get("ANTHROPIC_API_KEY")

        return cls(
            project=project,
            zone=zone,
            machine_type=machine_type,
            repo_url=getattr(args, 'repo', "https://github.com/anthropics/agency.git"),
            branch=getattr(args, 'branch', None) or "main",
            spot=getattr(args, 'spot', False),
            anthropic_api_key=api_key,
            use_local_code=getattr(args, 'local', False),
            bucket=bucket,
        )


def run_cmd(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command and optionally capture output."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def get_current_branch() -> Optional[str]:
    """Get current git branch if in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def create_tarball(source_dir: Path, output_path: Path) -> None:
    """Create a tarball of the source directory, excluding unnecessary files."""
    print(f"Creating tarball of {source_dir}...")

    exclude_patterns = [
        '.git',
        '__pycache__',
        '*.pyc',
        '.pytest_cache',
        '*.egg-info',
        'venv',
        '.venv',
        'node_modules',
        '.env',
        '*.log',
        '.mypy_cache',
        '.ruff_cache',
    ]

    def filter_func(tarinfo):
        name = tarinfo.name
        for pattern in exclude_patterns:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return None
            elif pattern in name.split('/'):
                return None
        return tarinfo

    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(source_dir, arcname="agency", filter=filter_func)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Created {output_path.name} ({size_mb:.1f} MB)")


def ensure_bucket_exists(config: DevServerConfig) -> bool:
    """Ensure the GCS bucket exists, create if not."""
    result = subprocess.run(
        ["gsutil", "ls", f"gs://{config.bucket}"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        return True

    print(f"Creating GCS bucket: {config.bucket}")
    try:
        run_cmd([
            "gsutil", "mb", "-p", config.project,
            "-l", config.zone.rsplit("-", 1)[0],
            f"gs://{config.bucket}"
        ])
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create bucket: {e}")
        return False


def upload_to_gcs(local_path: Path, config: DevServerConfig, gcs_path: str) -> bool:
    """Upload a file to GCS."""
    full_gcs_path = f"gs://{config.bucket}/{gcs_path}"
    print(f"Uploading to {full_gcs_path}...")
    try:
        run_cmd(["gsutil", "cp", str(local_path), full_gcs_path])
        return True
    except subprocess.CalledProcessError:
        return False


def generate_dev_startup_script(config: DevServerConfig, tarball_gcs_path: Optional[str] = None) -> str:
    """Generate the VM startup script for dev environment."""

    # Optionally set up API key
    api_key_setup = ""
    if config.anthropic_api_key:
        api_key_setup = f'''
# Set up Anthropic API key
echo 'export ANTHROPIC_API_KEY="{config.anthropic_api_key}"' >> /root/.bashrc
echo 'export ANTHROPIC_API_KEY="{config.anthropic_api_key}"' >> /etc/profile.d/agency.sh
chmod 644 /etc/profile.d/agency.sh
'''

    # Code setup depends on whether we're using local code or GitHub
    if tarball_gcs_path:
        code_setup = f'''
# Download code from GCS (local upload)
echo "Downloading code from GCS..."
cd /root
gsutil cp gs://{config.bucket}/{tarball_gcs_path} code.tar.gz
tar -xzf code.tar.gz
rm code.tar.gz
cd agency
'''
    else:
        code_setup = f'''
# Clone repo from GitHub
echo "Cloning repo from GitHub..."
cd /root
git clone --branch {config.branch} {config.repo_url} agency
cd agency
'''

    return f'''#!/bin/bash
set -e

# Log everything
exec > >(tee -a /var/log/dev-server-setup.log) 2>&1
echo "=== Dev Server Setup Started at $(date) ==="

# Install system dependencies
echo "Installing system packages..."
apt-get update
apt-get install -y \
    software-properties-common \
    git curl wget \
    build-essential \
    jq htop tmux vim \
    ca-certificates gnupg

# Install Python 3.11 (project requires >= 3.11)
echo "Installing Python 3.11..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev

# Install Node.js (for Claude Code)
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install Claude Code CLI
echo "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

{api_key_setup}

{code_setup}

# Create virtual environment with Python 3.11
echo "Setting up Python environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install package with all dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e ".[server,dev]"

# Set up bashrc for convenience
cat >> /root/.bashrc << 'BASHRC_EOF'
# Agency dev environment
cd /root/agency 2>/dev/null || true
source /root/agency/venv/bin/activate 2>/dev/null || true
alias ll='ls -la'
alias gs='git status'
alias gd='git diff'
alias pytest='python -m pytest'
echo ""
echo "========================================"
echo "  Agency Dev Server Ready!"
echo "========================================"
echo ""
echo "Useful commands:"
echo "  pytest                    - Run tests"
echo "  claude                    - Start Claude Code"
echo "  agency-quickdeploy --help - CLI help"
echo ""
BASHRC_EOF

# Signal that setup is complete
curl -s -X PUT -H "Metadata-Flavor: Google" \
    -d "ready" \
    "http://metadata.google.internal/computeMetadata/v1/instance/guest-attributes/dev-server/status" || true

echo "=== Dev Server Setup Complete at $(date) ==="
'''


def create_dev_server(config: DevServerConfig, name: str, tarball_gcs_path: Optional[str] = None) -> bool:
    """Create a dev server VM."""
    print(f"\nCreating dev server: {name}")

    # Write startup script to temp file
    script_path = f"/tmp/{name}-startup.sh"
    startup_script = generate_dev_startup_script(config, tarball_gcs_path)
    with open(script_path, "w") as f:
        f.write(startup_script)

    cmd = [
        "gcloud", "compute", "instances", "create", name,
        f"--project={config.project}",
        f"--zone={config.zone}",
        f"--machine-type={config.machine_type}",
        "--image-family=ubuntu-2204-lts",
        "--image-project=ubuntu-os-cloud",
        f"--boot-disk-size={config.disk_size_gb}GB",
        "--metadata-from-file", f"startup-script={script_path}",
        "--labels=dev-server=true,agency=true",
        "--scopes=cloud-platform",
        "--format=json",
    ]

    if config.spot:
        cmd.extend(["--provisioning-model=SPOT", "--instance-termination-action=DELETE"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        instance_info = json.loads(result.stdout)
        if instance_info:
            external_ip = None
            for nic in instance_info[0].get("networkInterfaces", []):
                for ac in nic.get("accessConfigs", []):
                    if ac.get("natIP"):
                        external_ip = ac["natIP"]
                        break
            print(f"  VM created!")
            if external_ip:
                print(f"  External IP: {external_ip}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create VM: {e.stderr}")
        return False


def wait_for_ready(config: DevServerConfig, name: str, timeout_minutes: int = 10) -> bool:
    """Wait for dev server to finish setup."""
    print(f"\nWaiting for dev server setup (timeout: {timeout_minutes}m)...")

    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while time.time() - start_time < timeout_seconds:
        result = subprocess.run(
            [
                "gcloud", "compute", "instances", "get-guest-attributes", name,
                f"--project={config.project}",
                f"--zone={config.zone}",
                "--query-path=dev-server/status",
                "--format=value(value)",
            ],
            capture_output=True, text=True
        )

        if result.returncode == 0 and result.stdout.strip() == "ready":
            return True

        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        print(f"  Setting up... {mins}m {secs}s elapsed", end="\r")
        time.sleep(10)

    return False


def list_dev_servers(project: str) -> list[dict]:
    """List all dev servers."""
    result = subprocess.run(
        [
            "gcloud", "compute", "instances", "list",
            f"--project={project}",
            "--filter=labels.dev-server=true",
            "--format=json",
        ],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        return []

    try:
        instances = json.loads(result.stdout)
        servers = []
        for inst in instances:
            external_ip = None
            for nic in inst.get("networkInterfaces", []):
                for ac in nic.get("accessConfigs", []):
                    if ac.get("natIP"):
                        external_ip = ac["natIP"]
                        break

            # Extract zone from zone URL
            zone = inst.get("zone", "").split("/")[-1]

            servers.append({
                "name": inst["name"],
                "status": inst["status"],
                "zone": zone,
                "external_ip": external_ip,
                "machine_type": inst.get("machineType", "").split("/")[-1],
            })
        return servers
    except json.JSONDecodeError:
        return []


def ssh_to_server(project: str, zone: str, name: str) -> None:
    """SSH into a dev server."""
    cmd = [
        "gcloud", "compute", "ssh", name,
        f"--project={project}",
        f"--zone={zone}",
    ]
    print(f"Connecting to {name}...")
    os.execvp("gcloud", cmd)


def delete_dev_server(project: str, zone: str, name: str) -> bool:
    """Delete a dev server."""
    print(f"Deleting dev server: {name}")
    try:
        run_cmd([
            "gcloud", "compute", "instances", "delete", name,
            f"--project={project}",
            f"--zone={zone}",
            "--quiet",
        ])
        return True
    except subprocess.CalledProcessError:
        return False


def load_env_files():
    """Load .env from multiple possible locations."""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(str(env_path))

    root_env = PROJECT_ROOT / ".env"
    if root_env.exists():
        load_dotenv(str(root_env))


def cmd_launch(args):
    """Handle 'launch' command."""
    load_env_files()

    # Auto-detect branch if not specified and using GitHub
    if not args.local and args.branch is None:
        args.branch = get_current_branch() or "main"
        print(f"Using branch: {args.branch}")

    try:
        config = DevServerConfig.from_env(args)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Generate name if not provided
    name = args.name
    if not name:
        timestamp = int(time.time())
        name = f"dev-{timestamp}"

    print("=" * 60)
    print("Dev Server Launch")
    print("=" * 60)
    print(f"Name:         {name}")
    print(f"Project:      {config.project}")
    print(f"Zone:         {config.zone}")
    print(f"Machine:      {config.machine_type}")
    if config.use_local_code:
        print(f"Code:         Local (uploading to GCS)")
    else:
        print(f"Code:         GitHub ({config.branch})")
    print(f"Spot:         {config.spot}")
    print(f"API Key:      {'configured' if config.anthropic_api_key else 'not set'}")
    print("=" * 60)

    tarball_gcs_path = None

    # If using local code, create and upload tarball
    if config.use_local_code:
        if not ensure_bucket_exists(config):
            sys.exit(1)

        with tempfile.TemporaryDirectory() as tmpdir:
            tarball_path = Path(tmpdir) / f"{name}.tar.gz"
            create_tarball(PROJECT_ROOT, tarball_path)

            tarball_gcs_path = f"dev-servers/{name}.tar.gz"
            if not upload_to_gcs(tarball_path, config, tarball_gcs_path):
                print("ERROR: Failed to upload code to GCS")
                sys.exit(1)

    if not create_dev_server(config, name, tarball_gcs_path):
        sys.exit(1)

    if wait_for_ready(config, name):
        print("\n")
        print("=" * 60)
        print(" Dev server ready!")
        print("=" * 60)
        print(f"\nTo connect:")
        print(f"  python scripts/dev_server.py ssh {name}")
        print(f"  # or directly:")
        print(f"  gcloud compute ssh {name} --zone={config.zone} --project={config.project}")
        print(f"\nTo stop:")
        print(f"  python scripts/dev_server.py stop {name}")
    else:
        print("\n")
        print("Warning: Setup might still be running. Try SSH in a few minutes.")
        print(f"  gcloud compute ssh {name} --zone={config.zone} --project={config.project}")


def cmd_list(args):
    """Handle 'list' command."""
    load_env_files()

    project = os.environ.get("QUICKDEPLOY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        print("ERROR: GCP project not configured")
        sys.exit(1)

    servers = list_dev_servers(project)

    if not servers:
        print("No dev servers found.")
        return

    print(f"\n{'Name':<25} {'Status':<12} {'Zone':<20} {'IP':<16} {'Machine'}")
    print("-" * 90)
    for s in servers:
        print(f"{s['name']:<25} {s['status']:<12} {s['zone']:<20} {s['external_ip'] or 'N/A':<16} {s['machine_type']}")


def cmd_ssh(args):
    """Handle 'ssh' command."""
    load_env_files()

    project = os.environ.get("QUICKDEPLOY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    zone = os.environ.get("QUICKDEPLOY_ZONE", "us-central1-a")
    if not project:
        print("ERROR: GCP project not configured")
        sys.exit(1)

    # If no zone specified, try to find the server in any zone
    servers = list_dev_servers(project)
    for s in servers:
        if s['name'] == args.name:
            zone = s['zone']
            break

    ssh_to_server(project, zone, args.name)


def cmd_stop(args):
    """Handle 'stop' command."""
    load_env_files()

    project = os.environ.get("QUICKDEPLOY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    zone = os.environ.get("QUICKDEPLOY_ZONE", "us-central1-a")
    if not project:
        print("ERROR: GCP project not configured")
        sys.exit(1)

    if args.all:
        servers = list_dev_servers(project)
        if not servers:
            print("No dev servers to stop.")
            return

        print(f"Stopping {len(servers)} dev server(s)...")
        for s in servers:
            delete_dev_server(project, s['zone'], s['name'])
    else:
        if not args.name:
            print("ERROR: Specify a server name or use --all")
            sys.exit(1)

        # Find the server's zone
        servers = list_dev_servers(project)
        for s in servers:
            if s['name'] == args.name:
                zone = s['zone']
                break

        delete_dev_server(project, zone, args.name)


def main():
    parser = argparse.ArgumentParser(
        description="Manage dev server VMs for agency development (GCP only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SSH Options:
  After launching, you can SSH in two ways:

  1. Via this script:
     python scripts/dev_server.py ssh SERVER_NAME

  2. Directly via gcloud:
     gcloud compute ssh SERVER_NAME --zone=ZONE --project=PROJECT

Note: Currently only supports GCP. Future versions will add AWS, Docker, etc.
""",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Launch command
    launch_parser = subparsers.add_parser("launch", help="Launch a new dev server")
    launch_parser.add_argument("--name", help="Server name (auto-generated if not set)")
    launch_parser.add_argument("--branch", help="Git branch (default: current or main)")
    launch_parser.add_argument("--repo", default="https://github.com/anthropics/agency.git",
                               help="Git repository URL")
    launch_parser.add_argument("--local", action="store_true",
                               help="Upload local code instead of cloning from GitHub")
    launch_parser.add_argument("--zone", help="GCP zone")
    launch_parser.add_argument("--machine-type", help="Machine type (default: e2-standard-4)")
    launch_parser.add_argument("--spot", action="store_true", help="Use spot instance (cheaper but can be preempted)")

    # List command
    subparsers.add_parser("list", help="List running dev servers")

    # SSH command
    ssh_parser = subparsers.add_parser("ssh", help="SSH into a dev server")
    ssh_parser.add_argument("name", help="Server name")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop and delete a dev server")
    stop_parser.add_argument("name", nargs="?", help="Server name")
    stop_parser.add_argument("--all", action="store_true", help="Stop all dev servers")

    args = parser.parse_args()

    if args.command == "launch":
        cmd_launch(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "ssh":
        cmd_ssh(args)
    elif args.command == "stop":
        cmd_stop(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
