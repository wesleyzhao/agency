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

- [ ] Add troubleshooting guide (common errors, SSH debugging)
- [ ] Document OAuth token refresh flow
- [ ] Add architecture diagram
- [ ] Record demo video
- [ ] Write "Getting Started in 5 Minutes" guide

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

### Running Tests
```bash
python -m pytest agency_quickdeploy/ shared/ -v
```

### Testing a Launch
```bash
# Set up .env with your credentials
echo 'QUICKDEPLOY_PROJECT=your-project' >> .env
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env  # or CLAUDE_CODE_OAUTH_TOKEN

# Launch test agent
python -m agency_quickdeploy launch "Build a hello world Python CLI" --no-shutdown --name test-agent

# Monitor
python -m agency_quickdeploy status test-agent
python -m agency_quickdeploy logs test-agent

# SSH in to inspect
gcloud compute ssh test-agent --zone=us-central1-a --project=your-project

# Clean up
python -m agency_quickdeploy stop test-agent
```

### Key Files
- `shared/harness/startup_template.py` - VM startup script template
- `agency_quickdeploy/launcher.py` - Main orchestration logic
- `agency_quickdeploy/auth.py` - API key and OAuth handling
- `agency_quickdeploy/cli.py` - CLI commands

---

## Notes from 2026-01-04 Testing Session

### What We Fixed
- Workspace sync to GCS using `gsutil -m rsync`
- --no-shutdown flag for VM inspection after completion
- --wait flag for automatic download when agent completes
- Detects agent-created projects in /tmp and agent home
- Fixed download step to create output directory
- Validated full end-to-end: prompt → agent builds → download → tests pass
