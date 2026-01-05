# Hook Details for Workflow State Patterns

## Phase Transition Rules

| From | To | Required State Files | Created State File |
|------|-----|---------------------|-------------------|
| START | Analysis | (none) | .analysis-done |
| Analysis | Planning | .analysis-done | .plan-approved |
| Planning | User Approval | .plan-approved | (user action) |
| User Approval | Execution | .analysis-done + .plan-approved | .execution-done |
| Execution | Verification | .execution-done | .audit-passed OR (none) |
| Verification (PASS) | COMPLETE | .audit-passed | (cleanup all) |
| Verification (FAIL) | Execution | .execution-done preserved | (retry) |

---

## Hook Types (Claude Code 1.0.40+ Schema)

### PreToolUse Hook (Quality Gate)

Blocks execution if requirements not met:

```json
{
  "matcher": "Task",
  "hooks": [
    {
      "type": "command",
      "command": "test -f .{workflow}-analysis-done && test -f .{workflow}-plan-approved || (echo 'Workflow violation: Analysis and plan approval required' && exit 1)",
      "timeout": 5
    }
  ]
}
```

### PostToolUse Hook (State Progression)

Creates state files on completion:

```json
{
  "matcher": "Task",
  "hooks": [
    {
      "type": "command",
      "command": "touch .{workflow}-analysis-done && echo 'Analysis phase complete'",
      "timeout": 3
    }
  ]
}
```

### Stop Hook (Session Cleanup)

Advises on workflow state when session ends:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "if [ -f .{workflow}-execution-done ]; then echo 'Workflow in progress. Run audit to complete.'; fi",
      "timeout": 5
    }
  ]
}
```

---

## Full Hook Template Structure

`hooks/hooks.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "test -f .{workflow}-analysis-done && test -f .{workflow}-plan-approved || (echo 'Gate violation: Analysis and plan approval required' && exit 1)",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "touch .{workflow}-analysis-done && echo 'Analysis phase complete'",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

**Note:** Pattern-based filtering (e.g., `*executor`, `*analyzer`) is not supported in current schema. Use separate hook configurations or implement filtering in the command script.

---

## Failure Recovery Patterns

### Audit Failure → Retry

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f .{workflow}-audit-failed ]; then echo 'Audit failed. Fix issues and re-run executor.' && rm -f .{workflow}-audit-passed; fi",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

### Successful Completion → Cleanup

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f .{workflow}-audit-passed ]; then rm -f .{workflow}-analysis-done .{workflow}-plan-approved .{workflow}-execution-done && echo 'Workflow complete, state cleaned'; fi",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

---

## Integration with MCP Gateway

Combine workflow states with gateway calls:

```
User Request
    ↓
[PRE HOOK] Check workflow state
    ↓
Agent calls Gateway (Task tool)
    ↓
Gateway executes MCP operation
    ↓
[POST HOOK] Update workflow state
    ↓
Response to user
```

Example hook for MODIFY operations:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "test -f .{workflow}-plan-approved || (echo 'MODIFY requires approved plan' && exit 1)",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```
