"""AWS provider implementation for agency-quickdeploy.

This module implements the BaseProvider interface using AWS EC2 instances
and S3 for state storage.

AWS credentials are loaded from the standard AWS credential chain:
- Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- AWS credentials file (~/.aws/credentials)
- IAM role (if running on EC2)
"""

import os
from typing import Optional, Any

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

from agency_quickdeploy.providers.base import BaseProvider, DeploymentResult
from agency_quickdeploy.config import QuickDeployConfig
from agency_quickdeploy.auth import Credentials


# Ubuntu 22.04 LTS AMI IDs by region (HVM, SSD, x86_64)
# These are the official Canonical AMIs
UBUNTU_AMIS = {
    "us-east-1": "ami-0c7217cdde317cfec",
    "us-east-2": "ami-05fb0b8c1424f266b",
    "us-west-1": "ami-0ce2cb35386fc22e9",
    "us-west-2": "ami-008fe2fc65df48dac",
    "eu-west-1": "ami-0905a3c97561e0b69",
    "eu-west-2": "ami-0e5f882be1900e43b",
    "eu-central-1": "ami-0faab6bdbac9486fb",
    "ap-northeast-1": "ami-07c589821f2b353aa",
    "ap-southeast-1": "ami-078c1149d8ad719a7",
    "ap-southeast-2": "ami-04f5097681773b989",
}


class AWSError(Exception):
    """AWS-specific error with actionable messages."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    @classmethod
    def not_installed(cls) -> "AWSError":
        """Create error for missing boto3 package."""
        return cls(
            "boto3 package not installed. "
            "Install it with: pip install boto3"
        )

    @classmethod
    def no_credentials(cls) -> "AWSError":
        """Create error for missing AWS credentials."""
        return cls(
            "AWS credentials not found. Configure credentials using:\n"
            "  - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)\n"
            "  - AWS CLI: aws configure\n"
            "  - IAM role (if running on EC2)"
        )

    @classmethod
    def region_not_supported(cls, region: str) -> "AWSError":
        """Create error for unsupported region."""
        return cls(
            f"Region '{region}' does not have a pre-configured Ubuntu AMI. "
            f"Supported regions: {', '.join(sorted(UBUNTU_AMIS.keys()))}"
        )

    @classmethod
    def instance_not_found(cls, agent_id: str) -> "AWSError":
        """Create error for instance not found."""
        return cls(
            f"Instance '{agent_id}' not found. "
            "Run 'agency-quickdeploy list --provider aws' to see available agents."
        )


class AWSProvider(BaseProvider):
    """AWS provider using EC2 instances and S3 for state.

    This provider launches agents as EC2 instances, using S3 for state
    storage. Credentials are passed via user-data.

    IMPORTANT: For S3 access from EC2 instances, you must configure one of:
    1. IAM instance profile with S3 permissions (recommended)
    2. Use the default VPC which has internet access + IAM role
    3. Configure AWS credentials in the startup script (current approach)

    For SSH access, ensure:
    1. Security group allows port 22 inbound
    2. Key pair is specified in instance launch (not yet implemented)

    Attributes:
        region: AWS region for resources
        bucket: S3 bucket for state storage
        instance_type: EC2 instance type
    """

    def __init__(self, config: QuickDeployConfig):
        """Initialize AWS provider.

        Args:
            config: QuickDeploy configuration with AWS settings
        """
        if not BOTO3_AVAILABLE:
            raise AWSError.not_installed()

        self.config = config
        self.region = config.aws_region
        self.bucket = config.aws_bucket
        self.instance_type = config.aws_instance_type
        self._ec2 = None
        self._s3 = None

    @property
    def ec2(self):
        """Lazy-initialize EC2 resource."""
        if self._ec2 is None:
            try:
                self._ec2 = boto3.resource('ec2', region_name=self.region)
                # Test credentials
                list(self._ec2.instances.limit(1))
            except NoCredentialsError:
                raise AWSError.no_credentials()
        return self._ec2

    @property
    def s3(self):
        """Lazy-initialize S3 client."""
        if self._s3 is None:
            try:
                self._s3 = boto3.client('s3', region_name=self.region)
            except NoCredentialsError:
                raise AWSError.no_credentials()
        return self._s3

    def _get_ami(self) -> str:
        """Get the Ubuntu AMI ID for the current region."""
        if self.region not in UBUNTU_AMIS:
            raise AWSError.region_not_supported(self.region)
        return UBUNTU_AMIS[self.region]

    def _ensure_bucket(self) -> str:
        """Ensure S3 bucket exists, creating if needed.

        Returns:
            Bucket name
        """
        if not self.bucket:
            # Auto-generate bucket name
            try:
                sts = boto3.client('sts', region_name=self.region)
                account_id = sts.get_caller_identity()['Account']
                self.bucket = f"agency-quickdeploy-{account_id}-{self.region}"
            except Exception:
                self.bucket = f"agency-quickdeploy-{self.region}"

        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # Create bucket
                if self.region == 'us-east-1':
                    self.s3.create_bucket(Bucket=self.bucket)
                else:
                    self.s3.create_bucket(
                        Bucket=self.bucket,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )

        return self.bucket

    def _generate_startup_script(
        self,
        agent_id: str,
        prompt: str,
        credentials: Optional[Credentials],
        **kwargs: Any,
    ) -> str:
        """Generate EC2 user-data startup script.

        Args:
            agent_id: Agent identifier
            prompt: Task prompt
            credentials: Authentication credentials
            **kwargs: Additional options

        Returns:
            Bash startup script
        """
        # Get credentials from passed object or environment
        api_key = ""
        oauth_token = ""
        auth_type = "api_key"

        if credentials:
            cred_vars = credentials.get_env_vars()
            api_key = cred_vars.get("ANTHROPIC_API_KEY", "")
            oauth_token = cred_vars.get("CLAUDE_CODE_OAUTH_TOKEN", "")
            auth_type = cred_vars.get("AUTH_TYPE", "api_key")
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
            auth_type = os.environ.get("QUICKDEPLOY_AUTH_TYPE", "api_key")

        max_iterations = kwargs.get("max_iterations", 0)
        no_shutdown = "true" if kwargs.get("no_shutdown") else "false"
        repo_url = kwargs.get("repo", "")
        repo_branch = kwargs.get("branch", "main")

        # Escape prompt for embedding in script
        import shlex
        escaped_prompt = shlex.quote(prompt)

        script = f'''#!/bin/bash
set -e

# === Configuration ===
AGENT_ID="{agent_id}"
BUCKET="{self.bucket}"
MAX_ITERATIONS="{max_iterations}"
NO_SHUTDOWN="{no_shutdown}"
REPO_URL="{repo_url}"
REPO_BRANCH="{repo_branch}"
AUTH_TYPE="{auth_type}"
ANTHROPIC_API_KEY="{api_key}"
CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}"

exec > >(tee /var/log/agent-startup.log) 2>&1

log() {{ echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }}

log "=== AWS Agent Starting ==="
log "Agent ID: $AGENT_ID"
log "Region: {self.region}"

# === Update status to starting ===
echo "starting" > /tmp/agent_status
aws s3 cp /tmp/agent_status s3://$BUCKET/agents/$AGENT_ID/status --quiet || true

# === Install dependencies ===
log "Installing dependencies..."
apt-get update
apt-get install -y git curl python3 python3-pip python3-venv unzip

# Install AWS CLI v2
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
unzip -q /tmp/awscliv2.zip -d /tmp
/tmp/aws/install --update || true

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install Claude Code CLI
log "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# === Setup agent user ===
log "Setting up agent user..."
useradd -m -s /bin/bash agent || true
AGENT_HOME=/home/agent
WORKSPACE=$AGENT_HOME/workspace
PROJECT_DIR=$WORKSPACE/project

mkdir -p $PROJECT_DIR
chown -R agent:agent $AGENT_HOME

# === Setup credentials ===
log "Setting up credentials..."
if [ "$AUTH_TYPE" = "oauth" ] && [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    mkdir -p $AGENT_HOME/.claude
    cat > $AGENT_HOME/.claude/.credentials.json << CREDS_EOF
{{"claudeAiOauth": {{"accessToken": "$CLAUDE_CODE_OAUTH_TOKEN"}}}}
CREDS_EOF
    chown -R agent:agent $AGENT_HOME/.claude
    log "OAuth credentials configured"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> $AGENT_HOME/.bashrc
    log "API key configured"
else
    log "WARNING: No credentials configured"
fi

# === Clone repository if specified ===
if [ -n "$REPO_URL" ]; then
    log "Cloning repository: $REPO_URL"
    sudo -u agent git clone --depth 1 -b $REPO_BRANCH "$REPO_URL" $PROJECT_DIR || true
fi

# === Save prompt ===
cat > $WORKSPACE/app_spec.txt << 'PROMPT_EOF'
{prompt}
PROMPT_EOF

# === Create empty feature_list.json (workaround for first-file bug) ===
cat > $PROJECT_DIR/feature_list.json << 'FEATURE_EOF'
{{"features": []}}
FEATURE_EOF
chown -R agent:agent $WORKSPACE

# === Update status to running ===
echo "running" > /tmp/agent_status
aws s3 cp /tmp/agent_status s3://$BUCKET/agents/$AGENT_ID/status --quiet || true

# === Setup sync to S3 ===
log "Setting up S3 sync..."
cat > /usr/local/bin/sync-to-s3.sh << 'SYNC_EOF'
#!/bin/bash
BUCKET="{self.bucket}"
AGENT_ID="{agent_id}"
WORKSPACE=/home/agent/workspace

# Sync workspace files
for fpath in $WORKSPACE/project/feature_list.json $WORKSPACE/project/claude-progress.txt; do
    if [ -f "$fpath" ]; then
        aws s3 cp "$fpath" "s3://$BUCKET/agents/$AGENT_ID/$(basename $fpath)" --quiet 2>/dev/null || true
    fi
done

# Sync logs
if [ -f /var/log/agent.log ]; then
    aws s3 cp /var/log/agent.log "s3://$BUCKET/agents/$AGENT_ID/logs/agent.log" --quiet 2>/dev/null || true
fi
SYNC_EOF
chmod +x /usr/local/bin/sync-to-s3.sh

# Run sync every 60 seconds
(while true; do sleep 60; /usr/local/bin/sync-to-s3.sh; done) &

# === Create agent runner script ===
log "Creating agent runner..."
cat > $AGENT_HOME/run_agent.py << 'AGENT_EOF'
#!/usr/bin/env python3
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{{timestamp}}] {{msg}}", flush=True)

WORKSPACE = Path("/home/agent/workspace")
PROJECT_DIR = WORKSPACE / "project"
APP_SPEC = WORKSPACE / "app_spec.txt"
MAX_ITERATIONS = int(os.environ.get("MAX_ITERATIONS", "0"))

def is_first_session():
    feature_list = PROJECT_DIR / "feature_list.json"
    if not feature_list.exists():
        return True
    try:
        data = json.loads(feature_list.read_text())
        return len(data.get("features", [])) == 0
    except:
        return True

def get_pending_features():
    feature_list = PROJECT_DIR / "feature_list.json"
    try:
        data = json.loads(feature_list.read_text())
        return [f for f in data.get("features", []) if f.get("status") == "pending"]
    except:
        return []

def load_progress():
    progress_file = PROJECT_DIR / "claude-progress.txt"
    if progress_file.exists():
        return progress_file.read_text()
    return ""

def get_prompt():
    app_spec = APP_SPEC.read_text() if APP_SPEC.exists() else ""

    if is_first_session():
        return f"""You are setting up a new project. Your task is to:

1. Analyze the following application specification
2. Create a feature_list.json file with a structured breakdown of features
3. Each feature should have: id, description, status (pending)
4. Set up the basic project structure

Application Specification:
{{app_spec}}

Create the feature_list.json file in the current directory with this format:
{{
  "features": [
    {{"id": 1, "description": "Feature description", "status": "pending"}},
    ...
  ]
}}

Work autonomously - do not ask for confirmation."""
    else:
        progress = load_progress()
        pending = get_pending_features()

        if not pending:
            return "All features are complete. Review and make final improvements."

        next_feature = pending[0]
        return f"""You are continuing work on a project.

Application Specification:
{{app_spec}}

Previous Progress:
{{progress if progress else "No previous progress."}}

Task: Implement feature #{{next_feature.get('id')}}
Description: {{next_feature.get('description')}}

After implementing:
1. Update feature_list.json to mark this feature as "completed"
2. Add notes to claude-progress.txt
3. Commit changes with git

Work autonomously - do not ask for confirmation."""

async def run_session():
    from claude_agent_sdk import query
    from claude_agent_sdk.types import ClaudeAgentOptions

    prompt = get_prompt()
    log(f"Running session with prompt: {{prompt[:100]}}...")

    try:
        options = ClaudeAgentOptions(
            cwd=str(PROJECT_DIR),
            permission_mode="bypassPermissions",
        )
        async for message in query(prompt=prompt, options=options):
            log(f"  {{type(message).__name__}}")
        return True
    except Exception as e:
        log(f"Session error: {{e}}")
        return False

async def main():
    log("Agent starting...")
    iteration = 0

    while True:
        iteration += 1
        log(f"=== Iteration {{iteration}} ===")

        if MAX_ITERATIONS > 0 and iteration > MAX_ITERATIONS:
            log(f"Reached max iterations ({{MAX_ITERATIONS}})")
            break

        success = await run_session()

        pending = get_pending_features()
        if not pending and not is_first_session():
            log("All features completed!")
            break

        await asyncio.sleep(2)

    log("Agent finished")

if __name__ == "__main__":
    asyncio.run(main())
AGENT_EOF
chmod +x $AGENT_HOME/run_agent.py
chown agent:agent $AGENT_HOME/run_agent.py

# === Install claude-agent-sdk ===
log "Installing claude-agent-sdk..."
sudo -u agent pip3 install claude-agent-sdk --user

# === Run the agent ===
log "Starting agent..."
cd $PROJECT_DIR
sudo -u agent -E bash -c "export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY; python3 $AGENT_HOME/run_agent.py" >> /var/log/agent.log 2>&1

# === Finalize ===
log "Agent completed"
echo "completed" > /tmp/agent_status
aws s3 cp /tmp/agent_status s3://$BUCKET/agents/$AGENT_ID/status --quiet || true
/usr/local/bin/sync-to-s3.sh

if [ "$NO_SHUTDOWN" != "true" ]; then
    log "Shutting down instance..."
    shutdown -h now
fi
'''
        return script

    def launch(
        self,
        agent_id: str,
        prompt: str,
        credentials: Optional[Credentials],
        **kwargs: Any,
    ) -> DeploymentResult:
        """Launch an agent on AWS EC2.

        Args:
            agent_id: Unique identifier for the agent
            prompt: Task prompt for the agent
            credentials: Authentication credentials
            **kwargs: Additional options (repo, branch, spot, max_iterations, no_shutdown)

        Returns:
            DeploymentResult with launch status
        """
        try:
            # Ensure bucket exists
            self._ensure_bucket()

            # Get AMI for region
            ami_id = self._get_ami()

            # Generate startup script
            startup_script = self._generate_startup_script(
                agent_id, prompt, credentials, **kwargs
            )

            # Build instance parameters
            instance_params = {
                "ImageId": ami_id,
                "InstanceType": self.instance_type,
                "MinCount": 1,
                "MaxCount": 1,
                "UserData": startup_script,
                "TagSpecifications": [{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': agent_id},
                        {'Key': 'agency-quickdeploy', 'Value': 'true'},
                        {'Key': 'agent-id', 'Value': agent_id},
                    ]
                }],
            }

            # Add spot instance configuration if requested
            if kwargs.get('spot'):
                instance_params['InstanceMarketOptions'] = {
                    'MarketType': 'spot',
                    'SpotOptions': {
                        'SpotInstanceType': 'one-time',
                    }
                }

            # Launch instance
            instances = self.ec2.create_instances(**instance_params)

            return DeploymentResult(
                agent_id=agent_id,
                provider="aws",
                status="launching",
            )

        except AWSError:
            raise
        except Exception as e:
            return DeploymentResult(
                agent_id=agent_id,
                provider="aws",
                status="failed",
                error=str(e),
            )

    def _get_instance(self, agent_id: str):
        """Get EC2 instance by agent-id tag.

        Args:
            agent_id: Agent identifier

        Returns:
            EC2 instance or None
        """
        instances = self.ec2.instances.filter(
            Filters=[
                {'Name': 'tag:agent-id', 'Values': [agent_id]},
                {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
            ]
        )
        for instance in instances:
            return instance
        return None

    def status(self, agent_id: str) -> dict:
        """Get agent status from EC2 and S3.

        Args:
            agent_id: Agent identifier

        Returns:
            Status dict with agent info
        """
        result = {
            "agent_id": agent_id,
        }

        # Get EC2 instance status
        instance = self._get_instance(agent_id)
        if instance:
            result["status"] = instance.state['Name']
            result["instance_id"] = instance.id
            result["external_ip"] = instance.public_ip_address
        else:
            result["status"] = "not_found"
            return result

        # Try to get status from S3
        if self.bucket:
            try:
                response = self.s3.get_object(
                    Bucket=self.bucket,
                    Key=f"agents/{agent_id}/status"
                )
                s3_status = response['Body'].read().decode().strip()
                result["agent_status"] = s3_status
            except Exception:
                pass  # S3 status not available yet

            # Try to get feature progress
            try:
                response = self.s3.get_object(
                    Bucket=self.bucket,
                    Key=f"agents/{agent_id}/feature_list.json"
                )
                import json
                data = json.loads(response['Body'].read().decode())
                features = data.get("features", [])
                completed = sum(1 for f in features if f.get("status") == "completed")
                result["features"] = f"{completed}/{len(features)} features completed"
            except Exception:
                pass  # Feature list not available yet

        return result

    def logs(self, agent_id: str) -> Optional[str]:
        """Get agent logs from S3.

        Args:
            agent_id: Agent identifier

        Returns:
            Log content as string, or None if not available
        """
        if not self.bucket:
            return None

        try:
            response = self.s3.get_object(
                Bucket=self.bucket,
                Key=f"agents/{agent_id}/logs/agent.log"
            )
            return response['Body'].read().decode()
        except ClientError:
            return None

    def stop(self, agent_id: str) -> bool:
        """Stop an agent by terminating its EC2 instance.

        Args:
            agent_id: Agent identifier

        Returns:
            True if stopped successfully
        """
        instance = self._get_instance(agent_id)
        if instance:
            instance.terminate()
            return True
        return False

    def list_agents(self) -> list[dict]:
        """List all AWS agents.

        Returns:
            List of agent dicts with name, status, etc.
        """
        try:
            instances = self.ec2.instances.filter(
                Filters=[
                    {'Name': 'tag:agency-quickdeploy', 'Values': ['true']},
                    {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                ]
            )

            agents = []
            for instance in instances:
                # Get agent-id from tags
                agent_id = None
                for tag in instance.tags or []:
                    if tag['Key'] == 'agent-id':
                        agent_id = tag['Value']
                        break

                if agent_id:
                    agents.append({
                        "name": agent_id,
                        "status": instance.state['Name'],
                        "instance_id": instance.id,
                        "external_ip": instance.public_ip_address,
                    })

            return agents
        except Exception:
            return []
