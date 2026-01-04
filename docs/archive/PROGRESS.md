# AgentCtl - Progress Tracker

## Instructions

Update this file after completing each task:
- Change ⬜ to ✅ when complete
- Add completion date
- Note any issues or deviations

---

## Phase 0: Setup

| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 0.1 | Repository creation | ✅ | 2026-01-01 | Created agentctl package structure, tests dirs, .gitignore |
| 0.2 | Package configuration | ✅ | 2026-01-01 | Created pyproject.toml, requirements.txt, requirements-dev.txt |

---

## Phase 1: Core CLI (Local)

| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 1.0 | Provider interface | ✅ | 2026-01-01 | CloudProvider base, LocalProvider, GCPProvider placeholder |
| 1.1 | Define core data models | ✅ | 2026-01-01 | AgentStatus, AgentConfig, Agent models |
| 1.2 | Configuration module | ✅ | 2026-01-01 | Config class, YAML loading, env var overrides |
| 1.3 | CLI framework setup | ✅ | 2026-01-01 | Click-based CLI with help and version |
| 1.4 | API client module | ✅ | 2026-01-01 | APIClient class with httpx |
| 1.5 | Run command | ✅ | 2026-01-01 | CLI run command with all options |
| 1.6 | List command | ✅ | 2026-01-01 | list, status, stop, delete commands |
| 1.7 | Tell command | ✅ | 2026-01-01 | Send instructions to running agent |

**Phase 1 Checkpoint:** ✅ All 27 unit tests pass

---

## Phase 2: Local Server

| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 2.1 | Server skeleton | ✅ | 2026-01-01 | FastAPI app with health endpoint |
| 2.2 | Agent repository | ✅ | 2026-01-01 | SQLite CRUD operations |
| 2.3 | Agent routes | ✅ | 2026-01-01 | REST API endpoints for agents |

**Phase 2 Checkpoint:** ✅ All 36 unit tests + 5 integration tests pass

---

## Phase 3: GCP Integration

| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 3.1 | GCP client utilities | ✅ | 2026-01-01 | gcloud wrappers for auth, project, APIs |
| 3.2 | Secret Manager service | ✅ | 2026-01-01 | Secrets CRUD operations |
| 3.3 | Storage Manager service | ✅ | 2026-01-01 | GCS bucket operations |
| 3.4 | VM Manager service | ✅ | 2026-01-01 | GCE instance lifecycle |
| 3.5 | Init command | ✅ | 2026-01-01 | GCP project setup wizard |
| 3.6 | Wire up VM creation | ✅ | 2026-01-01 | VM lifecycle in agent routes |
| 3.7 | SSH command | ✅ | 2026-01-01 | gcloud compute ssh wrapper |
| 3.8 | Logs command | ✅ | 2026-01-01 | Serial console + SSH tail |

**Phase 3 Checkpoint:** ✅ All 45 tests pass, all GCP services implemented

---

## Phase 4: Agent VM & Runner

| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 4.1 | Improved startup script | ✅ | 2026-01-01 | Auto-commit, screenshots, metadata secrets |
| 4.2 | Internal heartbeat endpoint | ✅ | 2026-01-01 | /v1/internal/heartbeat for agent status |
| 4.3 | Screenshots CLI command | ✅ | 2026-01-01 | List and download agent screenshots |
| 4.4 | Stop command - Delete VM | ✅ | 2026-01-01 | Already done in Task 3.6 |

**Phase 4 Checkpoint:** ✅ All 45 tests pass, agent lifecycle complete

---

## Phase 5: GCP Agent Deployment Fixes (2026-01-04)

| Task | Description | Status | Date | Notes |
|------|-------------|--------|------|-------|
| 5.1 | Fix GCS bucket permissions | ✅ | 2026-01-04 | Auto-grant compute SA in init |
| 5.2 | Fix VM OAuth scopes | ✅ | 2026-01-04 | Always use cloud-platform scope |
| 5.3 | Add workspace sync to GCS | ✅ | 2026-01-04 | gsutil rsync for full workspace |
| 5.4 | Add --no-shutdown flag | ✅ | 2026-01-04 | Keep VM for SSH inspection |
| 5.5 | Add --wait flag | ✅ | 2026-01-04 | Auto-download when complete |
| 5.6 | Detect agent-created projects | ✅ | 2026-01-04 | Scan /tmp and home for .git |
| 5.7 | Validate end-to-end | ✅ | 2026-01-04 | Calculator app: 18 tests pass |

**Phase 5 Checkpoint:** ✅ Full end-to-end workflow validated

---

## Final Verification

| Check | Status |
|-------|--------|
| All unit tests pass | ✅ |
| All integration tests pass | ✅ |
| End-to-end workflow works | ✅ |
| GCP agent deployment works | ✅ |
| Workspace sync to GCS works | ✅ |
| Output download works | ✅ |
| Documentation complete | ✅ |
| Clean git history | ✅ |

---

## Issues Log

| Date | Issue | Resolution |
|------|-------|------------|
| 2026-01-04 | VMs couldn't write to GCS | Auto-grant compute SA bucket access in init |
| 2026-01-04 | Workspace not syncing | Use gsutil rsync, scan multiple locations |
| 2026-01-04 | Download failing | Create output dir, use rsync not cp |

---

## Notes

### 2026-01-04 - MVP Complete
Successfully deployed agent to GCP, built a Python calculator with 18 tests, synced to GCS, downloaded locally, verified all tests pass. Full MVP workflow validated.
