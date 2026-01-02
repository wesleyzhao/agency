# Plan: Get GCP Agents Working

## Goal
Get a successful end-to-end agent run: create VM → run Claude Code → create file → verify output

## Phase 1: Add Docker-Based Testing (30 mins)
**Why:** Current testing is 5-10 mins per cycle. Docker testing is instant and free.

### Tasks
1. Create `scripts/test_startup_local.sh` that:
   - Generates the startup script with mock values
   - Runs it in a Docker container (ubuntu:22.04)
   - Captures all output for debugging

2. Test the startup script locally to identify issues before GCP

```bash
# Example usage
./scripts/test_startup_local.sh
```

### Success Criteria
- Can run startup script locally in Docker
- See all output/errors immediately
- Fix issues without launching GCP VMs

---

## Phase 2: Fix VM Termination Issue (1 hour)
**Why:** VMs terminate too quickly, can't capture logs or verify Claude ran.

### Hypothesis
The VM probably runs successfully but shuts down before we can see results. Need to:
1. Add delay before shutdown to capture logs
2. Or disable auto-shutdown for debugging
3. Upload logs to GCS before shutdown

### Tasks
1. Modify startup script to:
   - Upload agent.log to GCS before shutdown
   - Add 60-second delay before shutdown (debug mode)
   - Log explicit status checkpoints

2. Add `--debug` flag to `agentctl run` that keeps VM running

3. Verify Claude Code actually executed by checking:
   - /workspace/agent.log contents
   - Exit code from claude command
   - Whether hello.txt was created

### Success Criteria
- Can see full Claude Code output in logs
- Know definitively if task succeeded or failed

---

## Phase 3: Complete Full Lifecycle Test (30 mins)
**Why:** Verify all commands work end-to-end.

### Tasks
1. Run successful agent: `agentctl run "Create hello.txt"`
2. Monitor: `agentctl status`, `agentctl logs`
3. Verify task completed successfully
4. Clean up: `agentctl stop`, `agentctl delete`

### Success Criteria
- Full lifecycle works: run → monitor → stop → delete
- Can see output/results from Claude Code

---

## Phase 4: Commit & Document (15 mins)
1. Commit all fixes
2. Update PROGRESS.md
3. Update README with working instructions

---

## Deferred (see BACKLOG.md)
- Container-based multi-agent architecture
- Pre-baked VM images
- Cloud Run deployment
- Agent SDK integration

---

## Quick Reference

### Test locally first
```bash
./scripts/test_startup_local.sh
```

### Create agent
```bash
agentctl run --name test1 "Create hello.txt with Hello World"
```

### Debug agent
```bash
agentctl logs test1
agentctl status test1
agentctl ssh test1  # if VM still running
```

### Check GCS for logs
```bash
gsutil cat gs://agentctl-agentctl-test-*/agents/test1/agent.log
```
