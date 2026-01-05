# Side Effect Patterns

Side effect hooks **perform actions** after tool completion without blocking.

## Auto-Format (PostToolUse)

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

[[ -z "$FILE_PATH" ]] && exit 0

# Format based on extension
case "$FILE_PATH" in
    *.ts|*.tsx|*.js|*.jsx)
        npx prettier --write "$FILE_PATH" 2>/dev/null
        ;;
    *.py)
        black "$FILE_PATH" 2>/dev/null
        isort "$FILE_PATH" 2>/dev/null
        ;;
    *.rs)
        rustfmt "$FILE_PATH" 2>/dev/null
        ;;
    *.go)
        gofmt -w "$FILE_PATH" 2>/dev/null
        ;;
esac
exit 0
```

## Auto-Lint Warning

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

[[ -z "$FILE_PATH" ]] && exit 0

# Run linter and show warnings (don't block)
case "$FILE_PATH" in
    *.py)
        LINT_OUTPUT=$(flake8 "$FILE_PATH" 2>&1)
        if [[ -n "$LINT_OUTPUT" ]]; then
            echo "⚠️ Lint warnings:" >&2
            echo "$LINT_OUTPUT" >&2
        fi
        ;;
    *.ts|*.tsx)
        LINT_OUTPUT=$(npx eslint "$FILE_PATH" 2>&1)
        if [[ $? -ne 0 ]]; then
            echo "⚠️ ESLint issues:" >&2
            echo "$LINT_OUTPUT" | head -10 >&2
        fi
        ;;
esac
exit 0
```

## Auto-Commit (PostToolUse)

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

[[ -z "$FILE_PATH" ]] && exit 0

# Auto-stage and commit
git add "$FILE_PATH" 2>/dev/null

if ! git diff --cached --quiet 2>/dev/null; then
    # Generate commit message from tool context
    TOOL=$(echo "$INPUT" | jq -r '.tool_name // "edit"')
    FILENAME=$(basename "$FILE_PATH")
    git commit -m "chore(ai): $TOOL $FILENAME" 2>/dev/null
fi
exit 0
```

## File Change Tracking

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
TOOL=$(echo "$INPUT" | jq -r '.tool_name // ""')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')

[[ -z "$FILE_PATH" ]] && exit 0

# Log to tracking file
TRACK_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/tracking"
mkdir -p "$TRACK_DIR"

echo "$(date -Iseconds) | $SESSION_ID | $TOOL | $FILE_PATH" >> "$TRACK_DIR/changes.log"
exit 0
```

## Notification/Alert

```bash
#!/bin/bash
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // ""')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

# Desktop notification (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "display notification \"$TOOL: $FILE_PATH\" with title \"Claude Code\""
fi

# Desktop notification (Linux)
if command -v notify-send &>/dev/null; then
    notify-send "Claude Code" "$TOOL: $FILE_PATH"
fi

exit 0
```

## Documentation Reminder

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

[[ -z "$FILE_PATH" ]] && exit 0

# Check if source file without corresponding docs
if [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.py ]]; then
    DOC_FILE="${FILE_PATH%.*}.md"
    if [[ ! -f "$DOC_FILE" ]] && [[ ! -f "docs/${DOC_FILE##*/}" ]]; then
        echo "📝 Consider adding documentation for: $FILE_PATH" >&2
    fi
fi
exit 0
```

## Stop Hook: End-of-Turn Quality

```bash
#!/bin/bash
# Run at end of Claude's turn

echo "════════════════════════════════════════════════"
echo "  📋 End-of-Turn Quality Check"
echo "════════════════════════════════════════════════"

# Install dependencies if needed
if [ -f package.json ]; then
    pnpm install --silent 2>/dev/null
fi

# Type check
if [ -f tsconfig.json ]; then
    if ! pnpm tsc --noEmit 2>/dev/null; then
        echo "❌ TypeScript errors found" >&2
    else
        echo "✓ TypeScript OK"
    fi
fi

# Lint
if [ -f .eslintrc* ] || [ -f eslint.config.* ]; then
    if ! pnpm lint 2>/dev/null; then
        echo "⚠️ Lint issues found" >&2
    else
        echo "✓ Lint OK"
    fi
fi

echo "════════════════════════════════════════════════"
exit 0
```

## Registration Example

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/auto-format.sh",
            "timeout": 10
          },
          {
            "type": "command",
            "command": ".claude/hooks/track-changes.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/quality-check.sh",
          "timeout": 60
        }]
      }
    ]
  }
}
```

## Key Points

1. **Always exit 0** - Side effects shouldn't block
2. **Fail silently** - Use `2>/dev/null` for optional tools
3. **Keep fast** - Users feel slow hooks
4. **Chain multiple hooks** - Order matters in hooks array
