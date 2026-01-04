"""Tests for startup script generation."""
import pytest
from agentctl.server.services.startup_script import (
    generate_startup_script,
    STARTUP_SCRIPT_TEMPLATE,
)


class TestStartupScriptGeneration:
    """Tests for startup script generation."""

    def test_generates_valid_bash_script(self):
        """Generated script should be valid bash."""
        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Build a todo app",
            engine="claude",
            project="my-project",
            bucket="my-bucket",
        )
        assert script.startswith("#!/bin/bash")
        assert "set -e" in script

    def test_substitutes_placeholders(self):
        """Placeholders should be replaced with values."""
        script = generate_startup_script(
            agent_id="agent-123",
            prompt="Build something",
            engine="claude",
            project="test-project",
            bucket="test-bucket",
            master_url="http://localhost:8000",
            repo="https://github.com/user/repo",
            branch="feature-branch",
        )
        assert "agent-123" in script
        assert "test-project" in script
        assert "test-bucket" in script
        assert "http://localhost:8000" in script
        assert "https://github.com/user/repo" in script
        assert "feature-branch" in script

    def test_escapes_prompt(self):
        """Prompts with special characters should be escaped."""
        script = generate_startup_script(
            agent_id="test",
            prompt="Build app with \\n newlines",
            engine="claude",
            project="proj",
            bucket="bucket",
        )
        # Backslashes should be escaped
        assert "\\\\n" in script


class TestStartupScriptAuthHandling:
    """Tests for authentication handling in startup script."""

    def test_default_auth_type_is_api_key(self):
        """Default auth type should be api_key."""
        script = generate_startup_script(
            agent_id="test",
            prompt="Build app",
            engine="claude",
            project="proj",
            bucket="bucket",
        )
        # Should use API key flow by default
        assert 'AUTH_TYPE=$(curl -s "$METADATA_URL/auth-type"' in script
        assert 'ANTHROPIC_API_KEY=$(curl -s "$METADATA_URL/anthropic-api-key"' in script

    def test_script_handles_oauth_auth_type(self):
        """Script should have OAuth handling logic."""
        script = generate_startup_script(
            agent_id="test",
            prompt="Build app",
            engine="claude",
            project="proj",
            bucket="bucket",
        )
        # Should have OAuth handling branch
        assert 'if [ "$AUTH_TYPE" = "oauth" ]' in script
        assert 'OAUTH_CREDENTIALS=$(curl -s "$METADATA_URL/oauth-credentials"' in script
        assert ".claude/.credentials.json" in script
        assert "CLAUDE_CODE_OAUTH_TOKEN" in script

    def test_script_sets_correct_permissions_for_oauth(self):
        """OAuth credentials file should have secure permissions."""
        script = generate_startup_script(
            agent_id="test",
            prompt="Build app",
            engine="claude",
            project="proj",
            bucket="bucket",
        )
        # Should set 600 permissions on credentials file
        assert "chmod 600" in script
        assert ".credentials.json" in script

    def test_oauth_creates_claude_directory(self):
        """OAuth flow should create .claude directory."""
        script = generate_startup_script(
            agent_id="test",
            prompt="Build app",
            engine="claude",
            project="proj",
            bucket="bucket",
        )
        assert 'mkdir -p $AGENT_HOME/.claude' in script

    def test_agent_runs_with_oauth_env_var(self):
        """Agent should receive CLAUDE_CODE_OAUTH_TOKEN when using OAuth."""
        script = generate_startup_script(
            agent_id="test",
            prompt="Build app",
            engine="claude",
            project="proj",
            bucket="bucket",
        )
        # The sudo -u agent env line should handle both auth types
        assert 'CLAUDE_CODE_OAUTH_TOKEN' in script


class TestStartupScriptTemplate:
    """Tests for the startup script template itself."""

    def test_template_has_all_placeholders(self):
        """Template should have all required placeholders."""
        required_placeholders = [
            "__AGENT_ID__",
            "__PROJECT__",
            "__BUCKET__",
            "__PROMPT__",
            "__REPO__",
            "__BRANCH__",
            "__MASTER_URL__",
        ]
        for placeholder in required_placeholders:
            assert placeholder in STARTUP_SCRIPT_TEMPLATE

    def test_template_installs_claude_code(self):
        """Template should install Claude Code CLI."""
        assert "npm install -g @anthropic-ai/claude-code" in STARTUP_SCRIPT_TEMPLATE

    def test_template_installs_claude_agent_sdk(self):
        """Template should install claude-agent-sdk."""
        assert "pip install claude-agent-sdk" in STARTUP_SCRIPT_TEMPLATE

    def test_template_creates_agent_user(self):
        """Template should create non-root agent user."""
        assert "useradd -m -s /bin/bash agent" in STARTUP_SCRIPT_TEMPLATE
        assert "sudo -u agent" in STARTUP_SCRIPT_TEMPLATE
