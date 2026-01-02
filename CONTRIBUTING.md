# Contributing to AgentCtl

Thank you for your interest in contributing to AgentCtl! This document provides guidelines and instructions for contributors.

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build something useful.

## Getting Started

### Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud`) - for GCP integration tests
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/agentctl
cd agentctl

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev,server]"

# Verify installation
agentctl --version
pytest tests/unit/ -v
```

### Running Tests

```bash
# Unit tests (no external dependencies)
pytest tests/unit/ -v

# Integration tests (requires running server)
uvicorn agentctl.server.app:app --port 8000 &
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=agentctl --cov-report=html tests/
```

### Running Locally

```bash
# Start the server
uvicorn agentctl.server.app:app --reload --port 8000

# In another terminal, configure CLI to use local server
export AGENTCTL_MASTER_URL=http://localhost:8000

# Test commands
agentctl list
agentctl run "Test prompt"
```

## Project Structure

```
agentctl/
├── agentctl/
│   ├── cli/          # CLI commands (Click)
│   ├── server/       # FastAPI server
│   ├── agent/        # Code that runs on VMs
│   ├── shared/       # Shared utilities and models
│   ├── engines/      # AI engine implementations
│   └── providers/    # Cloud provider implementations
├── tests/
│   ├── unit/         # Fast tests, no external deps
│   └── integration/  # Tests requiring server/GCP
├── docs/             # Documentation
└── scripts/          # Deployment and utility scripts
```

## Making Changes

### 1. Create an Issue First

Before starting work, create or find an issue describing the change. This allows for discussion before you invest time coding.

### 2. Branch Naming

```
feature/short-description
fix/issue-number-description
docs/what-youre-documenting
```

### 3. Code Style

- **Python:** Follow PEP 8. Use `black` for formatting.
- **Type hints:** Required for all public functions
- **Docstrings:** Required for all public functions and classes
- **Tests:** Required for new features, encouraged for bug fixes

```bash
# Format code
black agentctl/ tests/

# Check types
mypy agentctl/

# Lint
ruff check agentctl/
```

### 4. Commit Messages

Follow conventional commits:

```
feat: add support for custom machine types
fix: handle timeout correctly on spot instances
docs: update CLI reference for new flags
test: add integration tests for stop command
refactor: extract VM creation to provider interface
```

### 5. Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Request review from maintainers

## Architecture Guidelines

### Adding a New CLI Command

1. Create file in `agentctl/cli/`
2. Register in `agentctl/cli/main.py`
3. Add tests in `tests/unit/test_cli_<command>.py`
4. Document in `docs/COMMANDS.md`

```python
# agentctl/cli/mycommand.py
import click
from rich.console import Console

console = Console()

@click.command()
@click.argument("agent_id")
def mycommand(agent_id):
    """Short description for --help."""
    # Implementation
    console.print(f"[green]✓ Done[/green]")
```

### Adding a New API Endpoint

1. Add route in `agentctl/server/routes/`
2. Add Pydantic models for request/response
3. Add tests in `tests/integration/test_api.py`
4. Document in `docs/API.md`

```python
# agentctl/server/routes/myroute.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class MyRequest(BaseModel):
    field: str

@router.post("/myendpoint")
async def my_endpoint(request: MyRequest):
    return {"status": "ok"}
```

### Adding Cloud Provider Support

1. Implement `CloudProvider` interface in `agentctl/providers/`
2. Add provider selection logic
3. Add integration tests
4. Document setup requirements

```python
# agentctl/providers/aws.py
from agentctl.providers.base import CloudProvider

class AWSProvider(CloudProvider):
    def create_vm(self, name: str, config: VMConfig) -> VMInstance:
        # AWS EC2 implementation
        pass
```

## Testing Guidelines

### Unit Tests

- Test one thing per test
- Use descriptive names: `test_create_agent_with_invalid_prompt_raises_error`
- Mock external dependencies
- Fast execution (< 1 second per test)

```python
def test_config_loads_from_file(tmp_path):
    """Config.load() should read values from YAML file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("gcp_project: test-project\n")
    
    config = Config.load(config_file)
    
    assert config.gcp_project == "test-project"
```

### Integration Tests

- Test real interactions between components
- Use fixtures for setup/teardown
- Mark with `@pytest.mark.integration`

```python
@pytest.mark.integration
def test_create_and_list_agent(client):
    """Should be able to create an agent and see it in list."""
    # Create
    response = client.post("/agents", json={"prompt": "Test"})
    assert response.status_code == 201
    agent_id = response.json()["id"]
    
    # List
    response = client.get("/agents")
    assert any(a["id"] == agent_id for a in response.json()["agents"])
```

## Documentation

- Keep docs in sync with code
- Include examples
- Explain "why" not just "what"

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview, quick start |
| `docs/PRD.md` | Product requirements |
| `docs/TECHNICAL_SPEC.md` | Architecture and design |
| `docs/COMMANDS.md` | CLI reference |
| `docs/API.md` | REST API reference |
| `docs/DEPLOYMENT.md` | Deployment guide |
| `CONTRIBUTING.md` | This file |
| `CHANGELOG.md` | Version history |

## Getting Help

- **Questions:** Open a GitHub Discussion
- **Bugs:** Open a GitHub Issue with reproduction steps
- **Security issues:** Email maintainers directly (see SECURITY.md)

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for their contributions
- README.md contributors section

Thank you for contributing! 🎉
