#!/usr/bin/env python3
"""Test GCP deployment of an agent."""
import os
import sys
import time
import argparse
import subprocess

# Add project root to path
sys.path.insert(0, "/Users/wesley/projects/agency")

# Ensure gcloud tools are in PATH
GCLOUD_PATH = os.path.expanduser("~/google-cloud-sdk/bin")
if GCLOUD_PATH not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{GCLOUD_PATH}:{os.environ.get('PATH', '')}"

from agentctl.shared.config import Config
from agentctl.server.services.vm_manager import VMManager
from agentctl.server.services.startup_script import generate_startup_script
from agentctl.server.services.secret_manager import SecretManagerService


def main():
    parser = argparse.ArgumentParser(description="Test GCP agent deployment")
    parser.add_argument("--prompt", default="Create a file called hello.txt containing 'Hello from GCP!'")
    parser.add_argument("--max-iterations", type=int, default=1)
    parser.add_argument("--machine-type", default="e2-medium")
    parser.add_argument("--spot", action="store_true", help="Use spot instance")
    parser.add_argument("--no-shutdown", action="store_true", help="Keep VM running after completion for SSH inspection")
    parser.add_argument("--wait", action="store_true", help="Wait for completion and download output")
    parser.add_argument("--output-dir", default="./agent-output", help="Directory to download output to")
    args = parser.parse_args()

    # Load config
    config = Config.load()
    if not config.gcp_project:
        print("ERROR: No GCP project configured. Run 'agentctl init' first.")
        sys.exit(1)

    print(f"=== GCP Deployment Test ===")
    print(f"Project: {config.gcp_project}")
    print(f"Zone: {config.gcp_zone}")
    print(f"Bucket: {config.gcs_bucket}")
    print(f"Prompt: {args.prompt}")
    print(f"Max iterations: {args.max_iterations}")
    print(f"No shutdown: {args.no_shutdown}")
    print()

    # Generate agent ID
    agent_id = f"test-{int(time.time())}"
    instance_name = f"agent-{agent_id}"

    # Generate startup script
    print("Generating startup script...")
    startup_script = generate_startup_script(
        agent_id=agent_id,
        prompt=args.prompt,
        engine="claude",
        project=config.gcp_project,
        bucket=config.gcs_bucket or f"{config.gcp_project}-agentctl",
        master_url="",  # No master server for this test
        max_iterations=args.max_iterations,
        no_shutdown=args.no_shutdown,
        zone=config.gcp_zone,
    )

    # Save startup script for inspection
    script_path = f"/tmp/startup_script_{agent_id}.sh"
    with open(script_path, "w") as f:
        f.write(startup_script)
    print(f"Startup script saved to: {script_path}")

    # Get secrets
    print("Fetching secrets from Secret Manager...")
    secrets = SecretManagerService(config.gcp_project)
    metadata_items = {}

    try:
        api_key = secrets.get_secret("anthropic-api-key")
        if api_key:
            metadata_items["anthropic-api-key"] = api_key
            print("  - anthropic-api-key: found")
    except Exception as e:
        print(f"ERROR: Could not get API key: {e}")
        sys.exit(1)

    try:
        github_token = secrets.get_secret("github-token")
        if github_token:
            metadata_items["github-token"] = github_token
            print("  - github-token: found")
    except Exception:
        print("  - github-token: not found (optional)")

    # Create VM
    print()
    print(f"Creating VM: {instance_name}...")
    vm = VMManager(config.gcp_project, config.gcp_zone)

    try:
        result = vm.create_instance(
            name=instance_name,
            machine_type=args.machine_type,
            startup_script=startup_script,
            spot=args.spot,
            labels={"agent-id": agent_id, "test": "true"},
            metadata_items=metadata_items,
        )
        print(f"VM created successfully!")
        print(f"  - Name: {result['name']}")
        print(f"  - Status: {result['status']}")
        print(f"  - External IP: {result.get('external_ip', 'N/A')}")
    except Exception as e:
        print(f"ERROR: Failed to create VM: {e}")
        sys.exit(1)

    gcs_base = f"gs://{config.gcs_bucket}/agents/{agent_id}"

    # Monitor VM
    print()
    print("=== Monitoring VM ===")
    print("The VM is now running the startup script. This may take 5-10 minutes.")
    print()
    print("Useful commands:")
    print(f"  View logs:     gsutil cat {gcs_base}/logs/agent.log")
    print(f"  Check status:  gsutil cat {gcs_base}/status")
    print(f"  List output:   gsutil ls -r {gcs_base}/")
    print(f"  Download all:  gsutil -m cp -r {gcs_base}/workspace/ ./agent-output/")
    print()
    if args.no_shutdown:
        print(f"  SSH (after completion): gcloud compute ssh {instance_name} --zone={config.gcp_zone} --project={config.gcp_project}")
    print(f"  Delete VM:     gcloud compute instances delete {instance_name} --zone={config.gcp_zone} --project={config.gcp_project}")
    print()

    if args.wait:
        print("=== Waiting for completion ===")
        while True:
            # Check status
            result = subprocess.run(
                ["gsutil", "cat", f"{gcs_base}/status"],
                capture_output=True, text=True
            )
            status = result.stdout.strip()

            if status in ["completed", "failed"]:
                print(f"\nAgent finished with status: {status}")
                break

            print(f"  Status: {status or 'starting...'}", end="\r")
            time.sleep(30)

        # Download output
        print(f"\nDownloading output to {args.output_dir}/")
        os.makedirs(args.output_dir, exist_ok=True)
        subprocess.run([
            "gsutil", "-m", "rsync", "-r",
            f"{gcs_base}/workspace/",
            args.output_dir
        ])

        # Show what was downloaded
        print("\n=== Downloaded Files ===")
        subprocess.run(["find", args.output_dir, "-type", "f"])

        # Show the log
        print("\n=== Agent Log (last 50 lines) ===")
        subprocess.run([
            "gsutil", "cat", f"{gcs_base}/logs/agent.log"
        ])


if __name__ == "__main__":
    main()
