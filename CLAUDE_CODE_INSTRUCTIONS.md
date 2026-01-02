# Instructions for Claude Code

## READ THIS FIRST

You are implementing **AgentCtl**, a CLI-first system for deploying autonomous AI coding agents on Google Cloud Platform.

## Critical Rules

1. **Follow the Implementation Plan exactly** - Do tasks in order, don't skip ahead
2. **Write tests first or alongside code** - Every task has test criteria
3. **Small commits** - One commit per task, descriptive messages
4. **Test before committing** - Run the specified tests, verify they pass
5. **Update PROGRESS.md** - Mark each task complete as you go
6. **Ask if stuck** - Don't guess at requirements

## Documentation Order

Read these documents in this order:

1. **PRD.md** - Understand what we're building (10 min read)
2. **IMPLEMENTATION_PLAN_v2.md** - Your step-by-step guide (reference as you work)
3. **COMMANDS.md** - CLI interface spec (reference when implementing CLI)
4. **API.md** - REST API spec (reference when implementing server)

## MVP Scope

**In MVP:**
- CLI: init, run, list, status, stop, delete, tell, logs, ssh
- Server: REST API, SQLite persistence
- GCP: VM creation/deletion, Secret Manager, GCS
- Agent: Claude Code runner, git auto-commit, screenshots

**NOT in MVP (do not implement):**
- Web UI
- Codex support
- WebSocket terminal
- Cost tracking

## Phase Overview

| Phase | Goal | Duration |
|-------|------|----------|
| 1 | Core CLI with mocked API | 2 days |
| 2 | Local FastAPI server | 2 days |
| 3 | GCP integration | 3 days |
| 4 | Agent VM & runner | 3 days |

## Workflow for Each Task

```
1. Read task in IMPLEMENTATION_PLAN_v2.md
2. Create the test file first (if provided)
3. Implement the code
4. Run tests: pytest tests/ -v
5. Manual test if specified
6. git add . && git commit -m "Task X.Y: <description>"
7. Update PROGRESS.md
```

## Project Structure

```
agentctl/
├── agentctl/
│   ├── cli/           # Click commands
│   ├── server/        # FastAPI + SQLite
│   ├── agent/         # VM-side code
│   ├── shared/        # Models, config, API client
│   └── engines/       # Claude engine (extensible)
├── tests/
│   ├── unit/          # Fast, no external deps
│   └── integration/   # API tests, need server
├── scripts/           # Deployment scripts
└── docs/              # Documentation
```

## Key Technical Decisions

- **Python 3.11+** with type hints
- **Click** for CLI
- **FastAPI** for server
- **SQLite** for persistence (no external DB)
- **httpx** for HTTP client
- **rich** for terminal output
- **pydantic** for data validation

## Common Patterns

### CLI Command
```python
@click.command()
@click.argument("agent_id")
def my_command(agent_id):
    try:
        client = get_client()
        result = client.some_action(agent_id)
        console.print(f"[green]✓ Success[/green]")
    except APIError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
```

### API Route
```python
@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    agent = repository.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return agent_to_response(agent)
```

### Test
```python
def test_something():
    # Arrange
    config = AgentConfig(prompt="Test")
    
    # Act
    result = create_agent(config)
    
    # Assert
    assert result.status == AgentStatus.PENDING
```

## Gotchas

1. **GCE operations are async** - Always wait for operations to complete
2. **Startup scripts take 2-3 min** - VM won't be ready immediately
3. **Use `--force` for testing** - Skip confirmation prompts in tests
4. **SQLite path** - Use tmp_path fixture in tests for isolation

## Testing Commands

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run integration tests (needs server running)
pytest tests/integration/ -v

# Run specific test
pytest tests/unit/test_models.py -v

# Run with coverage
pytest --cov=agentctl tests/
```

## When You're Done with a Phase

1. All tests pass: `pytest tests/ -v`
2. Manual verification works
3. Code is committed
4. PROGRESS.md is updated
5. Move to next phase

## Success Criteria

MVP is complete when this works:

```bash
# Setup
agentctl init

# Create and monitor agent
agentctl run --timeout 10m "Create a hello world Python script"
agentctl list
agentctl logs <agent-id> --follow
agentctl ssh <agent-id>

# Control
agentctl tell <agent-id> "Add a docstring"
agentctl stop <agent-id>
agentctl delete <agent-id>
```

Good luck! Start with Task 0.1 in IMPLEMENTATION_PLAN_v2.md.
