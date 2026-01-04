"""Tests for startup_template.py - TDD style.

These tests define the expected behavior of the startup template generator.
Write these first, then implement to make them pass.
"""
import pytest


class TestGenerateStartupScript:
    """Tests for generate_startup_script function."""

    def test_generates_valid_bash_script(self):
        """Generated script should be valid bash with shebang."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent-123",
            prompt="Build a hello world app",
            project="my-gcp-project",
            bucket="my-bucket",
        )

        assert script.startswith("#!/bin/bash")
        assert "set -e" in script  # Error handling

    def test_substitutes_agent_id(self):
        """Agent ID should be substituted in the script."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="agent-20260102-abc123",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        assert "agent-20260102-abc123" in script
        assert "__AGENT_ID__" not in script  # Placeholder should be gone

    def test_substitutes_project(self):
        """GCP project should be substituted in the script."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="my-special-project",
            bucket="test-bucket",
        )

        assert "my-special-project" in script
        assert "__PROJECT__" not in script

    def test_substitutes_bucket(self):
        """GCS bucket should be substituted in the script."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="my-special-bucket",
        )

        assert "my-special-bucket" in script
        assert "__BUCKET__" not in script

    def test_substitutes_prompt(self):
        """Prompt should be substituted in the script."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Build a REST API with FastAPI and PostgreSQL",
            project="test-project",
            bucket="test-bucket",
        )

        assert "Build a REST API with FastAPI and PostgreSQL" in script
        assert "__PROMPT__" not in script

    def test_handles_prompt_with_special_characters(self):
        """Prompt with special bash characters should be safely escaped."""
        from shared.harness.startup_template import generate_startup_script

        # These characters could break bash if not escaped properly
        prompt = 'Build an app with "quotes" and $variables and `backticks`'

        script = generate_startup_script(
            agent_id="test-agent",
            prompt=prompt,
            project="test-project",
            bucket="test-bucket",
        )

        # Script should be generated without error
        assert script is not None
        # Prompt should appear somewhere (may be escaped)
        assert "quotes" in script

    def test_handles_optional_repo(self):
        """Optional repo parameter should work when provided."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
            repo="https://github.com/user/myrepo",
        )

        assert "https://github.com/user/myrepo" in script
        assert "__REPO__" not in script

    def test_handles_optional_branch(self):
        """Optional branch parameter should work when provided."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
            branch="feature/my-feature",
        )

        assert "feature/my-feature" in script
        assert "__BRANCH__" not in script

    def test_handles_max_iterations(self):
        """Max iterations should be configurable."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
            max_iterations=10,
        )

        assert "10" in script or "MAX_ITERATIONS" in script

    def test_no_placeholders_remain(self):
        """No __PLACEHOLDER__ style strings should remain after generation."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        # Check for common placeholder patterns
        import re
        placeholders = re.findall(r'__[A-Z_]+__', script)
        assert placeholders == [], f"Unsubstituted placeholders found: {placeholders}"

    def test_creates_agent_user(self):
        """Script should create non-root agent user (required by Claude Code)."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        assert "useradd" in script or "agent" in script

    def test_installs_nodejs(self):
        """Script should install Node.js (required for Claude Code CLI)."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        assert "nodejs" in script.lower() or "node" in script.lower()

    def test_installs_claude_code(self):
        """Script should install Claude Code CLI."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        assert "claude-code" in script or "@anthropic-ai" in script

    def test_no_secrets_in_script(self):
        """API keys should NOT be embedded in the script itself."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        # The actual API key should come from metadata, not be in the script
        assert "sk-ant-" not in script
        # Should use metadata to get the key
        assert "metadata" in script.lower()

    def test_syncs_to_gcs(self):
        """Script should sync progress to GCS."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        assert "gsutil" in script or "gcs" in script.lower()

    def test_shuts_down_on_completion_by_default(self):
        """Script should shutdown VM after agent completes (default behavior)."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        assert "shutdown" in script

    def test_no_shutdown_flag_disables_shutdown(self):
        """When no_shutdown=True, script should NOT shutdown VM."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
            no_shutdown=True,
        )

        # The shutdown command should be skipped when no_shutdown is True
        # Check that either shutdown is not present OR it's inside a conditional that won't execute
        assert 'NO_SHUTDOWN="true"' in script or 'NO_SHUTDOWN=true' in script

    def test_no_shutdown_false_includes_shutdown(self):
        """When no_shutdown=False (explicit), script should shutdown VM."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
            no_shutdown=False,
        )

        assert "shutdown" in script
        # Should NOT have the no-shutdown flag set
        assert 'NO_SHUTDOWN="true"' not in script


class TestStartupTemplateStructure:
    """Tests for the structure and content of the template."""

    def test_installs_required_dependencies(self):
        """Script should install all required system dependencies."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        # Essential dependencies
        required = ["git", "curl", "python"]
        for dep in required:
            assert dep in script.lower(), f"Missing dependency: {dep}"

    def test_logs_to_file(self):
        """Script should log to a file for debugging."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        # Should have logging function or redirect to file
        assert "log" in script.lower() or "/var/log" in script

    def test_reports_status_to_gcs(self):
        """Script should write status to GCS (not just master server)."""
        from shared.harness.startup_template import generate_startup_script

        script = generate_startup_script(
            agent_id="test-agent",
            prompt="Test prompt",
            project="test-project",
            bucket="test-bucket",
        )

        # Should write status file to GCS
        assert "status" in script.lower()
        assert "gs://" in script or "gsutil" in script
