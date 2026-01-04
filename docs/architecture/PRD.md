# AgentCtl - Product Requirements Document

## Executive Summary

AgentCtl is a CLI-first system for deploying and managing autonomous AI coding agents (Claude Code, Codex) on Google Cloud Platform. Users can spin up isolated VM instances, each running an AI agent working on a specified task, and monitor progress via logs, git commits, screenshots, and SSH access.

The system is designed to be:
- **Simple**: Minimal infrastructure, easy to understand
- **Flexible**: Supports various use cases (research, data mining, MVP building)
- **Extensible**: Clean interfaces allowing future enhancements
- **100% Code-Driven**: Everything deployable via scripts, suitable for open-source distribution

## Problem Statement

Running AI coding agents autonomously requires:
1. Isolated compute environments with proper tooling
2. Secure credential management
3. Persistent workspaces with version control
4. Observability into what agents are doing
5. Cost controls to prevent runaway spending

Currently, users must manually provision VMs, configure environments, and cobble together monitoring. AgentCtl automates this entire workflow.

## Target Users

- Solo developers wanting to leverage AI agents for extended tasks
- Researchers running AI experiments
- Technical users comfortable with CLI tools
- Open-source community members who want to self-host

## Core Requirements

### Functional Requirements

#### FR-1: Agent Lifecycle Management
- **FR-1.1**: Create agents with a prompt, optional repo, timeout, and engine choice (Claude/Codex)
- **FR-1.2**: List all agents with status, uptime, and cost
- **FR-1.3**: Stop agents on demand
- **FR-1.4**: Delete agents and clean up resources
- **FR-1.5**: Restart stopped agents from last git state

#### FR-2: Agent Execution
- **FR-2.1**: Agents run Claude Code or Codex with `--dangerously-skip-permissions`
- **FR-2.2**: Agents work in isolated GCE VM instances
- **FR-2.3**: Agents auto-terminate after configured timeout
- **FR-2.4**: Agents clone specified git repos and work on specified branches
- **FR-2.5**: Agents auto-commit and push to remote branches

#### FR-3: Observability
- **FR-3.1**: Stream real-time logs from agents
- **FR-3.2**: SSH access to agent VMs
- **FR-3.3**: View git history and diffs from agents
- **FR-3.4**: Periodic screenshot capture (configurable frequency and retention)
- **FR-3.5**: Download artifacts from agent workspaces

#### FR-4: Communication
- **FR-4.1**: Send follow-up instructions to running agents
- **FR-4.2**: Agents report status/heartbeat to master server

#### FR-5: Secret Management
- **FR-5.1**: Store API keys in GCP Secret Manager
- **FR-5.2**: CLI commands to set/get/list secrets
- **FR-5.3**: Agents automatically receive necessary credentials at startup

#### FR-6: Master Server
- **FR-6.1**: REST API for all agent operations
- **FR-6.2**: WebSocket endpoint for live log/terminal streaming
- **FR-6.3**: Persistent agent registry (SQLite)
- **FR-6.4**: Manages VM lifecycle via GCE API

### Non-Functional Requirements

#### NFR-1: Simplicity
- Minimal GCP resources required
- Single binary/script installation
- Clear, readable codebase

#### NFR-2: Security
- Credentials never logged or exposed
- **Secret injection model**: Master injects secrets; agents have no IAM access to Secret Manager
- **Network sandbox**: Agent VMs blocked from internal VPC by default (internet allowed)
- Agent VMs have minimal IAM permissions (logging and GCS upload only)
- Configurable `--allow-internal-network` flag for trusted workloads

#### NFR-3: Cost Efficiency
- Support for spot/preemptible instances
- Auto-shutdown on timeout
- Budget alerts integration
- Configurable screenshot retention to control storage costs

#### NFR-4: Extensibility
- Clean separation between CLI, API, and agent runtime
- Plugin architecture for future engines beyond Claude/Codex
- Webhook support for external integrations (future)

#### NFR-5: Portability
- 100% infrastructure-as-code
- Works with standard GCP free tier (where possible)
- Documented setup for fresh GCP projects

## Architecture Overview

### Components

1. **agentctl CLI**: User-facing command-line tool
2. **Master Server**: Coordination API running on GCE/Cloud Run
3. **Agent VMs**: Individual GCE instances running AI agents
4. **Agent Runner**: Process on each VM managing the AI agent
5. **GCP Services**: Secret Manager, Cloud Storage, Cloud Logging

### Data Flow

```
User → CLI → Master Server API → GCE API → Agent VM
                    ↓
              Agent Registry (SQLite)
                    ↓
              GCS (artifacts, screenshots)
```

### Key Design Principles

1. **Dumb Agents, Smart Master**: Agents are unprivileged and sandboxed. Master holds the keys.
2. **Stateless Master**: Master can be restarted; all state in DB and GCP
3. **Git as Truth**: Agent work is tracked in git; VM is ephemeral
4. **Secret Injection**: Master injects secrets via metadata; agents have no IAM access to Secret Manager
5. **Network Sandbox**: Agents can reach internet but not internal VPC (by default)
6. **Graceful Degradation**: If master is down, running agents continue; use `--direct` for emergencies

## User Stories

### US-1: First-Time Setup
> As a user, I want to initialize my GCP project with one command so I can start using AgentCtl quickly.

Acceptance Criteria:
- `agentctl init` creates all required GCP resources
- Prompts for API keys and stores them securely
- Validates GCP authentication
- Provides clear success/error messages

### US-2: Run a Simple Agent
> As a user, I want to start an agent with just a prompt so I can get work done with minimal configuration.

Acceptance Criteria:
- `agentctl run "Build a todo API"` works with sensible defaults
- Agent starts within 3 minutes
- User sees agent ID and status

### US-3: Monitor Agent Progress
> As a user, I want to see what my agent is doing in real-time so I can verify it's on track.

Acceptance Criteria:
- `agentctl logs <id>` streams output
- `agentctl ssh <id>` provides shell access
- Screenshots available via `agentctl screenshots <id>`

### US-4: Provide Additional Instructions
> As a user, I want to give my agent additional instructions mid-task so I can course-correct without restarting.

Acceptance Criteria:
- `agentctl tell <id> "Also add tests"` delivers message
- Agent acknowledges and incorporates instruction
- Instruction logged for audit

### US-5: Control Costs
> As a user, I want my agents to auto-stop after a timeout so I don't get surprised by bills.

Acceptance Criteria:
- `--timeout 4h` stops agent after 4 hours
- Agent commits work before stopping
- User notified of timeout

### US-6: Work with Git Repos
> As a user, I want my agent to work on my existing codebase so I can use it for real projects.

Acceptance Criteria:
- `--repo` clones specified repository
- `--branch` creates/checks out branch
- Agent pushes commits to remote
- SSH key or token authentication works

### US-7: Choose AI Engine
> As a user, I want to choose between Claude Code and Codex so I can use my preferred AI.

Acceptance Criteria:
- `--engine claude` or `--engine codex` works
- Correct API keys used for each
- Same interface regardless of engine

## Known Limitations (MVP)

These limitations are intentional for MVP simplicity:

1. **Single-user only** - No authentication or multi-tenancy. One GCP project = one user.

2. **Master server is SPOF** - If master goes down, can't create/stop agents normally. Use `agentctl stop --direct` for emergencies. Use `agentctl reconcile` to sync state after recovery.

3. **SQLite database** - Won't scale to thousands of agents. Fine for typical use (tens of agents).

4. **GCP only** - No AWS/Azure support yet. Provider interface designed for future extensibility.

5. **No authentication** - Master server API is open. Restrict via firewall/VPN.

See SECURITY.md for security implications and mitigations.

## Out of Scope (MVP)

- Multi-user/team support
- Custom VM images (using startup scripts instead)
- Inter-agent communication
- Agent task queuing
- Automatic PR creation
- Mobile app
- Windows agent VMs
- **Web UI** (CLI-first for MVP; web UI is post-MVP)
- **Codex support** (focus on Claude Code first; Codex is post-MVP)

## Success Metrics

1. User can go from zero to running agent in < 15 minutes
2. Agent startup time < 3 minutes
3. All operations achievable via CLI without GCP Console
4. Zero manual credential handling after initial setup

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Runaway API costs | High bills | Timeout enforcement, budget alerts |
| Agent does destructive action | Data loss | Git commits, isolated VMs, no prod credentials |
| GCP API rate limits | Failed operations | Exponential backoff, request batching |
| Claude Code changes | Breaking changes | Version pinning, abstraction layer |
| Spot instance preemption | Lost work | Frequent auto-commits |

## Timeline

- **Phase 1** (Core CLI - Local): 2 days
- **Phase 2** (Local Server): 2 days
- **Phase 3** (GCP Integration): 3 days
- **Phase 4** (Agent VM & Runner): 3 days

Total estimated: 10 days of Claude Code implementation time

Note: Web UI and Codex support are post-MVP and not included in this timeline.

## Appendix

### A. CLI Command Reference

See `COMMANDS.md` for complete CLI documentation.

### B. API Reference

See `API.md` for REST API documentation.

### C. Technical Specification

See `TECHNICAL_SPEC.md` for implementation details.
