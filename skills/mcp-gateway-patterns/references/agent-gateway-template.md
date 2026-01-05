# Agent Gateway Template

## Full Agent Markdown Template

```markdown
---
name: {mcp}-gateway
description: Central gateway for all {MCP_NAME} MCP tool access. Other agents must call this gateway via Task tool.
tools: ["{mcp_tool_list}"]
model: sonnet
---

# {MCP_NAME} Gateway

Central access point for {MCP_NAME} MCP. All {MCP_NAME} tool calls MUST go through this gateway.

## Request Protocol

All requests use structured JSON format:

\`\`\`json
{
  "intent": "QUERY|ANALYZE|GENERATE|MODIFY|EXECUTE",
  "action": "{mcp_action_name}",
  "effect": "READ_ONLY|MUTATING|EXTERNAL_EXEC",
  "artifact": "TEXT|JSON|CODE_PY|CODE_TS|PATCH|BINARY",
  "params": { ... },
  "context": {
    "caller": "optional",
    "project_root": "/path/to/project"
  }
}
\`\`\`

## Pre-Modification Validation (for MUTATING operations)

Before any MODIFY intent:
1. Verify project/context is activated
2. Verify target exists (symbol, file, etc.)
3. Assess impact scope (reference count, affected files)

## Response Protocol

Always respond with structured JSON:

Success:
\`\`\`json
{
  "ok": true,
  "request": { "intent": "...", "action": "...", "effect": "..." },
  "result": {
    "artifact_type": "JSON",
    "data": { ... },
    "affected_files": ["file1.py", "file2.py"],
    "affected_symbols": ["ClassName.method"]
  },
  "meta": {
    "duration_ms": 1234,
    "mcp_name": "{mcp}",
    "isolation_used": "agent"
  }
}
\`\`\`

Error:
\`\`\`json
{
  "ok": false,
  "request": { "intent": "...", "action": "...", "effect": "..." },
  "error": {
    "type": "MCP_ERROR|VALIDATION|PERMISSION",
    "message": "description",
    "recoverable": true,
    "suggestion": "how to fix"
  },
  "meta": { ... }
}
\`\`\`

## Gateway Rules

1. **Project activation required** - Check context before operations
2. **Pre-modification validation** - MUTATING requires existence check + impact assessment
3. **Report affected scope** - Always include affected_files and affected_symbols for MODIFY
4. **Atomic responses** - One complete response per request
5. **Error suggestions** - Provide recovery guidance on failure

## Supported Actions

| Intent | Action | Description |
|--------|--------|-------------|
| QUERY | {action1} | {description} |
| ANALYZE | {action2} | {description} |
| MODIFY | {action3} | {description} |
```

---

## Example: Serena Gateway

```markdown
---
name: serena-gateway
description: Central gateway for all Serena MCP tool access
tools: ["mcp__serena__find_symbol", "mcp__serena__find_referencing_symbols", "mcp__serena__get_symbols_overview", "mcp__serena__search_for_pattern", "mcp__serena__read_file", "mcp__serena__list_dir", "mcp__serena__read_memory", "mcp__serena__list_memories", "mcp__serena__write_memory", "mcp__serena__replace_symbol_body", "mcp__serena__replace_content", "mcp__serena__insert_after_symbol", "mcp__serena__insert_before_symbol", "mcp__serena__rename_symbol", "mcp__serena__execute_shell_command", "mcp__serena__activate_project", "mcp__serena__check_onboarding_performed"]
model: sonnet
---
```

### Serena Action Mapping

| Intent | Action | Serena Tool |
|--------|--------|-------------|
| QUERY | find_symbol | find_symbol |
| QUERY | search_pattern | search_for_pattern |
| QUERY | list_dir | list_dir |
| QUERY | read_file | read_file |
| ANALYZE | find_refs | find_referencing_symbols |
| ANALYZE | get_overview | get_symbols_overview |
| MODIFY | rename | rename_symbol |
| MODIFY | replace_body | replace_symbol_body |
| MODIFY | replace_content | replace_content |
| MODIFY | insert_before | insert_before_symbol |
| MODIFY | insert_after | insert_after_symbol |
| EXECUTE | shell | execute_shell_command |

---

## Calling Gateway from Other Agents

Other agents call the gateway using Task tool:

```markdown
Use the Task tool with:
- subagent_type: "serena-refactor:serena-gateway"
- prompt: JSON request object
```

Example call:
```json
{
  "intent": "QUERY",
  "action": "find_symbol",
  "effect": "READ_ONLY",
  "artifact": "JSON",
  "params": {
    "name": "MyClass",
    "type": "class"
  },
  "context": {
    "caller": "solid-analyzer",
    "project_root": "."
  }
}
```

---

## Integration with Workflow State

For workflows requiring sequential phases:

1. **PreToolUse hook** checks state files before gateway call
2. **Gateway** executes MCP operation
3. **PostToolUse hook** creates state file on success

Example hook configuration (Claude Code 1.0.40+):
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 scripts/gateway-gate.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Gate script filters by `tool_input.subagent_type` and checks state files before MODIFY operations.
