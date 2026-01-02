# AgentCtl - Deployment Guide

## Overview

This guide covers deploying AgentCtl from scratch on a fresh GCP project.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK** installed locally
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Linux
   curl https://sdk.cloud.google.com | bash
   
   # Verify
   gcloud --version
   ```

3. **Python 3.11+**
   ```bash
   python3 --version  # Should be 3.11 or higher
   ```

4. **API Keys Ready**
   - Anthropic API key (for Claude Code): https://console.anthropic.com/
   - OpenAI API key (for Codex, optional): https://platform.openai.com/
   - GitHub personal access token (optional, for private repos): https://github.com/settings/tokens

## Step-by-Step Deployment

### Step 1: GCP Authentication

```bash
# Login to GCP
gcloud auth login

# Set up application default credentials
gcloud auth application-default login
```

### Step 2: Create or Select a GCP Project

```bash
# Option A: Create a new project
gcloud projects create my-agentctl-project --name="AgentCtl"
gcloud config set project my-agentctl-project

# Option B: Use existing project
gcloud config set project existing-project-id

# Enable billing (required for compute resources)
# Do this in the GCP Console: https://console.cloud.google.com/billing
```

### Step 3: Install AgentCtl

```bash
# From PyPI (when published)
pip install agentctl

# Or from source
git clone https://github.com/yourusername/agentctl
cd agentctl
pip install -e .
```

### Step 4: Initialize AgentCtl

```bash
agentctl init
```

This interactive command will:

1. **Enable required GCP APIs:**
   - Compute Engine API
   - Secret Manager API
   - Cloud Storage API
   - Cloud Logging API

2. **Create GCS bucket** for artifacts

3. **Create service accounts:**
   - `agentctl-master` - for the master server
   - `agentctl-agent` - for agent VMs

4. **Configure IAM roles**

5. **Prompt for API keys** and store them in Secret Manager

6. **Deploy the master server**

7. **Save configuration** to `~/.agentctl/config.yaml`

### Step 5: Verify Installation

```bash
# Check server status
agentctl server status

# List agents (should be empty)
agentctl list

# Run a test agent
agentctl run --timeout 5m "Create a hello world Python script"

# Watch it work
agentctl logs test-agent --follow
```

---

## Manual Setup (Alternative)

If you prefer to set things up manually or need to customize:

### Enable APIs

```bash
PROJECT_ID=$(gcloud config get-value project)

gcloud services enable compute.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    logging.googleapis.com \
    --project=$PROJECT_ID
```

### Create GCS Bucket

```bash
BUCKET_NAME="agentctl-${PROJECT_ID}-$(openssl rand -hex 4)"

gsutil mb -l us-central1 gs://$BUCKET_NAME

echo "Created bucket: $BUCKET_NAME"
```

### Create Service Accounts

```bash
# Master server account
gcloud iam service-accounts create agentctl-master \
    --display-name="AgentCtl Master Server"

# Agent VM account
gcloud iam service-accounts create agentctl-agent \
    --display-name="AgentCtl Agent VMs"
```

### Configure IAM

```bash
PROJECT_ID=$(gcloud config get-value project)

# Master server permissions
for ROLE in roles/compute.admin roles/secretmanager.secretAccessor roles/storage.admin roles/logging.viewer; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:agentctl-master@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="$ROLE"
done

# Agent VM permissions
for ROLE in roles/secretmanager.secretAccessor roles/storage.objectAdmin roles/logging.logWriter; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:agentctl-agent@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="$ROLE"
done
```

### Store Secrets

```bash
# Anthropic API key
echo -n "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-

# GitHub token (optional)
echo -n "your-github-token" | gcloud secrets create github-token --data-file=-

# OpenAI API key (optional, for Codex)
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
```

### Deploy Master Server

```bash
# Create the master server VM
gcloud compute instances create agentctl-master \
    --zone=us-central1-a \
    --machine-type=e2-small \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --service-account=agentctl-master@${PROJECT_ID}.iam.gserviceaccount.com \
    --scopes=cloud-platform \
    --tags=http-server,https-server \
    --metadata-from-file=startup-script=scripts/master-startup.sh

# Allow HTTP traffic
gcloud compute firewall-rules create allow-agentctl \
    --allow=tcp:8080 \
    --target-tags=http-server \
    --description="Allow AgentCtl API access"

# Get external IP
MASTER_IP=$(gcloud compute instances describe agentctl-master \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "Master server IP: $MASTER_IP"

# Store master URL as secret (for agents to find)
echo -n "http://${MASTER_IP}:8080" | gcloud secrets create master-server-url --data-file=-
```

### Create Local Config

```bash
mkdir -p ~/.agentctl

cat > ~/.agentctl/config.yaml << EOF
gcp_project: ${PROJECT_ID}
gcp_region: us-central1
gcp_zone: us-central1-a
master_server_url: http://${MASTER_IP}:8080
gcs_bucket: ${BUCKET_NAME}
default_machine_type: e2-medium
default_timeout: 4h
default_engine: claude
screenshot_interval: 300
screenshot_retention: 24h
EOF
```

---

## Cost Optimization

### Use Spot Instances

Spot instances are 60-90% cheaper. Use by default:

```bash
agentctl run --spot "Your task here"
```

### Set Up Budget Alerts

```bash
# Create a budget (via gcloud or console)
# This requires the billing account ID

gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT_ID \
    --display-name="AgentCtl Budget" \
    --budget-amount=50 \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100
```

### Auto-Shutdown

Always use timeouts:

```bash
# Short tasks
agentctl run --timeout 30m "Quick task"

# Longer tasks
agentctl run --timeout 4h "Bigger task"
```

### Clean Up Old Resources

```bash
# Delete stopped agents older than 7 days
agentctl list --status stopped | xargs -I {} agentctl delete {} --force

# Or manually clean GCS
gsutil -m rm -r gs://${BUCKET_NAME}/old-agent-*
```

---

## Troubleshooting

### Master Server Not Starting

```bash
# Check VM status
gcloud compute instances describe agentctl-master --zone=us-central1-a

# SSH and check logs
gcloud compute ssh agentctl-master --zone=us-central1-a
sudo journalctl -u agentctl-master -f
```

### Agent VMs Not Starting

```bash
# Check recent operations
gcloud compute operations list --filter="targetLink:agent-" --limit=10

# Check specific agent VM
gcloud compute instances describe agent-my-agent --zone=us-central1-a

# SSH and check startup logs
gcloud compute ssh agent-my-agent --zone=us-central1-a
sudo cat /var/log/syslog | grep startup-script
```

### Permission Errors

```bash
# Verify service account roles
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:agentctl-" \
    --format="table(bindings.role, bindings.members)"
```

### Secret Access Issues

```bash
# List secrets
gcloud secrets list

# Test access
gcloud secrets versions access latest --secret=anthropic-api-key
```

---

## Updating AgentCtl

### Update CLI

```bash
pip install --upgrade agentctl
```

### Update Master Server

```bash
agentctl server deploy
```

This will:
1. Pull latest code
2. Restart the server process
3. Maintain existing database

---

## Uninstalling

### Remove All Resources

```bash
# Stop all agents
agentctl stop --all --force

# Delete all agents
agentctl list | xargs -I {} agentctl delete {} --force

# Delete master server
gcloud compute instances delete agentctl-master --zone=us-central1-a

# Delete bucket
gsutil -m rm -r gs://${BUCKET_NAME}

# Delete secrets
gcloud secrets delete anthropic-api-key
gcloud secrets delete github-token
gcloud secrets delete openai-api-key
gcloud secrets delete master-server-url

# Delete service accounts
gcloud iam service-accounts delete agentctl-master@${PROJECT_ID}.iam.gserviceaccount.com
gcloud iam service-accounts delete agentctl-agent@${PROJECT_ID}.iam.gserviceaccount.com

# Delete firewall rule
gcloud compute firewall-rules delete allow-agentctl

# Remove local config
rm -rf ~/.agentctl
```

---

## Security Considerations

### API Access

The master server is exposed on a public IP without authentication in MVP. For production:

1. Use a VPN or Cloud IAP
2. Add API key authentication
3. Use HTTPS with a proper certificate

### Secret Rotation

Rotate API keys periodically:

```bash
# Update a secret
echo -n "new-api-key" | gcloud secrets versions add anthropic-api-key --data-file=-

# Restart agents to pick up new keys
agentctl stop --all
# Re-run your agents
```

### Network Security

Consider restricting agent network access if they don't need full internet:

```bash
# Create a more restrictive firewall (example)
gcloud compute firewall-rules create agent-egress-restricted \
    --direction=EGRESS \
    --action=ALLOW \
    --rules=tcp:443 \
    --destination-ranges=0.0.0.0/0 \
    --target-tags=agent-vm
```
