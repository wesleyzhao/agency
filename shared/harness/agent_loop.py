"""Agent loop components for continuous Claude Code agents.

This module provides reusable functions for:
- Feature list parsing and manipulation
- Progress tracking
- Session detection (first session vs continuation)
- Prompt generation for initializer and coding agents
- Iteration control logic

Based on Anthropic's autonomous-coding patterns:
https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding
"""
import json
from pathlib import Path
from typing import Optional


# ============================================================================
# Feature List Functions
# ============================================================================

def parse_feature_list(feature_file: Path) -> list[dict]:
    """Parse feature_list.json and return list of features.

    Args:
        feature_file: Path to feature_list.json

    Returns:
        List of feature dictionaries, or empty list if file missing/invalid
    """
    if not feature_file.exists():
        return []

    try:
        data = json.loads(feature_file.read_text())
        return data.get("features", [])
    except (json.JSONDecodeError, KeyError):
        return []


def get_pending_features(feature_file: Path) -> list[dict]:
    """Get only pending features from feature list.

    Args:
        feature_file: Path to feature_list.json

    Returns:
        List of features with status "pending"
    """
    features = parse_feature_list(feature_file)
    return [f for f in features if f.get("status") == "pending"]


def is_all_completed(feature_file: Path) -> bool:
    """Check if all features are completed.

    Args:
        feature_file: Path to feature_list.json

    Returns:
        True if all features are completed, False otherwise
    """
    features = parse_feature_list(feature_file)
    if not features:
        return False  # No features means not completed yet

    return all(f.get("status") == "completed" for f in features)


# ============================================================================
# Progress Tracking Functions
# ============================================================================

def load_progress(project_dir: Path) -> str:
    """Load progress notes from claude-progress.txt.

    Args:
        project_dir: Directory containing progress file

    Returns:
        Progress notes as string, or default message if file missing
    """
    progress_file = project_dir / "claude-progress.txt"
    if progress_file.exists():
        return progress_file.read_text()
    return "No previous progress."


def save_progress(project_dir: Path, notes: str, append: bool = False) -> None:
    """Save progress notes to claude-progress.txt.

    Args:
        project_dir: Directory to save progress file
        notes: Progress notes to save
        append: If True, append to existing file; otherwise overwrite
    """
    progress_file = project_dir / "claude-progress.txt"

    if append and progress_file.exists():
        existing = progress_file.read_text()
        notes = existing + "\n" + notes

    progress_file.write_text(notes)


# ============================================================================
# Session Detection Functions
# ============================================================================

def is_first_session(project_dir: Path) -> bool:
    """Check if this is the first session (no feature_list.json yet).

    Args:
        project_dir: Directory to check

    Returns:
        True if this is the first session
    """
    feature_file = project_dir / "feature_list.json"
    return not feature_file.exists()


# ============================================================================
# Prompt Generation Functions
# ============================================================================

def get_initializer_prompt(app_spec: str) -> str:
    """Generate prompt for the first session (initializer agent).

    The initializer agent sets up the project structure and creates
    the feature_list.json file with all tasks.

    Args:
        app_spec: Application specification/requirements

    Returns:
        Prompt string for initializer agent
    """
    return f"""You are an AI coding agent tasked with building an application.

## Your Task
Read the application specification below and:
1. Create a feature_list.json file with ALL features needed (be comprehensive)
2. Set up the initial project structure
3. Create an init.sh script that sets up the development environment
4. Initialize git and make the first commit

## Application Specification
{app_spec}

## Feature List Format
Create feature_list.json with this structure:
{{
    "features": [
        {{"id": 1, "description": "Feature description", "status": "pending"}},
        ...
    ]
}}

## Important
- Be thorough - list ALL features needed
- Mark all features as "pending" initially
- The feature list is the source of truth for what needs to be done
- Make sure init.sh is executable and works

Start by creating the feature_list.json file."""


def get_coding_prompt(app_spec: str, progress: str) -> str:
    """Generate prompt for subsequent sessions (coding agent).

    The coding agent implements features one at a time, updating
    the feature list as it goes.

    Args:
        app_spec: Application specification/requirements
        progress: Previous progress notes

    Returns:
        Prompt string for coding agent
    """
    return f"""You are an AI coding agent continuing work on an application.

## Your Task
1. Read feature_list.json to see what features are pending
2. Pick the FIRST pending feature
3. Implement it completely
4. Test it works
5. Update feature_list.json to mark it as "completed"
6. Commit your changes with a descriptive message

## Application Specification
{app_spec}

## Previous Progress
{progress}

## Important Rules
- Only work on ONE feature per session
- Test your work before marking complete
- Always commit after completing a feature
- Update claude-progress.txt with what you did

Start by reading feature_list.json and picking the next pending feature."""


# ============================================================================
# Iteration Logic Functions
# ============================================================================

def should_continue(
    project_dir: Path,
    current_iteration: int,
    max_iterations: int = 0,
) -> bool:
    """Determine if the agent loop should continue.

    Args:
        project_dir: Directory containing feature_list.json
        current_iteration: Current iteration number (1-based)
        max_iterations: Maximum iterations (0 = unlimited)

    Returns:
        True if loop should continue, False if should stop
    """
    feature_file = project_dir / "feature_list.json"

    # First session always continues (need to create feature list)
    if not feature_file.exists():
        return True

    # Check max iterations (0 means unlimited)
    if max_iterations > 0 and current_iteration >= max_iterations:
        return False

    # Check if all features are completed
    if is_all_completed(feature_file):
        return False

    return True


# ============================================================================
# App Spec Functions
# ============================================================================

def load_app_spec(workspace_dir: Path) -> str:
    """Load application specification from app_spec.txt.

    Args:
        workspace_dir: Directory containing app_spec.txt

    Returns:
        Application specification as string

    Raises:
        FileNotFoundError: If app_spec.txt doesn't exist
    """
    spec_file = workspace_dir / "app_spec.txt"
    if not spec_file.exists():
        raise FileNotFoundError(f"app_spec.txt not found in {workspace_dir}")
    return spec_file.read_text()
