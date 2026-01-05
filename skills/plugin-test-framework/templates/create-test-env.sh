#!/bin/bash
#
# Create Virtual Test Environment for Claude Code Plugin Components
# Usage: ./create-test-env.sh [hook|plugin|agent|full] [output-dir]
#

set -e

TYPE="${1:-full}"
OUTPUT_DIR="${2:-/tmp/plugin-test-$(date +%s)}"

echo "Creating test environment: $OUTPUT_DIR"
echo "Type: $TYPE"

# Create directory structure
mkdir -p "$OUTPUT_DIR/.claude/hooks/logs"
mkdir -p "$OUTPUT_DIR/.claude-plugin"
mkdir -p "$OUTPUT_DIR/commands"
mkdir -p "$OUTPUT_DIR/skills/test-skill"
mkdir -p "$OUTPUT_DIR/agents"

#######################################
# Hook Test Components
#######################################
create_hook_tests() {
    local DIR="$1"

    # PreToolUse Guard Hook
    cat > "$DIR/.claude/hooks/pretooluse-guard.sh" << 'HOOK'
#!/bin/bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

LOG_DIR="$(dirname "$0")/logs"
mkdir -p "$LOG_DIR"
echo "$INPUT" > "$LOG_DIR/pretooluse-$(date +%s).json"

# Block dangerous patterns
if [[ "$TOOL_NAME" == "Bash" ]] && echo "$COMMAND" | grep -qE "rm\s+-rf\s+/"; then
    jq -n '{
      "hookSpecificOutput": {"permissionDecision": "deny"},
      "systemMessage": "TEST: Dangerous rm command blocked"
    }'
    exit 0
fi

# Block chmod 777 on sensitive paths
if [[ "$TOOL_NAME" == "Bash" ]] && echo "$COMMAND" | grep -qE "chmod\s+777"; then
    jq -n '{
      "hookSpecificOutput": {"permissionDecision": "deny"},
      "systemMessage": "TEST: Dangerous chmod 777 blocked"
    }'
    exit 0
fi

# Modify npm publish
if [[ "$TOOL_NAME" == "Bash" ]] && echo "$COMMAND" | grep -q "^npm publish"; then
    jq -n --arg cmd "$COMMAND --dry-run" '{
      "hookSpecificOutput": {
        "permissionDecision": "allow",
        "updatedInput": {"command": $cmd}
      },
      "systemMessage": "TEST: Added --dry-run"
    }'
    exit 0
fi

# Auto-allow safe commands
if [[ "$TOOL_NAME" == "Bash" ]] && echo "$COMMAND" | grep -qE "^(echo|pwd|ls|date|whoami)"; then
    jq -n '{"hookSpecificOutput": {"permissionDecision": "allow"}}'
    exit 0
fi

exit 0
HOOK
    chmod +x "$DIR/.claude/hooks/pretooluse-guard.sh"

    # PostToolUse Logger
    cat > "$DIR/.claude/hooks/posttooluse-logger.sh" << 'HOOK'
#!/bin/bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
RESPONSE=$(echo "$INPUT" | jq -c '.tool_response // {}')
TOOL_ID=$(echo "$INPUT" | jq -r '.tool_use_id // "unknown"')

LOG_DIR="$(dirname "$0")/logs"
mkdir -p "$LOG_DIR"

SUCCESS=true
echo "$RESPONSE" | grep -qiE "(error|failed|exception)" && SUCCESS=false

jq -n --arg tool "$TOOL_NAME" --arg id "$TOOL_ID" --argjson success "$SUCCESS" \
    '{timestamp: (now|todate), tool: $tool, tool_use_id: $id, success: $success}' \
    >> "$LOG_DIR/tool-usage.jsonl"

echo "PostToolUse logged: $TOOL_NAME (success: $SUCCESS)"
exit 0
HOOK
    chmod +x "$DIR/.claude/hooks/posttooluse-logger.sh"

    # UserPromptSubmit Context Injector
    cat > "$DIR/.claude/hooks/context-injector.sh" << 'HOOK'
#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // ""')

LOG_DIR="$(dirname "$0")/logs"
mkdir -p "$LOG_DIR"
echo "$INPUT" > "$LOG_DIR/userprompt-$(date +%s).json"

# Context injection via stdout
cat << 'EOF'
=== TEST CONTEXT INJECTION ===
[Virtual Test Environment Active]
- Mode: Testing
- Time: $(date)
- Status: OPERATIONAL
==============================
EOF

exit 0
HOOK
    chmod +x "$DIR/.claude/hooks/context-injector.sh"

    # Stop Control Hook
    cat > "$DIR/.claude/hooks/stop-control.sh" << 'HOOK'
#!/bin/bash
INPUT=$(cat)
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

# Prevent infinite loop
if [[ "$STOP_HOOK_ACTIVE" == "true" ]]; then
    exit 0
fi

# Check for workflow state
WORKFLOW_STATE=".claude/workflow-state.json"
if [[ -f "$WORKFLOW_STATE" ]]; then
    PHASE=$(jq -r '.phase // "unknown"' "$WORKFLOW_STATE")
    if [[ "$PHASE" != "complete" ]]; then
        jq -n --arg phase "$PHASE" '{
          "decision": "block",
          "reason": ("Workflow not complete. Phase: " + $phase)
        }'
        exit 0
    fi
fi

exit 0
HOOK
    chmod +x "$DIR/.claude/hooks/stop-control.sh"

    # Settings.json
    cat > "$DIR/.claude/settings.json" << 'JSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": ".claude/hooks/pretooluse-guard.sh", "timeout": 10}
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {"type": "command", "command": ".claude/hooks/posttooluse-logger.sh", "timeout": 10}
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": ".claude/hooks/context-injector.sh", "timeout": 10}
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": ".claude/hooks/stop-control.sh", "timeout": 10}
        ]
      }
    ]
  }
}
JSON
}

#######################################
# Plugin Test Components
#######################################
create_plugin_tests() {
    local DIR="$1"

    # plugin.json
    cat > "$DIR/.claude-plugin/plugin.json" << 'JSON'
{
  "name": "test-plugin",
  "description": "Virtual test plugin for validation",
  "version": "1.0.0",
  "author": {
    "name": "Test Author",
    "email": "test@example.com"
  }
}
JSON

    # Sample command
    cat > "$DIR/commands/test-command.md" << 'MD'
---
description: Test command for validation
argument-hint: [optional args]
allowed-tools: ["Read", "Write", "Bash"]
---

# Test Command

This is a test command for plugin validation.

## Usage

```
/test-plugin:test-command [args]
```
MD

    # Sample skill
    cat > "$DIR/skills/test-skill/SKILL.md" << 'MD'
---
name: test-skill
description: Test skill for validation
version: 1.0.0
---

# Test Skill

This is a test skill for plugin validation.

## Usage

Load this skill when testing plugin functionality.
MD
}

#######################################
# Agent Test Components
#######################################
create_agent_tests() {
    local DIR="$1"

    # Sample agent
    cat > "$DIR/agents/test-agent.md" << 'MD'
---
description: Test agent for validation
allowed-tools: ["Read", "Write", "Bash", "Glob", "Grep"]
model: haiku
---

# Test Agent

You are a test agent for plugin validation.

## Your Task

1. Read the provided context
2. Execute the requested operation
3. Return structured results

## Guidelines

- Always validate input
- Log all operations
- Return clear status messages
MD
}

#######################################
# Test Runner
#######################################
create_test_runner() {
    local DIR="$1"

    cat > "$DIR/run-tests.sh" << 'SCRIPT'
#!/bin/bash
# Plugin Component Test Runner

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS="$TEST_DIR/TEST-RESULTS.md"
PASS=0
FAIL=0

echo "# Plugin Test Results" > "$RESULTS"
echo "**Date:** $(date)" >> "$RESULTS"
echo "**Directory:** $TEST_DIR" >> "$RESULTS"
echo "" >> "$RESULTS"

test_result() {
    local NAME="$1"
    local RESULT="$2"
    if [[ "$RESULT" == "pass" ]]; then
        echo "✅ PASS: $NAME"
        echo "- ✅ $NAME" >> "$RESULTS"
        ((PASS++))
    else
        echo "❌ FAIL: $NAME"
        echo "- ❌ $NAME" >> "$RESULTS"
        ((FAIL++))
    fi
}

echo "================================"
echo "  Plugin Component Tests"
echo "================================"
echo ""

#--- Hook Tests ---
echo "## Hook Tests" >> "$RESULTS"
if [ -d "$TEST_DIR/.claude/hooks" ]; then
    echo "--- Hook Tests ---"

    # Test 1: Block dangerous rm
    OUTPUT=$(echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | \
        "$TEST_DIR/.claude/hooks/pretooluse-guard.sh" 2>&1)
    if echo "$OUTPUT" | grep -q "deny"; then
        test_result "Block dangerous rm" "pass"
    else
        test_result "Block dangerous rm" "fail"
    fi

    # Test 2: Modify npm publish
    OUTPUT=$(echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"npm publish"}}' | \
        "$TEST_DIR/.claude/hooks/pretooluse-guard.sh" 2>&1)
    if echo "$OUTPUT" | grep -q "dry-run"; then
        test_result "Modify npm publish" "pass"
    else
        test_result "Modify npm publish" "fail"
    fi

    # Test 3: Auto-allow safe
    OUTPUT=$(echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"echo hello"}}' | \
        "$TEST_DIR/.claude/hooks/pretooluse-guard.sh" 2>&1)
    if echo "$OUTPUT" | grep -q "allow"; then
        test_result "Auto-allow safe command" "pass"
    else
        test_result "Auto-allow safe command" "fail"
    fi

    # Test 4: PostToolUse success
    OUTPUT=$(echo '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_response":{"output":"ok"},"tool_use_id":"t1"}' | \
        "$TEST_DIR/.claude/hooks/posttooluse-logger.sh" 2>&1)
    if echo "$OUTPUT" | grep -q "success: true"; then
        test_result "Log success" "pass"
    else
        test_result "Log success" "fail"
    fi

    # Test 5: PostToolUse failure
    OUTPUT=$(echo '{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_response":{"error":"failed"},"tool_use_id":"t2"}' | \
        "$TEST_DIR/.claude/hooks/posttooluse-logger.sh" 2>&1)
    if echo "$OUTPUT" | grep -q "success: false"; then
        test_result "Detect failure" "pass"
    else
        test_result "Detect failure" "fail"
    fi

    # Test 6: Context injection
    OUTPUT=$(echo '{"hook_event_name":"UserPromptSubmit","prompt":"test"}' | \
        "$TEST_DIR/.claude/hooks/context-injector.sh" 2>&1)
    if echo "$OUTPUT" | grep -q "TEST CONTEXT"; then
        test_result "Context injection" "pass"
    else
        test_result "Context injection" "fail"
    fi
fi
echo "" >> "$RESULTS"

#--- Plugin Validation ---
echo "## Plugin Validation" >> "$RESULTS"
if [ -f "$TEST_DIR/.claude-plugin/plugin.json" ]; then
    echo "--- Plugin Validation ---"

    # Check plugin.json
    jq -e '.name and .description' "$TEST_DIR/.claude-plugin/plugin.json" > /dev/null 2>&1 && \
        test_result "plugin.json valid" "pass" || test_result "plugin.json valid" "fail"

    # Check commands
    if [ -d "$TEST_DIR/commands" ] && ls "$TEST_DIR/commands"/*.md > /dev/null 2>&1; then
        VALID=true
        for cmd in "$TEST_DIR/commands"/*.md; do
            grep -q "^description:" "$cmd" || VALID=false
        done
        [[ "$VALID" == "true" ]] && test_result "Commands have frontmatter" "pass" || test_result "Commands have frontmatter" "fail"
    fi

    # Check skills
    if [ -d "$TEST_DIR/skills" ]; then
        VALID=true
        for skill in "$TEST_DIR/skills"/*/; do
            [ -f "${skill}SKILL.md" ] || VALID=false
        done
        [[ "$VALID" == "true" ]] && test_result "Skills structured correctly" "pass" || test_result "Skills structured correctly" "fail"
    fi
fi
echo "" >> "$RESULTS"

#--- Agent Validation ---
echo "## Agent Validation" >> "$RESULTS"
if [ -d "$TEST_DIR/agents" ] && ls "$TEST_DIR/agents"/*.md > /dev/null 2>&1; then
    echo "--- Agent Validation ---"

    VALID=true
    for agent in "$TEST_DIR/agents"/*.md; do
        grep -q "^description:" "$agent" || VALID=false
    done
    [[ "$VALID" == "true" ]] && test_result "Agents have descriptions" "pass" || test_result "Agents have descriptions" "fail"

    VALID=true
    for agent in "$TEST_DIR/agents"/*.md; do
        # Accept either 'tools:' or 'allowed-tools:' (both are valid for agents)
        grep -qE "^(tools|allowed-tools):" "$agent" || VALID=false
    done
    [[ "$VALID" == "true" ]] && test_result "Agents have tool lists" "pass" || test_result "Agents have tool lists" "fail"
fi
echo "" >> "$RESULTS"

#--- Summary ---
TOTAL=$((PASS + FAIL))
echo ""
echo "================================"
echo "  Summary: $PASS / $TOTAL passed"
echo "================================"

echo "## Summary" >> "$RESULTS"
echo "- **Passed:** $PASS / $TOTAL" >> "$RESULTS"
echo "- **Failed:** $FAIL / $TOTAL" >> "$RESULTS"
echo "" >> "$RESULTS"

if [ $FAIL -eq 0 ]; then
    echo "**Status: ALL TESTS PASSED** ✅" >> "$RESULTS"
else
    echo "**Status: SOME TESTS FAILED** ❌" >> "$RESULTS"
fi

echo ""
echo "Results saved to: $RESULTS"
SCRIPT
    chmod +x "$DIR/run-tests.sh"
}

#######################################
# Main
#######################################
case "$TYPE" in
    hook)
        create_hook_tests "$OUTPUT_DIR"
        ;;
    plugin)
        create_plugin_tests "$OUTPUT_DIR"
        ;;
    agent)
        create_agent_tests "$OUTPUT_DIR"
        ;;
    full|*)
        create_hook_tests "$OUTPUT_DIR"
        create_plugin_tests "$OUTPUT_DIR"
        create_agent_tests "$OUTPUT_DIR"
        ;;
esac

create_test_runner "$OUTPUT_DIR"

#######################################
# Add YAML Tests and Python Runner
#######################################
add_advanced_testing() {
    local DIR="$1"
    local SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

    # Create tests directory
    mkdir -p "$DIR/tests"

    # Copy YAML test cases if available
    if [ -f "$SCRIPT_DIR/tests/hook-tests.yaml" ]; then
        cp "$SCRIPT_DIR/tests/hook-tests.yaml" "$DIR/tests/"
    else
        # Generate default YAML
        cat > "$DIR/tests/hook-tests.yaml" << 'YAML'
version: "1.0"
description: "Auto-generated test cases"

settings:
  timeout: 10

test_cases:
  - name: "Block dangerous rm"
    event: "PreToolUse"
    hook_pattern: "pretooluse*.sh"
    input:
      hook_event_name: "PreToolUse"
      tool_name: "Bash"
      tool_input: {command: "rm -rf /"}
    expect:
      output_contains: "deny"

  - name: "Auto-allow safe command"
    event: "PreToolUse"
    hook_pattern: "pretooluse*.sh"
    input:
      hook_event_name: "PreToolUse"
      tool_name: "Bash"
      tool_input: {command: "echo hello"}
    expect:
      output_contains: "allow"
YAML
    fi

    # Copy Python test runner if available
    if [ -f "$SCRIPT_DIR/test-runner.py" ]; then
        cp "$SCRIPT_DIR/test-runner.py" "$DIR/"
        chmod +x "$DIR/test-runner.py"
    fi

    # Create wrapper script for Python runner
    cat > "$DIR/run-advanced-tests.sh" << 'SCRIPT'
#!/bin/bash
# Advanced Test Runner (YAML + Auto-Discovery)

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found, falling back to basic tests"
    exec "$TEST_DIR/run-tests.sh"
fi

# Check for test-runner.py
if [ -f "$TEST_DIR/test-runner.py" ]; then
    python3 "$TEST_DIR/test-runner.py" "$TEST_DIR" "$TEST_DIR/tests/hook-tests.yaml"
else
    echo "test-runner.py not found, using basic tests"
    exec "$TEST_DIR/run-tests.sh"
fi
SCRIPT
    chmod +x "$DIR/run-advanced-tests.sh"
}

add_advanced_testing "$OUTPUT_DIR"

#######################################
# Add E2E Test Support
#######################################
add_e2e_testing() {
    local DIR="$1"
    local SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

    # Copy E2E test runner if available
    if [ -f "$SCRIPT_DIR/e2e-test-runner.py" ]; then
        cp "$SCRIPT_DIR/e2e-test-runner.py" "$DIR/"
        chmod +x "$DIR/e2e-test-runner.py"
    fi

    # Copy E2E test YAML if available
    if [ -f "$SCRIPT_DIR/e2e-tests.yaml" ]; then
        cp "$SCRIPT_DIR/e2e-tests.yaml" "$DIR/tests/"
    else
        # Generate sample E2E tests
        cat > "$DIR/tests/e2e-tests.yaml" << 'YAML'
version: "1.0"
description: "E2E Tests using Claude CLI"

settings:
  model: haiku
  max_budget_usd: 0.50
  timeout: 60

e2e_tests:
  - name: "CLI responds to simple prompt"
    prompt: "Say 'hello' and nothing else"
    expect:
      - contains: "hello"
      - exit_success: true
    timeout: 30

  - name: "Bash tool execution"
    prompt: "Run: echo 'E2E_TEST_MARKER'"
    allowed_tools: ["Bash"]
    expect:
      - tool_used: "Bash"
      - contains: "E2E_TEST_MARKER"
YAML
    fi

    # Create E2E wrapper script
    cat > "$DIR/run-e2e-tests.sh" << 'SCRIPT'
#!/bin/bash
# E2E Test Runner - Uses actual Claude CLI (API costs apply!)

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "================================"
echo "  Claude Code E2E Tests"
echo "================================"
echo "⚠️  This runs real API calls. Costs apply!"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 required"
    exit 1
fi

# Check for Claude CLI
if ! command -v claude &> /dev/null; then
    echo "Error: claude CLI not found"
    exit 1
fi

# Default options
MODEL="${1:-haiku}"
BUDGET="${2:-0.50}"

echo "Model: $MODEL"
echo "Max Budget: \$$BUDGET"
echo ""

read -p "Run E2E tests? (y/N) " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

python3 "$TEST_DIR/e2e-test-runner.py" \
    "$TEST_DIR/tests/e2e-tests.yaml" \
    --plugin-dir "$TEST_DIR" \
    --model "$MODEL" \
    --max-budget "$BUDGET"
SCRIPT
    chmod +x "$DIR/run-e2e-tests.sh"
}

add_e2e_testing "$OUTPUT_DIR"

echo ""
echo "================================"
echo "Test environment created!"
echo "Directory: $OUTPUT_DIR"
echo ""
echo "To run tests:"
echo "  Basic:    cd $OUTPUT_DIR && ./run-tests.sh"
echo "  Advanced: cd $OUTPUT_DIR && ./run-advanced-tests.sh"
echo "  E2E:      cd $OUTPUT_DIR && ./run-e2e-tests.sh [model] [budget]"
echo ""
echo "Test files:"
echo "  - tests/hook-tests.yaml (YAML definitions)"
echo "  - tests/e2e-tests.yaml (E2E test definitions)"
echo "  - test-runner.py (Hook test runner)"
echo "  - e2e-test-runner.py (E2E test runner)"
echo "================================"
