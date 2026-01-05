# MCP Setup Automation

## SessionStart Hook for Auto-Configuration

```json
{
  "hooks": [
    {
      "type": "SessionStart",
      "name": "mcp-auto-setup",
      "command": "${PLUGIN_ROOT}/scripts/setup_mcp.sh",
      "timeout": 30000
    }
  ]
}
```

## Setup Script Template

```bash
#!/bin/bash
# MCP Auto-Configuration Script

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🔧 Plugin Name - MCP Configuration Check"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if required command exists
if ! command -v <required-command> &> /dev/null; then
  echo "  ⚠️  <required-command> not installed"
  echo "  → Install with: <installation-command>"
  echo "════════════════════════════════════════════════════════════"
  exit 0
fi

# Check if MCP is already registered
if claude mcp list 2>/dev/null | grep -q "^<server-name>:"; then
  echo "  ✓ <Server Name> MCP already configured"
  echo "════════════════════════════════════════════════════════════"
  exit 0
fi

# Register MCP server
echo "  ⚙️  Registering <Server Name> MCP server..."

if claude mcp add --transport stdio --scope user <server-name> -- <command> <args> 2>&1; then
  echo ""
  echo "  ✅ <Server Name> MCP registered!"
  echo ""
  echo "  ⚠️  RESTART REQUIRED"
  echo "  → Restart Claude Code for changes to take effect"
  echo ""
else
  echo "  ❌ Failed to register MCP"
  echo "  → Try manual registration:"
  echo "  claude mcp add --transport stdio --scope user <server-name> -- <command> <args>"
fi

echo "════════════════════════════════════════════════════════════"
```

## Key Points

1. **Idempotent**: Check if already registered before adding
2. **Clear feedback**: Show status and next steps
3. **No blocking**: Exit gracefully if prerequisites missing
4. **Restart reminder**: MCP changes require session restart
