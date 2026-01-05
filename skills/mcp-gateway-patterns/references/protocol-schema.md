# MCP Gateway Protocol Schema

## Request Schema

```json
{
  "intent": "QUERY|ANALYZE|GENERATE|MODIFY|EXECUTE",
  "action": "mcp_specific_action_name",
  "effect": "READ_ONLY|MUTATING|EXTERNAL_EXEC",
  "artifact": "TEXT|JSON|CODE_PY|CODE_TS|PATCH|BINARY",
  "params": { },
  "constraints": {
    "timeout_ms": 300000,
    "retry_count": 0,
    "isolation": "agent|subprocess"
  },
  "context": {
    "caller": "optional_caller_name",
    "project_root": "/path/to/project"
  }
}
```

## Response Schema (Success)

```json
{
  "ok": true,
  "request": { "intent": "...", "action": "...", "effect": "..." },
  "result": {
    "artifact_type": "JSON",
    "data": { },
    "affected_files": [],
    "affected_symbols": []
  },
  "meta": {
    "duration_ms": 1234,
    "mcp_name": "serena",
    "isolation_used": "agent"
  }
}
```

## Response Schema (Error)

```json
{
  "ok": false,
  "error": {
    "type": "TIMEOUT|MCP_ERROR|VALIDATION|PERMISSION|UNKNOWN",
    "message": "description",
    "recoverable": true,
    "suggestion": "recovery hint"
  }
}
```

---

## Intent Details

| Intent | Description | Default Effect |
|--------|-------------|----------------|
| QUERY | Search/lookup/explore | READ_ONLY |
| ANALYZE | Interpret/summarize/impact analysis | READ_ONLY |
| GENERATE | Create artifacts (no file save) | READ_ONLY |
| MODIFY | Change files/code/state | MUTATING |
| EXECUTE | External system invocation | EXTERNAL_EXEC |

## Auxiliary Fields

| Field | Values | Purpose |
|-------|--------|---------|
| effect | READ_ONLY, MUTATING, EXTERNAL_EXEC | Risk level for timeout/retry/permission |
| artifact | TEXT, JSON, CODE_PY, CODE_TS, PATCH, BINARY | Output format for post-processing |

---

## Workflow State Integration

For multi-step operations, combine with `workflow-state-patterns`:

```
Intent: MODIFY
  ↓
[PRE-GATE] Check .analysis-done exists
  ↓
Gateway executes action
  ↓
[POST-GATE] Create .execution-done
```
