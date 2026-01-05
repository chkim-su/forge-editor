# MCP Validation Patterns

## Pre-Deployment Checks

### 1. Check MCP Registration Method

```python
# Add to validate_all.py or similar

def validate_mcp_setup(plugin_dir):
    """Validate MCP configuration patterns."""
    issues = []

    # Check for deprecated mcp_servers.json usage
    deprecated_files = [
        Path.home() / ".claude" / "mcp_servers.json",
        plugin_dir / ".claude" / "mcp_servers.json"
    ]

    for f in deprecated_files:
        if f.exists():
            issues.append({
                "severity": "ERROR",
                "code": "MCP001",
                "message": f"Deprecated MCP config found: {f}",
                "fix": "Use 'claude mcp add' instead"
            })

    return issues
```

### 2. Check Agent MCP Access

```python
def validate_agent_mcp_access(agent_file):
    """Check if agent can access required MCP tools."""
    import yaml

    with open(agent_file) as f:
        content = f.read()
        # Parse frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            frontmatter = yaml.safe_load(parts[1])

            tools = frontmatter.get('tools', [])

            # Empty tools = all access (OK)
            if not tools:
                return {"status": "OK", "mcp_access": True}

            # Check if MCP tools included
            has_mcp = any('mcp__' in str(t) for t in tools)

            if not has_mcp:
                # Check if agent body references MCP
                body = parts[2] if len(parts) > 2 else ""
                if 'mcp__' in body:
                    return {
                        "status": "WARNING",
                        "code": "MCP002",
                        "message": "Agent references MCP tools but tools: list excludes them",
                        "fix": "Add MCP tools to frontmatter or leave tools: empty"
                    }

    return {"status": "OK"}
```

### 3. Runtime MCP Verification

```bash
# Check if MCP server is connected
check_mcp_connected() {
    local server_name=$1

    if claude mcp list 2>/dev/null | grep -q "^${server_name}:.*✓ Connected"; then
        return 0  # Connected
    else
        return 1  # Not connected
    fi
}

# Usage
if check_mcp_connected "serena"; then
    echo "Serena MCP ready"
else
    echo "Serena MCP not connected - run setup script"
fi
```

## Error Codes

| Code | Severity | Description |
|------|----------|-------------|
| MCP001 | ERROR | Deprecated mcp_servers.json usage |
| MCP002 | WARNING | Agent references MCP but tools: excludes it |
| MCP003 | INFO | MCP server not connected (may need restart) |
| MCP004 | ERROR | Wrong MCP tool name format |

## Integration with Hooks

```json
{
  "hooks": [
    {
      "type": "PreToolUse",
      "event": "Task",
      "command": "python ${PLUGIN_ROOT}/scripts/check_mcp_access.py --agent ${TOOL_INPUT}",
      "timeout": 5000
    }
  ]
}
```
