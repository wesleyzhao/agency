# Security Policy

## Security Model

AgentCtl is designed for **single-user, self-hosted** deployments. Understanding the security model is important before deploying.

### Design Principle: Dumb Agents, Smart Master

AgentCtl follows a "dumb agent, smart master" architecture:

- **Master Server**: Privileged, has access to secrets and GCP APIs
- **Agent VMs**: Unprivileged, isolated, treated as potentially compromised

This means agents are sandboxed and have minimal permissions. If an AI agent "goes rogue" or executes malicious code, the blast radius is limited.

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR GCP PROJECT                             │
│                                                                  │
│  ┌──────────────────┐                                           │
│  │   Master Server  │  ← TRUSTED (has secret access)            │
│  │                  │                                           │
│  │  - GCE API       │                                           │
│  │  - Secret Manager│                                           │
│  │  - GCS Admin     │                                           │
│  └────────┬─────────┘                                           │
│           │ Injects secrets via metadata                        │
│           ▼                                                      │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │   Agent VM   │     │   Agent VM   │  ← UNTRUSTED             │
│  │  (isolated)  │     │  (isolated)  │                          │
│  │              │     │              │                          │
│  │  - No secret │     │  - No secret │                          │
│  │    IAM access│     │    IAM access│                          │
│  │  - No VPC    │     │  - No VPC    │                          │
│  │    access    │     │    access    │                          │
│  │  - Internet  │     │  - Internet  │                          │
│  │    only      │     │    only      │                          │
│  └──────────────┘     └──────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Secret Management (Injection Model)

**We use secret injection, NOT agent pull.**

Why? If agents could pull secrets directly from Secret Manager:
- They'd need `roles/secretmanager.secretAccessor` IAM permission
- A compromised agent could read ANY secret it has access to
- Increases blast radius of a security incident

Instead:
1. Master Server fetches secrets from Secret Manager
2. Master injects secrets into VM via **instance metadata** (not startup script)
3. Agent reads secrets from metadata service (no IAM needed)
4. Secrets never appear in plain text in GCP Console

```bash
# How agent gets secrets (inside VM):
ANTHROPIC_KEY=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/anthropic-api-key" \
    -H "Metadata-Flavor: Google")
```

### Network Isolation (Default: Sandboxed)

**Agents are network-sandboxed by default.**

Why? An autonomous AI agent running arbitrary code could:
- Scan your internal networks
- SSH into other servers
- Access internal admin panels
- Exfiltrate data to internal services

Default network rules for agent VMs:
- ✅ **Internet egress allowed** (needed for APIs, package managers, git)
- ❌ **Internal VPC traffic blocked** (can't reach other GCP resources)
- ❌ **No VPC peering** (can't reach other networks)

```bash
# Firewall rule created during init:
gcloud compute firewall-rules create agentctl-agent-deny-internal \
    --direction=EGRESS \
    --priority=1000 \
    --network=default \
    --action=DENY \
    --rules=all \
    --destination-ranges=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16 \
    --target-tags=agentctl-agent
```

**To allow internal network access** (use with caution):
```bash
agentctl run --allow-internal-network "My trusted task"
```

### What's Protected

| Asset | Protection |
|-------|------------|
| Anthropic API Key | Injected via metadata, agent has no IAM access |
| GitHub Token | Injected via metadata, agent has no IAM access |
| GCP Project | Agents can't access other GCP resources |
| Internal Network | Blocked by default firewall rules |
| Other VMs | Network isolated, no SSH access |

### What's NOT Protected (MVP)

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Master server auth** | Anyone with server IP can control agents | Use VPN, firewall, or private network |
| **Internet access** | Agents can reach the internet | Required for AI to work; review commits |
| **Multi-tenancy** | No user isolation | Single-user only in MVP |
| **Prompt injection** | Malicious prompts could attempt harmful actions | Review prompts; use timeouts; network sandbox limits damage |

### Agent VM Permissions (Minimal)

```yaml
agentctl-agent service account:
  - roles/logging.logWriter      # Write logs only
  - roles/storage.objectCreator  # Upload to GCS only (can't read/delete)
  # NOTE: No secretmanager access! Secrets injected by master.
```

Compare to master server:
```yaml
agentctl-master service account:
  - roles/compute.admin                # Manage VMs
  - roles/secretmanager.secretAccessor # Read secrets (to inject)
  - roles/storage.admin                # Full GCS access
  - roles/logging.viewer               # Read logs
```

## Security Best Practices

### 1. Network Security

**Default: Agents are sandboxed** (recommended)

Agents can reach the internet but not your internal network. This is the safest configuration.

**If you need internal access** (use sparingly):
```bash
# Per-agent override
agentctl run --allow-internal-network "Task that needs internal access"

# Or globally (not recommended)
# Edit config: ~/.agentctl/config.yaml
# allow_internal_network: true
```

**Master Server Access:**
```bash
# Restrict master server to your IP only
gcloud compute firewall-rules create agentctl-master-restricted \
    --allow=tcp:8000 \
    --source-ranges=YOUR_IP/32 \
    --target-tags=agentctl-master
```

### 2. Secret Management

Secrets are automatically injected via instance metadata. You don't need to do anything special.

**Do:**
- Use `agentctl secrets set` to store secrets (automatic with `agentctl init`)
- Rotate API keys periodically
- Use separate API keys for AgentCtl vs. production

**Don't:**
- Give agent VMs IAM access to Secret Manager (we don't by default)
- Store secrets in config files
- Commit secrets to git

### 3. Review Agent Output

Agents push to git branches. Before merging:
- Review the commits
- Check for suspicious changes (credential harvesting, network scanning code)
- Test the code

The network sandbox limits what a malicious agent can do, but code review is still important.

## Reporting Security Issues

**Do NOT open public GitHub issues for security vulnerabilities.**

Instead, email the maintainers directly at: [security@your-domain.com]

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you on a fix.

## Security Roadmap

Planned security improvements for future versions:

### v1.1
- [ ] API key authentication for master server
- [ ] Rate limiting on API endpoints
- [ ] Audit logging

### v1.2
- [ ] mTLS between CLI and master server
- [ ] Signed agent attestation
- [ ] VPC-native deployment option

### v2.0
- [ ] Multi-user support with RBAC
- [ ] Agent sandboxing (gVisor/Firecracker)
- [ ] Secrets per-agent instead of shared

## Compliance Notes

AgentCtl is **not** designed for:
- HIPAA workloads
- PCI-DSS environments
- FedRAMP systems

For regulated environments, additional controls would be needed.

## Acknowledgments

We appreciate security researchers who responsibly disclose vulnerabilities.

Security contributors:
- (Your name could be here!)
