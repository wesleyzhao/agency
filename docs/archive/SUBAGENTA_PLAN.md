# SubAgentA: QuickDeploy MVP

**Branch:** `subagentA/mvp-quickdeploy`
**Agent:** SubAgentA
**Last Updated:** 2026-01-03
**Status:** MVP COMPLETE & VERIFIED (89 tests passing, real GCP integration tested)

## Overview

This branch implements a standalone `agency-quickdeploy` CLI tool that enables one-command launching of GCP VMs running continuous Claude Code agents using Anthropic's proven autonomous-coding harness pattern.

## Goal

Make it as **EASY** and **QUICK** as possible to launch a GCP instance running a 24/7 continuous Claude Code agent.

```bash
agency-quickdeploy launch "Build a todo app with React"
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate `agency_quickdeploy/` module | Avoids conflicts with main agentctl changes |
| No master server | Uses GCS for all state (simpler, proven to work) |
| Shared harness in `shared/harness/` | Reusable by both agentctl and quickdeploy |
| TDD-strict development | Tests written before implementation |

## Module Structure

```
shared/
    harness/                     # Shared harness component
        __init__.py
        startup_template.py      # Core bash template generation
        agent_loop.py            # Python harness (Anthropic pattern)
        tests/

agency_quickdeploy/
    __init__.py
    __main__.py                  # python -m agency_quickdeploy
    cli.py                       # Click commands (entry point: agency-quickdeploy)
    config.py                    # Configuration dataclass
    launcher.py                  # Main orchestration
    gcp/
        vm.py                    # VM creation/deletion
        storage.py               # GCS operations
        secrets.py               # Secret Manager
    tests/
```

## Current Progress

### Phase 0: Setup & Documentation - COMPLETE
- [x] Create directory structure
- [x] Create this progress document
- [x] Verify pytest dependencies

### Phase 1: Shared Harness (TDD) - COMPLETE (44 tests)
- [x] Write `test_startup_template.py` (19 tests)
- [x] Implement `startup_template.py` (all tests pass)
- [x] Write `test_agent_loop.py` (25 tests)
- [x] Implement `agent_loop.py` (all tests pass)

### Phase 2: GCP Components (TDD) - COMPLETE (38 tests)
- [x] config.py with tests (21 tests)
- [x] gcp/storage.py with tests (9 tests)
- [x] gcp/secrets.py
- [x] gcp/vm.py with tests (8 tests)

### Phase 3: Launcher (TDD) - COMPLETE (7 tests)
- [x] launcher.py with tests (7 tests)

### Phase 4: CLI - COMPLETE
- [x] cli.py with Click commands
- [x] __main__.py entry point
- [x] pyproject.toml entry point

### Phase 5: Integration - COMPLETE
- [x] Real GCP VM launch test (agent-20260102-213725-03cddc2f)
- [x] Verified: Agent creates files, runs Claude Code, auto-shuts down
- [ ] Docker-based local test (optional, not needed for MVP)

## Files Modified/Created

**New Packages:**
- `agency_quickdeploy/` - Main quickdeploy package
  - `__init__.py`, `__main__.py`, `cli.py`, `config.py`, `launcher.py`
  - `gcp/` - `vm.py`, `storage.py`, `secrets.py`
  - `tests/` - 45 tests total

- `shared/harness/` - Shared harness components
  - `startup_template.py` - VM startup script generation
  - `agent_loop.py` - Agent loop logic (Anthropic pattern)
  - `tests/` - 44 tests total

- `docs/SUBAGENTA_PLAN.md` - This file
- `pyproject.toml` - Added `agency-quickdeploy` CLI entry point

## Coordination with Main Branch

This implementation is designed to minimize conflicts:
1. Uses separate `agency_quickdeploy/` directory
2. Uses `shared/harness/` for reusable code (not touching existing agentctl code)
3. No changes to existing agentctl modules
4. Can be merged independently when ready

## How to Use (Once Complete)

```bash
# Install
pip install -e .

# Launch an agent
agency-quickdeploy launch "Build a REST API with FastAPI"

# Check status
agency-quickdeploy status agent-20260102-abc123

# View logs
agency-quickdeploy logs agent-20260102-abc123

# Stop agent
agency-quickdeploy stop agent-20260102-abc123
```

## References

- [Anthropic Autonomous Coding](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Full plan: `/Users/wesley/.claude/plans/polished-greeting-orbit.md`
