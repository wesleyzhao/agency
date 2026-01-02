# AgentCtl - Architecture Review

**Reviewer:** Staff Engineer (Cloud Platforms)  
**Date:** December 2024  
**Status:** APPROVED with recommendations

---

## Executive Summary

The AgentCtl design is **fundamentally sound** for an open-source MVP. The architecture follows cloud-native patterns, maintains good separation of concerns, and is appropriately scoped. 

However, I've identified several issues that should be addressed before implementation to ensure the project is maintainable, extensible, and contributor-friendly.

---

## Critical Issues (Must Fix)

### 1. ❌ Cloud Provider Lock-in in Core Abstractions

**Problem:** The current design has GCP-specific code directly in the server routes and CLI commands. This makes it impossible to support other clouds (AWS, Azure) or local development without significant refactoring.

**Fix:** Introduce a **Provider Interface** that abstracts cloud operations.

```python
# agentctl/providers/base.py
from abc import ABC, abstractmethod

class CloudProvider(ABC):
    """Abstract interface for cloud operations."""
    
    @abstractmethod
    def create_vm(self, name: str, config: VMConfig) -> VMInstance: ...
    
    @abstractmethod
    def delete_vm(self, name: str) -> bool: ...
    
    @abstractmethod
    def get_secret(self, name: str) -> str: ...
    
    @abstractmethod
    def set_secret(self, name: str, value: str) -> None: ...
    
    @abstractmethod
    def upload_file(self, local: Path, remote: str) -> str: ...


# agentctl/providers/gcp.py
class GCPProvider(CloudProvider):
    """Google Cloud Platform implementation."""
    ...

# agentctl/providers/local.py  
class LocalProvider(CloudProvider):
    """Local Docker-based implementation for development."""
    ...
```

**Impact:** This enables:
- Local development without GCP account
- Future AWS/Azure support
- Easier testing with mock providers

### 2. ❌ Master Server is a Single Point of Failure

**Problem:** If the master server goes down:
- Can't create new agents
- Can't stop running agents (VMs keep running and billing)
- Can't get agent status

**Fix:** Design for resilience:

1. **Agent self-termination:** VMs should have a built-in timeout that doesn't depend on the master server. Already partially there with `timeout` command, but should be explicit.

2. **CLI direct-to-GCP fallback:** Add `--direct` flag that bypasses master server for emergency operations:
   ```bash
   agentctl stop agent-123 --direct  # Calls GCE API directly
   ```

3. **Document the failure mode:** Contributors should understand that master server state can diverge from GCP state.

### 3. ❌ No Idempotency in Agent Creation

**Problem:** If `agentctl run` fails halfway (VM created but DB not updated), you get orphaned VMs that cost money and are invisible to the system.

**Fix:** 
1. Generate agent ID upfront
2. Use GCE labels to track ownership
3. Add reconciliation command: `agentctl reconcile` that syncs DB with actual GCE state

---

## High Priority Issues (Should Fix)

### 4. ⚠️ Startup Script is Fragile

**Problem:** The startup script is a giant bash string with string interpolation. This is:
- Hard to test
- Easy to break with special characters in prompts
- Difficult to debug

**Fix:** 
1. Use a template file instead of inline string
2. Pass configuration via instance metadata (JSON), not interpolated bash
3. Have the VM fetch config from master server on startup

```bash
# Better approach - VM fetches its config
AGENT_ID=$(curl -s "http://metadata/computeMetadata/v1/instance/attributes/agent-id" -H "Metadata-Flavor: Google")
CONFIG=$(curl -s "$MASTER_URL/internal/agents/$AGENT_ID/config")
PROMPT=$(echo "$CONFIG" | jq -r '.prompt')
```

### 5. ⚠️ No Structured Logging

**Problem:** Logs are just print statements and `echo`. This makes it hard to:
- Search/filter logs
- Build dashboards
- Debug issues in production

**Fix:** Use structured JSON logging:

```python
import structlog

logger = structlog.get_logger()
logger.info("agent_created", agent_id=agent_id, engine=engine, timeout=timeout)
```

### 6. ⚠️ SQLite Won't Scale

**Problem:** SQLite is fine for single-user, but:
- No concurrent writes from multiple processes
- No replication
- File locking issues on network drives

**Fix:** This is acceptable for MVP, but:
1. Use SQLAlchemy with an abstract interface
2. Document the limitation
3. Design the schema to be compatible with PostgreSQL migration

---

## Medium Priority Issues (Nice to Have)

### 7. 📝 Missing Error Codes

**Problem:** API errors return text messages but no structured codes. This makes CLI error handling fragile.

**Fix:** Define error codes:

```python
class ErrorCode(str, Enum):
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_NOT_RUNNING = "AGENT_NOT_RUNNING"
    VM_CREATION_FAILED = "VM_CREATION_FAILED"
    INVALID_CONFIG = "INVALID_CONFIG"

class APIError(BaseModel):
    code: ErrorCode
    message: str
    details: dict = {}
```

### 8. 📝 No Retry Logic

**Problem:** GCP API calls can fail transiently. Current code doesn't retry.

**Fix:** Add retry with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def create_vm(...):
    ...
```

### 9. 📝 Agent ID Generation Could Collide

**Problem:** `agent-{uuid[:8]}` has collision probability that increases with scale.

**Fix:** Use full UUID or add timestamp prefix:
```python
def generate_id() -> str:
    return f"agent-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
```

### 10. 📝 Health Monitoring Strategy (Hybrid Approach)

**Original Concern:** Should we use heartbeat (agent pushes) or polling (master pulls)?

**Decision:** Use BOTH for robustness.

| Method | What It Detects | Implementation |
|--------|-----------------|----------------|
| **GCE API Polling** | Is VM running? | Master polls every 60s |
| **Heartbeat (Optional)** | Is agent process healthy? What's it doing? | Agent posts status every 30s |

**Status Logic:**
```python
def get_agent_health(agent):
    vm_status = poll_gce_api(agent.instance_name)
    last_heartbeat = agent.last_heartbeat_at
    
    if vm_status != "RUNNING":
        return "stopped"
    
    if last_heartbeat is None:
        return "running"  # VM up, never got heartbeat (startup phase)
    
    if time_since(last_heartbeat) > 5 * 60:  # 5 min
        return "unresponsive"  # VM up but agent not reporting
    
    return agent.heartbeat_status  # "running", "idle", "working"
```

This gives us:
- **Baseline health** from GCE API (reliable, master-controlled)
- **Rich status** from heartbeats (progress, errors, what agent is doing)
- **Graceful degradation** if heartbeats fail

---

## Documentation Issues

### 11. 📝 Missing CONTRIBUTING.md

For open source, need:
- How to set up dev environment
- How to run tests
- Code style guidelines
- PR process

### 12. 📝 Missing Architecture Diagram

The ASCII diagrams are okay, but a proper diagram would help contributors understand the system.

### 13. 📝 API Versioning Not Addressed

Should the API be versioned? (`/v1/agents` vs `/agents`)

**Recommendation:** Add `/v1` prefix now. It's easier to add than to change later.

---

## Security Review

### ✅ Good Decisions
- Secrets in Secret Manager, not env vars
- Service accounts with minimal permissions
- VMs isolated from each other

### ⚠️ Concerns

1. **Master server has no authentication** - Anyone with the IP can control agents. 
   - **Mitigation:** Document this. Add "use VPN or firewall" to deployment guide.
   - **Future:** Add API key authentication

2. **Startup script has secrets in memory** - API keys are in environment variables on the VM.
   - **Mitigation:** This is standard practice. Just don't log them.

3. **Agent has broad GCP permissions** - `cloud-platform` scope is very broad.
   - **Mitigation:** Document that agents can do anything the service account can do.

---

## Extensibility Assessment

### ✅ Good Extension Points
- Engine abstraction (can add new AI providers)
- Provider abstraction (can add new clouds) - *if added per recommendation*
- CLI uses Click (easy to add commands)
- FastAPI (easy to add endpoints)

### ❌ Missing Extension Points

1. **No plugin system for agent capabilities** - What if someone wants to add:
   - Custom pre/post hooks
   - Different screenshot mechanisms
   - Custom git workflows

   **Recommendation:** Define lifecycle hooks in the startup script:
   ```bash
   # /workspace/.agentctl/hooks/pre-run.sh
   # /workspace/.agentctl/hooks/post-run.sh
   ```

2. **No event system** - Can't subscribe to agent events (started, stopped, committed).
   **Recommendation:** Add webhook support in v2. For now, document polling as the approach.

---

## Recommendations Summary

### Must Do Before Implementation
1. ✅ Add CloudProvider interface for abstraction
2. ✅ Add `--direct` CLI flag for emergency operations
3. ✅ Add reconciliation command
4. Move startup script to template file
5. **✅ Implement secret injection model** (master injects, agents don't have IAM access)
6. **✅ Add network sandbox** (block internal VPC by default)
7. **✅ Add `--allow-internal-network` flag** for trusted workloads

### Should Do During Implementation
8. Use structured logging
9. Add retry logic to GCP calls
10. Use SQLAlchemy for DB abstraction
11. ✅ Add `/v1` API prefix
12. **Implement hybrid health monitoring** (GCE polling + optional heartbeat)

### Do Before Open Source Release
13. Create CONTRIBUTING.md ✅
14. Add architecture diagram
15. Document security model ✅ (SECURITY.md)
16. Add basic authentication option

---

## Approval

**Architecture Status:** ✅ APPROVED

The design is sound for an MVP. The critical issues are addressable without major redesign. Proceed with implementation, incorporating the "Must Do" items.

---

## Appendix: Suggested File Changes

Based on this review, these files need updates:

| File | Change |
|------|--------|
| `TECHNICAL_SPEC.md` | Add CloudProvider interface |
| `IMPLEMENTATION_PLAN_v2.md` | Add Task 1.0: Provider Interface |
| `PRD.md` | Add note about single-user limitation |
| `API.md` | Add `/v1` prefix to all endpoints |
| `COMMANDS.md` | Add `--direct` flag documentation |
| NEW: `CONTRIBUTING.md` | Create contributor guide |
| NEW: `SECURITY.md` | Document security model |
