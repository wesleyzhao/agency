# OAuth Authentication Design

## Overview

This feature adds support for Claude Code OAuth tokens (subscription-based) as an alternative
to API keys (usage-based billing). This enables running agents using a Claude subscription
rather than paying per-token API usage.

## Authentication Methods

### Method 1: API Key (Current)
- Uses `ANTHROPIC_API_KEY` environment variable
- Stored in GCP Secret Manager as `anthropic-api-key`
- Injected via VM instance metadata
- Billed per token usage

### Method 2: OAuth Token (New)
- Uses `CLAUDE_CODE_OAUTH_TOKEN` environment variable
- Optionally uses `~/.claude/.credentials.json` file
- Token generated via `claude setup-token` command locally
- Uses Claude subscription billing

## OAuth Token Format

```json
// ~/.claude/.credentials.json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",
    "expiresAt": 1748658860401,
    "scopes": ["user:inference", "user:profile"]
  }
}
```

The access token can also be used directly via `CLAUDE_CODE_OAUTH_TOKEN`.

## Design Decisions

### 1. Auth Type Configuration
Add an `auth_type` field to configuration:
- `api_key` (default): Use ANTHROPIC_API_KEY
- `oauth`: Use CLAUDE_CODE_OAUTH_TOKEN

### 2. Secret Manager Storage
For OAuth, store the full credentials JSON in Secret Manager:
- Secret name: `claude-oauth-credentials` (configurable)
- Contains the full credentials.json content

### 3. VM Credential Setup
For OAuth auth, the startup script:
1. Retrieves credentials from metadata
2. Creates `~/.claude/.credentials.json` in agent user's home
3. Sets `CLAUDE_CODE_OAUTH_TOKEN` as backup

### 4. Token Refresh Handling
The credentials.json includes a refresh token. Claude Code CLI handles
token refresh automatically when it detects expiration.

## Implementation Plan

### Phase 1: Core Module (this PR)
1. Create `agentctl/shared/auth.py` with credential handling
2. Add tests for credential validation and formatting
3. Update startup_script.py to support both auth types
4. Add `auth_type` config option

### Phase 2: CLI Integration (follow-up)
1. Add `--auth-type` CLI flag
2. Add `agentctl init` step to set up OAuth credentials
3. Add credential validation command

## File Changes

```
agentctl/
  shared/
    auth.py          # NEW: Authentication abstraction
  server/
    services/
      startup_script.py  # MODIFIED: Support OAuth tokens
tests/
  unit/
    test_auth.py     # NEW: Auth module tests
```

## Startup Script Changes

```bash
# Fetch auth configuration from metadata
AUTH_TYPE=$(curl -s "$METADATA_URL/auth-type" -H "$METADATA_HEADER" || echo "api_key")

if [ "$AUTH_TYPE" = "oauth" ]; then
    # OAuth flow
    OAUTH_CREDENTIALS=$(curl -s "$METADATA_URL/oauth-credentials" -H "$METADATA_HEADER")
    mkdir -p $AGENT_HOME/.claude
    echo "$OAUTH_CREDENTIALS" > $AGENT_HOME/.claude/.credentials.json
    chown -R agent:agent $AGENT_HOME/.claude
    chmod 600 $AGENT_HOME/.claude/.credentials.json

    # Also set env var as fallback
    OAUTH_TOKEN=$(echo "$OAUTH_CREDENTIALS" | jq -r '.claudeAiOauth.accessToken')
    export CLAUDE_CODE_OAUTH_TOKEN="$OAUTH_TOKEN"
else
    # API key flow (existing)
    ANTHROPIC_API_KEY=$(curl -s "$METADATA_URL/anthropic-api-key" -H "$METADATA_HEADER")
    export ANTHROPIC_API_KEY
fi
```

## Security Considerations

1. OAuth credentials stored in Secret Manager (same security as API keys)
2. Credentials file has 600 permissions (owner read/write only)
3. Token refresh handled by Claude Code CLI (no custom refresh logic)
4. Metadata endpoint only accessible from within the VM

## Migration Path

1. Feature is additive - existing API key flow unchanged
2. Users opt-in by setting `auth_type: oauth` in config
3. Must create oauth credentials secret via `claude setup-token` + Secret Manager

## Usage Example

```bash
# 1. Generate OAuth token locally (requires browser)
claude setup-token
# Outputs: sk-ant-oat01-...

# 2. Store in GCP Secret Manager
echo '{"claudeAiOauth":{"accessToken":"sk-ant-oat01-..."}}' | \
    gcloud secrets create claude-oauth-credentials --data-file=-

# 3. Launch agent with OAuth
agentctl run "Build a todo app" --auth-type oauth
```
