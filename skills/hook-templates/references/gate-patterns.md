# Gate Patterns

Gate hooks **block or allow** tool execution based on conditions.

## Basic Gate (PreToolUse)

```bash
#!/bin/bash
# Block dangerous rm commands
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

if [[ "$COMMAND" == *"rm -rf"* ]] || [[ "$COMMAND" == *"rm -r /"* ]]; then
    echo "❌ BLOCKED: Dangerous rm command" >&2
    exit 2
fi
exit 0
```

## Workflow Gate (Prerequisite Check)

```bash
#!/bin/bash
# Block execution without analysis
INPUT=$(cat)
SUBAGENT=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // ""')

[[ "$SUBAGENT" != *"executor"* ]] && exit 0

if [ ! -f .analysis-done ]; then
    echo "❌ BLOCKED: Analysis not completed" >&2
    echo "→ Run /analyze first" >&2
    exit 2
fi

if [ ! -f .plan-approved ]; then
    echo "❌ BLOCKED: Plan not approved" >&2
    echo "→ Run /plan and approve" >&2
    exit 2
fi

echo "✓ All prerequisites met"
exit 0
```

## File Protection Gate

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""')

# Protected paths
PROTECTED=(".env" ".env.*" "*.key" "*.pem" ".git/*" "config/production/*")

for pattern in "${PROTECTED[@]}"; do
    if [[ "$FILE_PATH" == $pattern ]]; then
        echo "❌ BLOCKED: Cannot modify protected file: $FILE_PATH" >&2
        echo "Use appropriate workflow instead" >&2
        exit 2
    fi
done
exit 0
```

## Conditional Gate with State Check

```bash
#!/bin/bash
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // ""')

# Only gate Write/Edit during "review" phase
STATE_FILE=".workflow-state"
if [ -f "$STATE_FILE" ]; then
    PHASE=$(jq -r '.phase // "init"' "$STATE_FILE")
    
    if [[ "$PHASE" == "review" ]] && [[ "$TOOL" =~ ^(Write|Edit)$ ]]; then
        echo "⚠️ Review phase - modifications blocked" >&2
        echo "Complete review before editing" >&2
        exit 2
    fi
fi
exit 0
```

## Stop Gate (Quality Check)

```bash
#!/bin/bash
# Prevent stopping without passing tests
if ! pnpm test --reporter=dot 2>/dev/null; then
    echo "❌ Tests failing - fix before stopping" >&2
    exit 2
fi

# Check for TODO/FIXME
if grep -rn "TODO\|FIXME" src/ 2>/dev/null | head -5; then
    echo "⚠️ Unresolved TODOs found" >&2
    # exit 2  # Uncomment to block
fi

exit 0
```

## Registration Example

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/bash-firewall.sh",
          "timeout": 5
        }]
      },
      {
        "matcher": "Task",
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/workflow-gate.sh",
          "timeout": 10
        }]
      },
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/file-protection.sh",
          "timeout": 5
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/quality-gate.sh",
          "timeout": 30
        }]
      }
    ]
  }
}
```

## Key Points

1. **Use exit 2** to block (not exit 1)
2. **Write reason to stderr** - Claude sees it
3. **Keep fast** - slow gates frustrate users
4. **Be specific** - tell user what to do instead
