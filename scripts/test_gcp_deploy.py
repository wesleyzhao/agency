#!/usr/bin/env python3
"""Test GCP deployment of an agent."""
import sys
import time
import argparse

# Add project root to path
sys.path.insert(0, "/Users/wesley/projects/agency")

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
    parser.add_argument("--cleanup", action="store_true", help="Delete VM after test")
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

    # Monitor VM
    print()
    print("=== Monitoring VM ===")
    print("The VM is now running the startup script. This may take 5-10 minutes.")
    print(f"View logs: gcloud compute instances get-serial-port-output {instance_name} --zone={config.gcp_zone} --project={config.gcp_project}")
    print(f"SSH: gcloud compute ssh {instance_name} --zone={config.gcp_zone} --project={config.gcp_project}")
    print()
    print(f"GCS output will be at: gs://{config.gcs_bucket}/agents/{agent_id}/")
    print()

    if args.cleanup:
        print("Waiting 60 seconds before cleanup...")
        time.sleep(60)
        print(f"Deleting VM {instance_name}...")
        vm.delete_instance(instance_name)
        print("VM deleted.")
    else:
        print(f"To delete the VM later: gcloud compute instances delete {instance_name} --zone={config.gcp_zone} --project={config.gcp_project}")


if __name__ == "__main__":
    main()
