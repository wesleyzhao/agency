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

1. **VM terminates too quickly** - Need to capture logs before shutdown
2. **Serial port output not ready** - VM shuts down before we can read logs
3. **Claude Code execution unknown** - Can't tell if it ran successfully

---

## Notes from 2026-01-02 Testing Session

### What We Fixed
- Installed gcloud SDK properly in ~/google-cloud-sdk
- Created non-root 'agent' user (Claude Code security requirement)
- Installed Node.js 18 from NodeSource (required for Claude Code)
- Injected Anthropic API key via VM metadata from Secret Manager
- Added helper script for prompt handling to avoid quoting issues

### What Still Needs Work
- VM terminates quickly, can't capture full logs
- Need to verify Claude Code actually runs the task
- Testing cycle is too slow (5-10 mins per iteration)
