#!/usr/bin/env python3
"""Railway Agent Runner - Entry point for Claude Code agents on Railway.

This script runs on Railway containers deployed by agency-quickdeploy.
It reads configuration from environment variables and runs the autonomous
agent loop using the claude-agent-sdk.

Environment Variables:
    AGENT_ID: Unique identifier for this agent
    AGENT_PROMPT: Task specification for the agent
    ANTHROPIC_API_KEY: API key for Claude (for api_key auth)
    CLAUDE_CODE_OAUTH_TOKEN: OAuth token (for oauth auth, alternative)
    AUTH_TYPE: 'api_key' or 'oauth'
    MAX_ITERATIONS: Maximum iterations (0 = unlimited)
    REPO_URL: Git repository to clone (optional)
    REPO_BRANCH: Git branch to checkout (optional)
    NO_SHUTDOWN: Keep running after completion (optional)
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def log(message: str) -> None:
    """Log a message with timestamp (Railway captures stdout)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def get_env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name, default)
    if required and not value:
        log(f"ERROR: Required environment variable {name} is not set")
        sys.exit(1)
    return value


def setup_credentials() -> None:
    """Set up Claude Code credentials from environment."""
    auth_type = get_env("AUTH_TYPE", "api_key")

    if auth_type == "oauth":
        oauth_token = get_env("CLAUDE_CODE_OAUTH_TOKEN")
        if oauth_token:
            # Set up OAuth credentials file for claude-code CLI
            claude_dir = Path.home() / ".claude"
            claude_dir.mkdir(parents=True, exist_ok=True)

            creds = {"claudeAiOauth": {"accessToken": oauth_token}}
            creds_file = claude_dir / ".credentials.json"
            creds_file.write_text(json.dumps(creds))
            log("OAuth credentials configured")
        else:
            log("WARNING: OAuth auth type but no CLAUDE_CODE_OAUTH_TOKEN set")
    else:
        api_key = get_env("ANTHROPIC_API_KEY")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            log("API key credentials configured")
        else:
            log("WARNING: No ANTHROPIC_API_KEY set")


def setup_workspace(agent_id: str, prompt: str) -> Path:
    """Set up the agent workspace directory."""
    workspace = Path("/workspace") / agent_id / "project"
    workspace.mkdir(parents=True, exist_ok=True)

    # Clone repository if specified
    repo_url = get_env("REPO_URL")
    repo_branch = get_env("REPO_BRANCH", "main")

    if repo_url:
        log(f"Cloning repository: {repo_url}")
        clone_cmd = ["git", "clone", "--depth", "1", "-b", repo_branch, repo_url, str(workspace)]
        subprocess.run(clone_cmd, check=True)
        log("Repository cloned successfully")

    # Create app_spec.txt with the prompt
    app_spec = workspace.parent / "app_spec.txt"
    app_spec.write_text(prompt)
    log(f"App spec written to {app_spec}")

    # Create empty feature_list.json (workaround for first-file bug)
    feature_list = workspace / "feature_list.json"
    if not feature_list.exists():
        feature_list.write_text('{"features": []}')
        log("Created empty feature_list.json")

    return workspace


def is_first_session(workspace: Path) -> bool:
    """Check if this is the first session (initializer) or continuation."""
    feature_list = workspace / "feature_list.json"
    if not feature_list.exists():
        return True

    try:
        data = json.loads(feature_list.read_text())
        features = data.get("features", [])
        return len(features) == 0
    except (json.JSONDecodeError, OSError):
        return True


def get_pending_features(workspace: Path) -> list:
    """Get list of pending features from feature_list.json."""
    feature_list = workspace / "feature_list.json"
    try:
        data = json.loads(feature_list.read_text())
        return [f for f in data.get("features", []) if f.get("status") == "pending"]
    except (json.JSONDecodeError, OSError, KeyError):
        return []


def load_progress(workspace: Path) -> str:
    """Load progress notes from previous sessions."""
    progress_file = workspace / "claude-progress.txt"
    if progress_file.exists():
        return progress_file.read_text()
    return ""


def get_prompt(workspace: Path, app_spec: str) -> str:
    """Generate the appropriate prompt based on session type."""
    if is_first_session(workspace):
        return f"""You are setting up a new project. Your task is to:

1. Analyze the following application specification
2. Create a feature_list.json file with a structured breakdown of features
3. Each feature should have: id, description, status (pending)
4. Set up the basic project structure

Application Specification:
{app_spec}

Create the feature_list.json file in the current directory with this format:
{{
  "features": [
    {{"id": 1, "description": "Feature description", "status": "pending"}},
    ...
  ]
}}

Work autonomously - do not ask for confirmation. Create the files directly."""
    else:
        progress = load_progress(workspace)
        pending = get_pending_features(workspace)

        if not pending:
            return "All features are complete. Review the project and make any final improvements."

        next_feature = pending[0]
        return f"""You are continuing work on a project.

Application Specification:
{app_spec}

Previous Progress:
{progress if progress else "No previous progress notes."}

Your task for this session: Implement feature #{next_feature.get('id')}
Description: {next_feature.get('description')}

After implementing:
1. Update feature_list.json to mark this feature as "completed"
2. Add notes to claude-progress.txt about what you did
3. Commit your changes with git

Work autonomously - do not ask for confirmation."""


async def run_session(workspace: Path, prompt: str) -> bool:
    """Run a single Claude Code session.

    Returns:
        True if session completed successfully, False if there was an error
    """
    from claude_agent_sdk import query
    from claude_agent_sdk.types import ClaudeAgentOptions

    log(f"Starting session in {workspace}")
    log(f"Prompt: {prompt[:100]}...")

    try:
        # Create proper options object
        options = ClaudeAgentOptions(
            cwd=str(workspace),
            permission_mode="bypassPermissions",
        )

        # query() returns an AsyncIterator, not a coroutine
        # We need to iterate over it to get messages
        result_messages = []
        async for message in query(prompt=prompt, options=options):
            # Log each message type as it comes in
            msg_type = type(message).__name__
            log(f"  {msg_type}: {str(message)[:100]}...")
            result_messages.append(message)

        log(f"Session completed with {len(result_messages)} messages")
        return True
    except Exception as e:
        log(f"Session error: {e}")
        return False


async def run_agent_loop(workspace: Path, app_spec: str, max_iterations: int) -> None:
    """Run the continuous agent loop.

    This loop is designed for 24/7 operation with error recovery.
    Individual session failures don't crash the loop - it will retry
    with exponential backoff.
    """
    iteration = 0
    consecutive_failures = 0
    max_consecutive_failures = 5
    base_retry_delay = 30  # seconds

    while True:
        iteration += 1
        log(f"=== Iteration {iteration} ===")

        # Check max iterations
        if max_iterations > 0 and iteration > max_iterations:
            log(f"Reached max iterations ({max_iterations})")
            break

        # Generate prompt for this session
        prompt = get_prompt(workspace, app_spec)

        # Run the session with error handling
        success = await run_session(workspace, prompt)

        if success:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                log(f"Too many consecutive failures ({consecutive_failures}), pausing for recovery")
                # Exponential backoff: 30s, 60s, 120s, 240s, 480s
                retry_delay = base_retry_delay * (2 ** min(consecutive_failures - 1, 4))
                log(f"Waiting {retry_delay} seconds before retry...")
                await asyncio.sleep(retry_delay)
            else:
                log(f"Session failed, retrying after short delay ({consecutive_failures}/{max_consecutive_failures})")
                await asyncio.sleep(5)
            continue  # Retry without incrementing logical progress

        # Check if all features are complete
        pending = get_pending_features(workspace)
        if not pending and not is_first_session(workspace):
            log("All features completed!")
            break

        # Small delay between iterations
        await asyncio.sleep(2)

    log("Agent loop finished")


def main() -> None:
    """Main entry point."""
    log("Railway Agent Runner starting...")

    # Check NO_SHUTDOWN flag early so we can use it in error handling
    no_shutdown = get_env("NO_SHUTDOWN", "false").lower() == "true"
    error_occurred = False

    try:
        # Get required environment variables
        agent_id = get_env("AGENT_ID", required=True)
        agent_prompt = get_env("AGENT_PROMPT", required=True)
        max_iterations = int(get_env("MAX_ITERATIONS", "0"))

        log(f"Agent ID: {agent_id}")
        log(f"Max iterations: {max_iterations if max_iterations > 0 else 'unlimited'}")
        log(f"NO_SHUTDOWN: {no_shutdown}")

        # Set up credentials
        setup_credentials()

        # Set up workspace
        workspace = setup_workspace(agent_id, agent_prompt)
        log(f"Workspace: {workspace}")

        # Run the agent loop
        asyncio.run(run_agent_loop(workspace, agent_prompt, max_iterations))

    except KeyboardInterrupt:
        log("Agent interrupted")
    except Exception as e:
        log(f"Agent error: {e}")
        error_occurred = True
        import traceback
        traceback.print_exc()

    # Handle shutdown behavior
    if no_shutdown:
        if error_occurred:
            log("NO_SHUTDOWN set - keeping container running despite error (for debugging)")
        else:
            log("NO_SHUTDOWN set - keeping container running")
        # Keep running so Railway doesn't restart
        while True:
            asyncio.run(asyncio.sleep(3600))
    else:
        if error_occurred:
            log("Agent failed - container will exit with error")
            sys.exit(1)
        else:
            log("Agent complete - container will exit")


if __name__ == "__main__":
    main()
