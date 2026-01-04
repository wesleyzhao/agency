# AgentCtl Backlog

## Architecture Improvements (Future)

### 1. Container-Based Multi-Agent Architecture
Instead of 1 VM per agent (expensive, slow), run multiple agents as Docker containers on a single larger VM.
- More cost-effective
- Faster startup (containers vs VMs)
- Better resource utilization
- Requires careful isolation with `--dangerously-skip-permissions`

### 2. Pre-Baked VM Images (Packer)
Create base images with Node.js 18, Claude Code, and dependencies pre-installed.
- Reduces startup time from 3 mins to ~30 secs
- Fewer moving parts = fewer failures
- Use Packer to build, Terraform to deploy

### 3. Cloud Run for Master Server
Deploy master server to Cloud Run instead of local/GCE.
- Serverless, auto-scaling
- No VM management
- Cost-effective for variable workloads

### 4. Anthropic Agent SDK Integration
Integrate with Anthropic's Claude Agent SDK for:
- Long-running agent patterns
- Checkpointing and resumable tasks
- Better error handling

### 5. One-Click Deployment
Make launching continuous agents extremely easy:
- `npx agentctl@latest run "prompt"`
- Web UI with deploy button
- GitHub Action integration

### 6. Multiple Agents per Instance
Option to run agents in Docker containers within same instance:
- Cheaper than separate VMs
- Shared compute resources
- Kubernetes or Docker Compose orchestration

---

## Testing Improvements

### Docker-Based Local Testing (HIGH PRIORITY)
Test startup scripts locally in Docker before deploying to GCP:
```bash
docker run -it ubuntu:22.04 bash -c "$(cat startup_script.sh)"
```
Benefits:
- Catches 90% of errors without touching GCP
- Instant feedback vs 5-10 min cycles
- Free vs $0.01-0.02 per VM

### Persistent Debug VM
Keep a "debug mode" VM running without auto-shutdown for SSH debugging.

### Better Log Capture
- Stream logs in real-time during startup
- Don't shutdown until logs are persisted to GCS
- Add explicit checkpoints in startup script

---

## Current Issues to Fix

_None - all major issues resolved as of 2026-01-04_

---

## Resolved Issues (2026-01-04)

1. ~~**VM terminates too quickly**~~ - FIXED: Added --no-shutdown flag, logs upload before shutdown
2. ~~**Serial port output not ready**~~ - FIXED: Logs sync to GCS, can download anytime
3. ~~**Claude Code execution unknown**~~ - FIXED: Full output synced to GCS workspace
4. ~~**GCS bucket permissions**~~ - FIXED: Auto-grant compute service account in `agentctl init`
5. ~~**VM OAuth scopes**~~ - FIXED: Always use cloud-platform scope for write access
6. ~~**Workspace not synced**~~ - FIXED: gsutil rsync syncs entire workspace + detects agent-created projects

---

## Notes from 2026-01-02 Testing Session

### What We Fixed
- Installed gcloud SDK properly in ~/google-cloud-sdk
- Created non-root 'agent' user (Claude Code security requirement)
- Installed Node.js 18 from NodeSource (required for Claude Code)
- Injected Anthropic API key via VM metadata from Secret Manager
- Added helper script for prompt handling to avoid quoting issues

---

## Notes from 2026-01-04 Testing Session

### What We Fixed
- Workspace sync to GCS using `gsutil -m rsync`
- --no-shutdown flag for VM inspection after completion
- --wait flag for automatic download when agent completes
- Detects agent-created projects in /tmp and agent home
- Fixed download step to create output directory
- Validated full end-to-end: prompt → agent builds → download → tests pass
