#!/bin/bash
# Forge E2E Test Entry Point with tmux
# Sets up isolated test environment and runs tests

set -euo pipefail

SESSION="forge-test"
WORKSPACE="/workspace/test"
FORGE_ROOT="/workspace/forge"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Initialize test workspace
init_workspace() {
    log_info "Initializing test workspace..."
    mkdir -p "$WORKSPACE/.claude/local"
    
    # Set environment
    export CLAUDE_WORKING_DIR="$WORKSPACE"
    export CLAUDE_PLUGIN_ROOT="$FORGE_ROOT"
    
    log_info "Workspace: $WORKSPACE"
    log_info "Plugin root: $FORGE_ROOT"
}

# Run workflow tests in headless mode (no tmux)
run_headless() {
    log_info "Running E2E workflow tests in headless mode..."
    
    # Start daemon in background
    log_info "Starting forge daemon..."
    python3 "$FORGE_ROOT/scripts/forge-daemon.py" "$WORKSPACE" &
    DAEMON_PID=$!
    
    # Wait for daemon to start
    sleep 2
    
    # Check daemon is running
    if ! kill -0 $DAEMON_PID 2>/dev/null; then
        log_error "Daemon failed to start"
        exit 1
    fi
    log_info "Daemon started (PID: $DAEMON_PID)"
    
    # Run test suite
    log_info "Running workflow test suite..."
    python3 "$FORGE_ROOT/tests/e2e-docker-test.py"
    TEST_RESULT=$?
    
    # Cleanup
    log_info "Stopping daemon..."
    kill $DAEMON_PID 2>/dev/null || true
    wait $DAEMON_PID 2>/dev/null || true
    
    if [[ $TEST_RESULT -eq 0 ]]; then
        log_info "All workflow tests passed!"
    else
        log_error "Workflow tests failed with exit code: $TEST_RESULT"
    fi
    
    exit $TEST_RESULT
}

# Run schema validation tests
run_schema_tests() {
    log_info "Running schema validation E2E tests..."
    
    # No daemon needed for schema tests
    python3 "$FORGE_ROOT/tests/e2e-schema-validation.py" --verbose
    TEST_RESULT=$?
    
    if [[ $TEST_RESULT -eq 0 ]]; then
        log_info "All schema validation tests passed!"
    else
        log_error "Schema validation tests failed with exit code: $TEST_RESULT"
    fi
    
    exit $TEST_RESULT
}

# Run refactor plugin E2E test (tmux-based interactive)
run_refactor_plugin_test() {
    log_info "Running Refactor Plugin E2E Test..."
    
    # Kill existing session if present
    tmux kill-session -t refactor-test 2>/dev/null || true
    
    # Create tmux session
    tmux new-session -d -s refactor-test -x 200 -y 50
    
    # Set up environment
    tmux send-keys -t refactor-test "export CLAUDE_WORKING_DIR=$WORKSPACE" C-m
    tmux send-keys -t refactor-test "export CLAUDE_PLUGIN_ROOT=$FORGE_ROOT" C-m
    tmux send-keys -t refactor-test "cd $WORKSPACE" C-m
    sleep 1
    
    # Start daemon in background
    log_info "Starting forge daemon..."
    python3 "$FORGE_ROOT/scripts/forge-daemon.py" "$WORKSPACE" &
    DAEMON_PID=$!
    sleep 2
    
    if ! kill -0 $DAEMON_PID 2>/dev/null; then
        log_error "Daemon failed to start"
        exit 1
    fi
    
    # Launch mock Claude in tmux
    tmux send-keys -t refactor-test "claude" C-m
    sleep 3
    
    # Send test prompt
    log_info "Sending test prompt..."
    tmux send-keys -t refactor-test "I want to make a refactor plugin. The plugin will be designed and executed inside a Docker container." C-m
    
    # Wait for response
    log_info "Waiting for response..."
    sleep 10
    
    # Capture output
    OUTPUT=$(tmux capture-pane -t refactor-test -p -S -200)
    
    # Provide clarification if needed
    if echo "$OUTPUT" | grep -qi "?"; then
        log_info "Providing clarification responses..."
        
        sleep 2
        tmux send-keys -t refactor-test "The plugin is intended to support refactoring workflows in general. The specific refactor target and strategy are intentionally undefined." C-m
        sleep 5
        
        tmux send-keys -t refactor-test "The plugin should be advisory by default. It must not perform automatic file modifications unless explicitly instructed." C-m
        sleep 5
        
        tmux send-keys -t refactor-test "The plugin must assume a Docker-based, ephemeral runtime. Any required state must be explicitly materialized as artifacts inside the container." C-m
        sleep 5
    fi
    
    # Capture final output
    FINAL_OUTPUT=$(tmux capture-pane -t refactor-test -p -S -500)
    
    # Save output
    echo "$FINAL_OUTPUT" > "$WORKSPACE/refactor-plugin-test-output.txt"
    log_info "Output saved to $WORKSPACE/refactor-plugin-test-output.txt"
    
    # Run validation
    log_info "Running validation..."
    python3 "$FORGE_ROOT/tests/e2e-refactor-plugin-test.py"
    TEST_RESULT=$?
    
    # Cleanup
    log_info "Cleaning up..."
    tmux kill-session -t refactor-test 2>/dev/null || true
    kill $DAEMON_PID 2>/dev/null || true
    
    if [[ $TEST_RESULT -eq 0 ]]; then
        log_info "Refactor Plugin E2E Test PASSED!"
    else
        log_error "Refactor Plugin E2E Test FAILED!"
    fi
    
    exit $TEST_RESULT
}

# Run all tests (workflow + schema)
run_all_tests() {
    log_info "Running full test suite (workflow + schema)..."
    
    local OVERALL_RESULT=0
    
    # Run schema validation tests first (no daemon needed)
    log_info "=== Schema Validation Tests ==="
    python3 "$FORGE_ROOT/tests/e2e-schema-validation.py" --verbose
    SCHEMA_RESULT=$?
    
    if [[ $SCHEMA_RESULT -ne 0 ]]; then
        log_error "Schema validation tests failed!"
        OVERALL_RESULT=1
    else
        log_info "Schema validation tests passed!"
    fi
    
    echo ""
    log_info "=== Workflow Tests ==="
    
    # Start daemon for workflow tests
    log_info "Starting forge daemon..."
    python3 "$FORGE_ROOT/scripts/forge-daemon.py" "$WORKSPACE" &
    DAEMON_PID=$!
    sleep 2
    
    if ! kill -0 $DAEMON_PID 2>/dev/null; then
        log_error "Daemon failed to start"
        exit 1
    fi
    
    # Run workflow tests
    python3 "$FORGE_ROOT/tests/e2e-docker-test.py"
    WORKFLOW_RESULT=$?
    
    # Cleanup daemon
    kill $DAEMON_PID 2>/dev/null || true
    wait $DAEMON_PID 2>/dev/null || true
    
    if [[ $WORKFLOW_RESULT -ne 0 ]]; then
        log_error "Workflow tests failed!"
        OVERALL_RESULT=1
    else
        log_info "Workflow tests passed!"
    fi
    
    # Final summary
    echo ""
    log_info "=== Final Summary ==="
    if [[ $OVERALL_RESULT -eq 0 ]]; then
        log_info "All tests passed!"
    else
        log_error "Some tests failed!"
        [[ $SCHEMA_RESULT -ne 0 ]] && log_error "  - Schema validation tests: FAILED"
        [[ $WORKFLOW_RESULT -ne 0 ]] && log_error "  - Workflow tests: FAILED"
    fi
    
    exit $OVERALL_RESULT
}

# Run tests in interactive tmux mode
run_interactive() {
    log_info "Running E2E tests in interactive tmux mode..."
    
    # Kill existing session if present
    tmux kill-session -t $SESSION 2>/dev/null || true
    
    # Create new tmux session
    tmux new-session -d -s $SESSION -n "main" -x 200 -y 50
    
    # Split into panes:
    # Pane 0 (top-left): Forge daemon
    # Pane 1 (top-right): Test runner
    # Pane 2 (bottom): Interactive shell
    
    tmux split-window -h -t $SESSION:0
    tmux split-window -v -t $SESSION:0.0
    
    # Set up environment in all panes
    for pane in 0 1 2; do
        tmux send-keys -t $SESSION:0.$pane "export CLAUDE_WORKING_DIR=$WORKSPACE" C-m
        tmux send-keys -t $SESSION:0.$pane "export CLAUDE_PLUGIN_ROOT=$FORGE_ROOT" C-m
        tmux send-keys -t $SESSION:0.$pane "cd $WORKSPACE" C-m
    done
    
    # Pane 0: Start daemon
    tmux send-keys -t $SESSION:0.0 "echo '=== Forge Daemon ===' && python3 $FORGE_ROOT/scripts/forge-daemon.py $WORKSPACE" C-m
    
    # Wait for daemon
    sleep 2
    
    # Pane 1: Run tests
    tmux send-keys -t $SESSION:0.1 "echo '=== Test Runner ===' && sleep 1 && python3 $FORGE_ROOT/tests/e2e-docker-test.py" C-m
    
    # Pane 2: Interactive shell for debugging
    tmux send-keys -t $SESSION:0.2 "echo '=== Interactive Shell ===' && echo 'Forge commands available:'" C-m
    tmux send-keys -t $SESSION:0.2 "echo '  python3 \$CLAUDE_PLUGIN_ROOT/scripts/forge-state.py get'" C-m
    tmux send-keys -t $SESSION:0.2 "echo '  python3 \$CLAUDE_PLUGIN_ROOT/scripts/forge-state.py activate'" C-m
    tmux send-keys -t $SESSION:0.2 "echo '  claude help'" C-m
    
    # Attach to session
    tmux attach-session -t $SESSION
}

# Main
main() {
    init_workspace
    
    # Check for mode argument
    local mode="${1:-headless}"
    
    case "$mode" in
        "headless"|"-h"|"--headless")
            run_headless
            ;;
        "interactive"|"-i"|"--interactive")
            run_interactive
            ;;
        "tmux")
            run_interactive
            ;;
        "schema"|"schema-tests")
            run_schema_tests
            ;;
        "all"|"all-tests"|"full")
            run_all_tests
            ;;
        "refactor-plugin-test"|"refactor-plugin")
            run_refactor_plugin_test
            ;;
        *)
            log_error "Unknown mode: $mode"
            echo "Usage: entrypoint.sh [headless|interactive|tmux|schema|all|refactor-plugin-test]"
            echo ""
            echo "Modes:"
            echo "  headless             - Run workflow tests (default)"
            echo "  interactive          - Run tests in tmux (for debugging)"
            echo "  schema               - Run schema validation tests"
            echo "  all                  - Run all tests (schema + workflow)"
            echo "  refactor-plugin-test - Run refactor plugin E2E test"
            exit 1
            ;;
    esac
}

main "$@"
