# Agency QuickDeploy Backlog

## Known Issues & Workarounds

### 1. First-File Creation Bug (WORKAROUND IN PLACE)
**Issue**: `claude-agent-sdk` with `permission_mode='bypassPermissions'` cannot create the FIRST file in a session. Subsequent file creations work fine.

**Symptoms**: Agent outputs "Now let me create feature_list.json..." but no file appears. Loops indefinitely on first session.

**Workaround**: Startup script seeds an empty `feature_list.json` so agent only needs to populate it, not create it.

**Status**: Workaround deployed. Root cause unknown.
- Tested: 2026-01-04 with OAuth auth
- Local testing with same SDK version works fine
- May be OAuth-specific, timing issue, or SDK initialization bug

**TODO**: File issue with Anthropic if this persists across SDK updates.

---

## Recently Completed (2026-01-07)

### Multi-Provider Support ✅
Added support for deploying agents to multiple platforms:

**Providers:**
- **GCP** (existing) - Compute Engine VMs with GCS storage
- **AWS** (new) - EC2 instances with S3 storage
- **Docker** (new) - Local containers for free 24/7 agents
- **Railway** (merged from feature branch) - Fast container deployments

**Usage:**
```bash
agency-quickdeploy launch "task" --provider [gcp|aws|docker|railway]
```

**Known Limitations:**

1. **AWS Provider:**
   - **Security:** Claude credentials are passed via EC2 user-data (visible in AWS console and metadata service). Credentials are NOT logged but are present in the startup script. For higher security, use short-lived credentials or rotate after use.
   - No IAM instance profile configured by default - S3 access requires default VPC or manual IAM setup
   - No SSH key pair specified - use AWS Console to configure SSH access
   - No security group created - uses default (may not allow SSH inbound)
   - Spot instances work but interruption handling not implemented

2. **Docker Provider:**
   - Requires Docker daemon running locally
   - No built-in log file persistence (uses Docker stdout)
   - Container restart policy is "unless-stopped" - may restart unexpectedly
   - Credentials are passed via container environment variables

3. **GCP Provider:**
   - Credentials passed via VM instance metadata (similar to AWS user-data)
   - Supports GCP Secret Manager for more secure credential storage

4. **General:**
   - Agent-runner image (`ghcr.io/wesleyzhao/agency-agent:latest`) must be published before Docker/Railway work
   - AMI IDs for AWS may become outdated over time

**Credential Security Best Practices:**

| Provider | How Credentials Are Passed | Security Level |
|----------|---------------------------|----------------|
| Docker | Container environment variables | Medium - visible to `docker inspect` |
| GCP | Instance metadata or Secret Manager | Medium/High |
| AWS | EC2 user-data | Medium - visible in AWS console |
| Railway | Railway environment variables | Medium - encrypted at rest |

For production use:
- Use short-lived API keys and rotate after agent completes
- For GCP, use Secret Manager (`--auth-type oauth` with secret in Secret Manager)
- Consider using IAM roles where possible instead of static credentials

---

## Recently Completed (2026-01-04)

### OAuth Token Support ✅
- Use Claude subscription instead of API key billing
- `--auth-type oauth` flag or `QUICKDEPLOY_AUTH_TYPE=oauth` env var
- Token from `claude setup-token` stored in Secret Manager or env var

### --no-shutdown Flag ✅
- Keep VM running after agent completes for inspection
- SSH in to see what was built
- Manually stop with `agency-quickdeploy stop <agent-id>`

### .env File Support ✅
- Load config from `.env` file (no external dependency)
- Supports `QUICKDEPLOY_PROJECT`, `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`

### bypassPermissions Mode ✅
- Agent SDK now uses `permission_mode='bypassPermissions'`
- Auto-accepts all file operations (required for headless operation)

---

## High Priority Backlog

### 1. --timeout Flag
Stop Claude after X time, keep VM alive for inspection.
- Use case: Budget control, prevent runaway agents
- Implementation: Pass timeout to run_agent.py, kill claude process after N seconds

### 2. Better SSH UX
Wrapper command for easier SSH access:
```bash
agency-quickdeploy ssh <agent-id>
# instead of
gcloud compute ssh <agent-id> --zone=us-central1-a --project=my-project
```

### 3. Real-time Log Streaming
Stream agent logs in real-time instead of polling GCS:
- WebSocket or SSE from agent to client
- Or use Cloud Logging with real-time tailing

### 4. Pre-Baked VM Images (Packer)
Create base images with dependencies pre-installed:
- Node.js 18, Claude Code CLI, Python 3.11, gcloud SDK
- Reduces startup time from 3 mins to ~30 secs
- Use Packer to build, store in GCE images

---

## Architecture Improvements (Future)

### Container-Based Multi-Agent Architecture
Run multiple agents as Docker containers on a single larger VM:
- More cost-effective than 1 VM per agent
- Faster startup (containers vs VMs)
- Better resource utilization
- Requires careful isolation

### Cloud Run for Orchestrator
Deploy a lightweight orchestrator to Cloud Run:
- Serverless, auto-scaling
- Trigger agent launches via HTTP
- Cost-effective for variable workloads

### GitHub Integration
- Auto-create PRs from agent work
- GitHub Actions for triggering agents
- Branch-per-agent workflow

---

## Testing Improvements

### Docker-Based Local Testing
Test startup scripts locally before deploying to GCP:
```bash
docker run -it ubuntu:22.04 bash -c "$(cat startup_script.sh)"
```
- Catches 90% of errors without touching GCP
- Instant feedback vs 5-10 min cycles

### Integration Test Suite
Automated tests that:
1. Launch agent on GCP
2. Wait for completion
3. Verify expected files created
4. Check feature_list.json updated
5. Clean up VM

---

## Documentation TODO

- [x] Add troubleshooting guide - see README.md and CLAUDE.md
- [x] Document OAuth token flow - see CLAUDE.md "Authentication Deep Dive"
- [ ] Add architecture diagram
- [ ] Record demo video
- [x] Write "Getting Started in 5 Minutes" guide - see README.md "Choose Your Path"

**Documentation Structure (2026-01-19):**
- `README.md` - User-friendly getting started guide
- `CLAUDE.md` - Comprehensive technical reference for developers & AI agents
- `BACKLOG.md` - Known issues and roadmap (this file)
- `docs/` - Detailed reference documentation (API, CLI, deployment, architecture)

---

## Resolved Issues (2026-01-04)

1. ~~**VM terminates too quickly**~~ - FIXED: Added --no-shutdown flag, logs upload before shutdown
2. ~~**Serial port output not ready**~~ - FIXED: Logs sync to GCS, can download anytime
3. ~~**Claude Code execution unknown**~~ - FIXED: Full output synced to GCS workspace
4. ~~**GCS bucket permissions**~~ - FIXED: Auto-grant compute service account in `agentctl init`
5. ~~**VM OAuth scopes**~~ - FIXED: Always use cloud-platform scope for write access
6. ~~**Workspace not synced**~~ - FIXED: gsutil rsync syncs entire workspace + detects agent-created projects

---

## Notes for Contributors

See [CLAUDE.md](CLAUDE.md) for comprehensive developer documentation including:
- Project architecture and key files
- Complete CLI reference
- Environment variables
- Testing instructions
- Troubleshooting guide

### Quick Test Commands
```bash
# Run all tests
python -m pytest

# Test a launch (Docker - no cloud costs)
ANTHROPIC_API_KEY=sk-ant-... agency-quickdeploy launch "Build hello world" --provider docker --no-shutdown
agency-quickdeploy status <agent-id> --provider docker
agency-quickdeploy stop <agent-id> --provider docker
```

---

## Notes from 2026-01-04 Testing Session

### What We Fixed
- Workspace sync to GCS using `gsutil -m rsync`
- --no-shutdown flag for VM inspection after completion
- --wait flag for automatic download when agent completes
- Detects agent-created projects in /tmp and agent home
- Fixed download step to create output directory
- Validated full end-to-end: prompt → agent builds → download → tests pass
