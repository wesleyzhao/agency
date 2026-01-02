# AgentCtl - REST API Reference

## Overview

The AgentCtl Master Server exposes a REST API for managing agents. The CLI is a thin wrapper around this API.

**Base URL:** `http://<master-server-ip>:8000/v1`

**API Version:** v1

> **Note:** All endpoints are prefixed with `/v1`. This allows for future API versions without breaking existing clients.

## Authentication

MVP: No authentication (single-user system)

> ⚠️ **Security Warning:** The master server has no authentication in MVP. Restrict access via firewall rules or VPN. See SECURITY.md for details.

Future: API key authentication planned for v1.1

---

## Endpoints

### Agents

#### Create Agent

```http
POST /v1/agents
```

**Request Body:**
```json
{
  "id": "my-agent",
  "prompt": "Build a todo API with FastAPI",
  "engine": "claude",
  "repo": "https://github.com/user/repo",
  "branch": "feature/todo",
  "timeout": 14400,
  "machine_type": "e2-medium",
  "spot": true,
  "screenshot_interval": 300,
  "screenshot_retention": "24h"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | No | Agent ID (auto-generated if not provided) |
| prompt | string | Yes | Task prompt |
| engine | string | No | "claude" or "codex" (default: claude) |
| repo | string | No | Git repository URL |
| branch | string | No | Git branch to use |
| timeout | integer | No | Timeout in seconds (default: 14400 = 4h) |
| machine_type | string | No | GCE machine type (default: e2-medium) |
| spot | boolean | No | Use spot instance (default: false) |
| screenshot_interval | integer | No | Seconds between screenshots, 0 to disable (default: 300) |
| screenshot_retention | string | No | How long to keep screenshots (default: "24h") |

**Response:** `201 Created`
```json
{
  "id": "my-agent",
  "status": "starting",
  "engine": "claude",
  "repo": "https://github.com/user/repo",
  "branch": "feature/todo",
  "machine_type": "e2-medium",
  "spot": true,
  "timeout_seconds": 14400,
  "external_ip": null,
  "gce_instance_name": "agent-my-agent",
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": null,
  "screenshot_settings": {
    "interval": 300,
    "retention": "24h"
  }
}
```

---

#### List Agents

```http
GET /agents
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status: running, stopped, failed, timeout |

**Response:** `200 OK`
```json
{
  "agents": [
    {
      "id": "my-agent",
      "status": "running",
      "engine": "claude",
      "repo": "https://github.com/user/repo",
      "branch": "feature/todo",
      "external_ip": "34.123.45.67",
      "started_at": "2025-01-15T10:32:00Z",
      "uptime_seconds": 3600,
      "estimated_cost": 0.42
    }
  ],
  "total": 1
}
```

---

#### Get Agent

```http
GET /agents/{agent_id}
```

**Response:** `200 OK`
```json
{
  "id": "my-agent",
  "status": "running",
  "engine": "claude",
  "prompt": "Build a todo API with FastAPI",
  "repo": "https://github.com/user/repo",
  "branch": "feature/todo",
  "machine_type": "e2-medium",
  "spot": true,
  "timeout_seconds": 14400,
  "external_ip": "34.123.45.67",
  "gce_instance_name": "agent-my-agent",
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:32:00Z",
  "uptime_seconds": 3600,
  "time_remaining_seconds": 10800,
  "estimated_cost": 0.42,
  "last_heartbeat": "2025-01-15T11:30:00Z",
  "git_stats": {
    "commits": 12,
    "last_commit_message": "Add DELETE endpoint",
    "last_commit_time": "2025-01-15T11:25:00Z"
  },
  "screenshot_settings": {
    "interval": 300,
    "retention": "24h"
  }
}
```

---

#### Stop Agent

```http
POST /agents/{agent_id}/stop
```

**Response:** `200 OK`
```json
{
  "id": "my-agent",
  "status": "stopped",
  "stopped_at": "2025-01-15T12:00:00Z",
  "final_commit": "abc123f"
}
```

---

#### Delete Agent

```http
DELETE /agents/{agent_id}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| keep_artifacts | boolean | Don't delete GCS artifacts (default: false) |

**Response:** `204 No Content`

---

#### Send Instruction

```http
POST /agents/{agent_id}/tell
```

**Request Body:**
```json
{
  "instruction": "Also add input validation to all endpoints"
}
```

**Response:** `200 OK`
```json
{
  "id": "my-agent",
  "instruction_id": 5,
  "status": "queued",
  "message": "Instruction queued for delivery"
}
```

---

### Logs

#### Get Logs

```http
GET /agents/{agent_id}/logs
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| tail | integer | Number of lines (default: 100) |
| since | string | ISO timestamp or duration (e.g., "1h") |
| follow | boolean | Stream logs via SSE (default: false) |

**Response (non-streaming):** `200 OK`
```json
{
  "agent_id": "my-agent",
  "logs": [
    {
      "timestamp": "2025-01-15T10:32:00Z",
      "message": "Agent starting..."
    },
    {
      "timestamp": "2025-01-15T10:32:05Z",
      "message": "Cloning repository..."
    }
  ]
}
```

**Response (streaming):** `200 OK` with `text/event-stream`
```
event: log
data: {"timestamp": "2025-01-15T10:32:00Z", "message": "Agent starting..."}

event: log
data: {"timestamp": "2025-01-15T10:32:05Z", "message": "Cloning repository..."}
```

---

### Screenshots

#### List Screenshots

```http
GET /agents/{agent_id}/screenshots
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Max screenshots to return (default: 10) |

**Response:** `200 OK`
```json
{
  "agent_id": "my-agent",
  "screenshots": [
    {
      "filename": "screenshot_20250115_113000.png",
      "timestamp": "2025-01-15T11:30:00Z",
      "size_bytes": 245678,
      "url": "/agents/my-agent/screenshots/screenshot_20250115_113000.png"
    }
  ],
  "total": 25
}
```

---

#### Get Screenshot

```http
GET /agents/{agent_id}/screenshots/{filename}
```

**Response:** `200 OK` with `image/png`

Binary PNG data.

---

### Artifacts

#### List Artifacts

```http
GET /agents/{agent_id}/artifacts
```

**Response:** `200 OK`
```json
{
  "agent_id": "my-agent",
  "artifacts": [
    {
      "path": "output/report.pdf",
      "size_bytes": 1024000,
      "created_at": "2025-01-15T11:00:00Z"
    }
  ]
}
```

---

#### Get Artifact

```http
GET /agents/{agent_id}/artifacts/{path}
```

**Response:** `200 OK` with appropriate Content-Type

Binary file data.

---

### Git

#### Get Git Status

```http
GET /agents/{agent_id}/git/status
```

**Response:** `200 OK`
```json
{
  "agent_id": "my-agent",
  "branch": "feature/todo",
  "clean": false,
  "staged": ["src/api.py"],
  "modified": ["README.md"],
  "untracked": ["notes.txt"]
}
```

---

#### Get Git Log

```http
GET /agents/{agent_id}/git/log
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Number of commits (default: 20) |

**Response:** `200 OK`
```json
{
  "agent_id": "my-agent",
  "commits": [
    {
      "hash": "abc123f",
      "short_hash": "abc123f",
      "message": "Add DELETE endpoint",
      "timestamp": "2025-01-15T11:25:00Z"
    }
  ]
}
```

---

#### Get Git Diff

```http
GET /agents/{agent_id}/git/diff
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| commit | string | Commit to diff against (default: HEAD) |

**Response:** `200 OK`
```json
{
  "agent_id": "my-agent",
  "diff": "diff --git a/README.md b/README.md\n..."
}
```

---

### WebSocket

#### Terminal

```
WS /agents/{agent_id}/terminal
```

Provides a live terminal connection to the agent VM.

**Client → Server Messages:**
```json
{"type": "input", "data": "ls -la\n"}
{"type": "resize", "cols": 80, "rows": 24}
```

**Server → Client Messages:**
```json
{"type": "output", "data": "total 16\ndrwxr-xr-x..."}
{"type": "error", "message": "Connection lost"}
{"type": "close", "reason": "Agent stopped"}
```

---

### Internal Endpoints

These are used by agent VMs to communicate with the master. They should not be called by external clients.

#### Heartbeat

```http
POST /internal/heartbeat
```

**Request Body:**
```json
{
  "agent_id": "my-agent",
  "status": "running",
  "message": "Working on task..."
}
```

**Response:** `200 OK`

---

#### Get Pending Instructions

```http
GET /internal/instructions/{agent_id}
```

**Response:** `200 OK`
```json
{
  "instructions": [
    {
      "id": 5,
      "instruction": "Also add input validation",
      "created_at": "2025-01-15T11:00:00Z"
    }
  ]
}
```

---

#### Acknowledge Instruction

```http
POST /internal/instructions/{agent_id}/{instruction_id}/ack
```

**Response:** `200 OK`

---

### Health

#### Health Check

```http
GET /health
```

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 86400
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent 'xyz' not found",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| AGENT_NOT_FOUND | 404 | Agent does not exist |
| AGENT_ALREADY_EXISTS | 409 | Agent with this ID already exists |
| AGENT_NOT_RUNNING | 400 | Agent is not in running state |
| INVALID_REQUEST | 400 | Request validation failed |
| GCP_ERROR | 500 | GCP API error |
| INTERNAL_ERROR | 500 | Internal server error |

---

## Rate Limits

MVP: No rate limits

Future: Consider rate limiting for resource-intensive operations like VM creation.

---

## Pagination

For list endpoints that may return many results, pagination is supported:

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Max items per page (default: 50, max: 100) |
| offset | integer | Number of items to skip |

**Response includes:**
```json
{
  "items": [...],
  "total": 150,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```
