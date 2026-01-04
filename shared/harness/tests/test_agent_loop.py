"""Tests for agent_loop.py - TDD style.

These tests define the expected behavior of the agent loop components.
The agent loop implements Anthropic's two-agent pattern for long-running tasks.
"""
import json
import pytest
from pathlib import Path


class TestFeatureListParsing:
    """Tests for feature list JSON parsing and manipulation."""

    def test_parse_valid_feature_list(self, tmp_path):
        """Should parse a valid feature_list.json file."""
        from shared.harness.agent_loop import parse_feature_list

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [
                {"id": 1, "description": "Setup project", "status": "completed"},
                {"id": 2, "description": "Add login page", "status": "pending"},
                {"id": 3, "description": "Add dashboard", "status": "pending"},
            ]
        }))

        features = parse_feature_list(feature_file)

        assert len(features) == 3
        assert features[0]["status"] == "completed"
        assert features[1]["status"] == "pending"

    def test_parse_empty_feature_list(self, tmp_path):
        """Should handle empty feature list."""
        from shared.harness.agent_loop import parse_feature_list

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({"features": []}))

        features = parse_feature_list(feature_file)

        assert features == []

    def test_parse_missing_file_returns_empty(self, tmp_path):
        """Should return empty list if file doesn't exist."""
        from shared.harness.agent_loop import parse_feature_list

        feature_file = tmp_path / "nonexistent.json"

        features = parse_feature_list(feature_file)

        assert features == []

    def test_parse_invalid_json_returns_empty(self, tmp_path):
        """Should return empty list if JSON is invalid."""
        from shared.harness.agent_loop import parse_feature_list

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text("not valid json {{{")

        features = parse_feature_list(feature_file)

        assert features == []

    def test_get_pending_features(self, tmp_path):
        """Should filter to only pending features."""
        from shared.harness.agent_loop import get_pending_features

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [
                {"id": 1, "description": "Done task", "status": "completed"},
                {"id": 2, "description": "Pending task 1", "status": "pending"},
                {"id": 3, "description": "Pending task 2", "status": "pending"},
            ]
        }))

        pending = get_pending_features(feature_file)

        assert len(pending) == 2
        assert all(f["status"] == "pending" for f in pending)

    def test_all_features_completed(self, tmp_path):
        """Should detect when all features are completed."""
        from shared.harness.agent_loop import is_all_completed

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [
                {"id": 1, "description": "Task 1", "status": "completed"},
                {"id": 2, "description": "Task 2", "status": "completed"},
            ]
        }))

        assert is_all_completed(feature_file) is True

    def test_not_all_features_completed(self, tmp_path):
        """Should detect when features are still pending."""
        from shared.harness.agent_loop import is_all_completed

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [
                {"id": 1, "description": "Task 1", "status": "completed"},
                {"id": 2, "description": "Task 2", "status": "pending"},
            ]
        }))

        assert is_all_completed(feature_file) is False


class TestProgressTracking:
    """Tests for progress file reading and writing."""

    def test_load_progress_from_file(self, tmp_path):
        """Should load progress notes from file."""
        from shared.harness.agent_loop import load_progress

        progress_file = tmp_path / "claude-progress.txt"
        progress_file.write_text("Session 1: Set up project structure\nSession 2: Added login")

        progress = load_progress(tmp_path)

        assert "Session 1" in progress
        assert "Added login" in progress

    def test_load_progress_missing_file(self, tmp_path):
        """Should return default message if file doesn't exist."""
        from shared.harness.agent_loop import load_progress

        progress = load_progress(tmp_path)

        assert "No previous progress" in progress or progress == ""

    def test_save_progress(self, tmp_path):
        """Should save progress notes to file."""
        from shared.harness.agent_loop import save_progress

        save_progress(tmp_path, "Completed feature X")

        progress_file = tmp_path / "claude-progress.txt"
        assert progress_file.exists()
        assert "Completed feature X" in progress_file.read_text()

    def test_append_progress(self, tmp_path):
        """Should append to existing progress."""
        from shared.harness.agent_loop import save_progress, load_progress

        # First write
        save_progress(tmp_path, "Session 1 notes")
        # Append
        save_progress(tmp_path, "Session 2 notes", append=True)

        progress = load_progress(tmp_path)
        assert "Session 1" in progress
        assert "Session 2" in progress


class TestSessionDetection:
    """Tests for detecting first session vs continuation."""

    def test_is_first_session_no_feature_file(self, tmp_path):
        """Should detect first session when no feature_list.json exists."""
        from shared.harness.agent_loop import is_first_session

        assert is_first_session(tmp_path) is True

    def test_is_not_first_session_with_feature_file(self, tmp_path):
        """Should detect continuation when feature_list.json exists."""
        from shared.harness.agent_loop import is_first_session

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text('{"features": []}')

        assert is_first_session(tmp_path) is False


class TestPromptGeneration:
    """Tests for prompt generation based on session type."""

    def test_initializer_prompt_contains_app_spec(self):
        """Initializer prompt should include the app specification."""
        from shared.harness.agent_loop import get_initializer_prompt

        app_spec = "Build a REST API with user authentication"
        prompt = get_initializer_prompt(app_spec)

        assert "REST API" in prompt
        assert "user authentication" in prompt

    def test_initializer_prompt_asks_for_feature_list(self):
        """Initializer prompt should request feature_list.json creation."""
        from shared.harness.agent_loop import get_initializer_prompt

        prompt = get_initializer_prompt("Any app")

        assert "feature_list.json" in prompt.lower() or "feature list" in prompt.lower()

    def test_coding_prompt_contains_progress(self):
        """Coding prompt should include previous progress."""
        from shared.harness.agent_loop import get_coding_prompt

        app_spec = "Build a todo app"
        progress = "Session 1: Created initial structure"

        prompt = get_coding_prompt(app_spec, progress)

        assert "Session 1" in prompt
        assert "Created initial structure" in prompt

    def test_coding_prompt_focuses_on_one_feature(self):
        """Coding prompt should instruct agent to work on one feature at a time."""
        from shared.harness.agent_loop import get_coding_prompt

        prompt = get_coding_prompt("Any app", "Some progress")

        # Should mention working on one/single/first feature
        prompt_lower = prompt.lower()
        assert "one" in prompt_lower or "single" in prompt_lower or "first" in prompt_lower


class TestIterationLogic:
    """Tests for the iteration loop logic."""

    def test_should_continue_with_pending_features(self, tmp_path):
        """Should continue when there are pending features."""
        from shared.harness.agent_loop import should_continue

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [
                {"id": 1, "status": "completed"},
                {"id": 2, "status": "pending"},
            ]
        }))

        assert should_continue(tmp_path, current_iteration=1, max_iterations=0) is True

    def test_should_stop_all_completed(self, tmp_path):
        """Should stop when all features are completed."""
        from shared.harness.agent_loop import should_continue

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [
                {"id": 1, "status": "completed"},
                {"id": 2, "status": "completed"},
            ]
        }))

        assert should_continue(tmp_path, current_iteration=1, max_iterations=0) is False

    def test_should_stop_at_max_iterations(self, tmp_path):
        """Should stop when max iterations reached."""
        from shared.harness.agent_loop import should_continue

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [{"id": 1, "status": "pending"}]
        }))

        assert should_continue(tmp_path, current_iteration=10, max_iterations=10) is False

    def test_should_continue_below_max_iterations(self, tmp_path):
        """Should continue when below max iterations."""
        from shared.harness.agent_loop import should_continue

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [{"id": 1, "status": "pending"}]
        }))

        assert should_continue(tmp_path, current_iteration=5, max_iterations=10) is True

    def test_unlimited_iterations_with_zero(self, tmp_path):
        """max_iterations=0 should mean unlimited."""
        from shared.harness.agent_loop import should_continue

        feature_file = tmp_path / "feature_list.json"
        feature_file.write_text(json.dumps({
            "features": [{"id": 1, "status": "pending"}]
        }))

        # Even at iteration 1000, should continue if features pending and max=0
        assert should_continue(tmp_path, current_iteration=1000, max_iterations=0) is True

    def test_first_session_should_always_continue(self, tmp_path):
        """First session (no feature file) should always continue."""
        from shared.harness.agent_loop import should_continue

        # No feature file exists
        assert should_continue(tmp_path, current_iteration=1, max_iterations=0) is True


class TestAppSpecHandling:
    """Tests for loading and handling app specifications."""

    def test_load_app_spec(self, tmp_path):
        """Should load app spec from file."""
        from shared.harness.agent_loop import load_app_spec

        spec_file = tmp_path / "app_spec.txt"
        spec_file.write_text("Build a todo application with React frontend")

        spec = load_app_spec(tmp_path)

        assert "todo application" in spec
        assert "React" in spec

    def test_load_missing_app_spec(self, tmp_path):
        """Should raise error if app_spec.txt is missing."""
        from shared.harness.agent_loop import load_app_spec

        with pytest.raises(FileNotFoundError):
            load_app_spec(tmp_path)
