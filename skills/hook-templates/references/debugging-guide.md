# Hook Debugging Guide

Techniques for debugging Claude Code hooks.

## Debugging Basics

### 1. Use stderr for Debug Output

```bash
#!/bin/bash
echo "DEBUG: Hook started" >&2
INPUT=$(cat)
echo "DEBUG: Received input" >&2
echo "DEBUG: Tool = $(echo "$INPUT" | jq -r '.tool_name')" >&2

# Process normally
exit 0
```

**Key point**: stderr doesn't affect Claude's context, stdout does!

### 2. Log to Files

```bash
#!/bin/bash
LOG_DIR="$CLAUDE_PROJECT_DIR/.claude/hooks/logs"
mkdir -p "$LOG_DIR"

INPUT=$(cat)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Log full input
echo "$INPUT" > "$LOG_DIR/${TIMESTAMP}_input.json"

# Log formatted
{
    echo "=== $(date) ==="
    echo "Tool: $(echo "$INPUT" | jq -r '.tool_name')"
    echo "Input: $(echo "$INPUT" | jq -c '.tool_input')"
} >> "$LOG_DIR/debug.log"
```

### 3. Validate JSON Input

```bash
#!/bin/bash
INPUT=$(cat)

# Check if valid JSON
if ! echo "$INPUT" | jq . >/dev/null 2>&1; then
    echo "ERROR: Invalid JSON input" >&2
    echo "Raw input: $INPUT" >&2
    exit 1
fi

# Check required fields
TOOL=$(echo "$INPUT" | jq -r '.tool_name // "MISSING"')
if [ "$TOOL" = "MISSING" ]; then
    echo "ERROR: Missing tool_name field" >&2
    exit 1
fi
```

## Common Issues

### Issue 1: Hook Not Executing

**Symptoms**: Hook seems to be ignored

**Debug steps**:
```bash
#!/bin/bash
# Add to beginning of hook
echo "HOOK EXECUTED: $(date)" >> /tmp/hook-test.log

INPUT=$(cat)
echo "INPUT: $INPUT" >> /tmp/hook-test.log
```

**Common causes**:
1. settings.json not reloaded (need new session)
2. Wrong matcher pattern
3. Hook not executable (`chmod +x hook.sh`)
4. Path error in command

### Issue 2: Exit Code Not Working

**Symptoms**: exit 2 doesn't block

**Debug**:
```bash
#!/bin/bash
echo "About to exit with code 2" >&2
exit 2

# Verify the exit actually happens:
echo "This should never run" >&2
```

**Common causes**:
1. Using exit 1 instead of exit 2
2. Subshell issues (use `exit` not `return`)
3. Script continuing after intended exit

### Issue 3: stdin Not Available

**Symptoms**: INPUT is empty

**Debug**:
```bash
#!/bin/bash
# Check if stdin has data
if [ -t 0 ]; then
    echo "ERROR: No stdin (terminal mode)" >&2
    exit 1
fi

INPUT=$(cat)
if [ -z "$INPUT" ]; then
    echo "ERROR: Empty stdin" >&2
    exit 1
fi
```

**Common causes**:
1. Running hook directly in terminal (no stdin)
2. Reading stdin twice (cat consumes it)
3. Pipe issues in complex commands

### Issue 4: Context Injection Not Working

**Symptoms**: stdout not appearing in Claude's context

**Debug**:
```bash
#!/bin/bash
# Verify this is UserPromptSubmit
INPUT=$(cat)
echo "DEBUG: Event check" >&2

# Output to stdout (should appear in context)
echo "🔧 TEST: This should appear in Claude's context"
exit 0
```

**Common causes**:
1. Wrong event type (only UserPromptSubmit injects context)
2. Output going to stderr instead of stdout
3. Hook returning non-zero exit code

## Test Script

Save as `test-hook.sh`:

```bash
#!/bin/bash
# Test hook with sample input

HOOK_SCRIPT="$1"
EVENT_TYPE="${2:-PreToolUse}"

if [ -z "$HOOK_SCRIPT" ]; then
    echo "Usage: $0 <hook-script> [event-type]"
    exit 1
fi

# Generate test input based on event type
case "$EVENT_TYPE" in
    "PreToolUse"|"PostToolUse")
        TEST_INPUT='{
            "tool_name": "Bash",
            "tool_input": {"command": "echo test"},
            "session_id": "test-session-123"
        }'
        ;;
    "UserPromptSubmit")
        TEST_INPUT='{
            "prompt": "test prompt",
            "session_id": "test-session-123",
            "cwd": "/tmp"
        }'
        ;;
    "Stop")
        TEST_INPUT='{
            "stop_reason": "end_turn",
            "session_id": "test-session-123"
        }'
        ;;
esac

echo "=== Testing $HOOK_SCRIPT ==="
echo "Event: $EVENT_TYPE"
echo "Input: $TEST_INPUT"
echo ""
echo "=== Hook Output ==="

echo "$TEST_INPUT" | "$HOOK_SCRIPT"
EXIT_CODE=$?

echo ""
echo "=== Exit Code: $EXIT_CODE ==="
case $EXIT_CODE in
    0) echo "Result: ALLOW" ;;
    2) echo "Result: BLOCK" ;;
    *) echo "Result: ERROR" ;;
esac
```

Usage:
```bash
chmod +x test-hook.sh
./test-hook.sh .claude/hooks/my-hook.sh PreToolUse
```

## Logging Setup

### Structured Logging

```bash
#!/bin/bash
LOG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/logs/hook.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    local level="$1"
    local message="$2"
    echo "[$(date -Iseconds)] [$level] $message" >> "$LOG_FILE"
}

log "INFO" "Hook started"
INPUT=$(cat)
log "DEBUG" "Input: $(echo "$INPUT" | jq -c .)"

# ... processing ...

log "INFO" "Hook completed with exit 0"
exit 0
```

### JSON Logging

```bash
#!/bin/bash
LOG_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/logs/events.jsonl"
mkdir -p "$(dirname "$LOG_FILE")"

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
SESSION=$(echo "$INPUT" | jq -r '.session_id // "unknown"')

# Log as JSON line
jq -n \
    --arg ts "$(date -Iseconds)" \
    --arg tool "$TOOL" \
    --arg session "$SESSION" \
    --argjson input "$INPUT" \
    '{timestamp: $ts, tool: $tool, session: $session, input: $input}' \
    >> "$LOG_FILE"
```

## Quick Checklist

- [ ] Hook is executable (`chmod +x`)
- [ ] Using correct event type
- [ ] Reading stdin with `INPUT=$(cat)`
- [ ] Using exit 2 for blocking (not exit 1)
- [ ] Debug output goes to stderr (`>&2`)
- [ ] Context injection goes to stdout
- [ ] JSON parsing uses jq
- [ ] settings.json reloaded (new session)
