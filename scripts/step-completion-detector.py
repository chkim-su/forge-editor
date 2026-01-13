#!/usr/bin/env python3
"""
Step Completion Detector - Auto-advance step on completion triggers.

PostToolUse hook that detects when step completion triggers are satisfied
and automatically advances to the next step.

Exit Codes:
    0 = Always (PostToolUse hooks don't block)

Trigger Types:
    - task_agent: Task with specific agent pattern completed
    - bash_exit_code: Bash command with specific exit code
    - bash_pattern: Bash command containing pattern
    - validation_passed: Daemon validation status is "passed"
    - task_complete: Any Task tool completion
    - manual: Only advances via explicit CLI command

Usage (called by hooks via stdin):
    echo '{"tool_name": "Task", "tool_input": {...}, "tool_response": {...}}' | python3 step-completion-detector.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPTS_DIR = Path(__file__).parent
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", SCRIPTS_DIR.parent))
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
CONFIG_FILE = PLUGIN_ROOT / "config" / "step-definitions.json"

# Patterns indicating pass/success in Task output
PASS_PATTERNS = [
    "pass", "passed", "success", "successful",
    "appropriate", "recommended", "correctly",
    "all tests passed", "validation passed",
    "compliant", "approved", "complete"
]

FAIL_PATTERNS = [
    "fail", "failed", "error", "violation",
    "rejected", "inappropriate", "incorrect"
]

# =============================================================================
# STEP DEFINITIONS LOADING
# =============================================================================

_step_definitions_cache = None


def load_step_definitions() -> dict:
    """Load step definitions from config file."""
    global _step_definitions_cache

    if _step_definitions_cache is not None:
        return _step_definitions_cache

    if not CONFIG_FILE.exists():
        return {"commands": {}, "global_settings": {}}

    try:
        with open(CONFIG_FILE) as f:
            _step_definitions_cache = json.load(f)
            return _step_definitions_cache
    except (json.JSONDecodeError, IOError):
        return {"commands": {}, "global_settings": {}}


def get_command_from_workflow(workflow_type: str) -> str | None:
    """Map workflow_type back to command name."""
    defs = load_step_definitions()
    for cmd, config in defs.get("commands", {}).items():
        if config.get("workflow_type") == workflow_type:
            return cmd
    return None


def get_step_definition(workflow_type: str, step_number: int) -> dict | None:
    """Get step definition for a workflow at a specific step."""
    defs = load_step_definitions()

    for cmd, config in defs.get("commands", {}).items():
        if config.get("workflow_type") == workflow_type:
            steps = config.get("steps", [])
            for step in steps:
                if step.get("step_number") == step_number:
                    return step
            break

    return None


def get_total_steps(workflow_type: str) -> int:
    """Get total number of steps for a workflow."""
    defs = load_step_definitions()

    for cmd, config in defs.get("commands", {}).items():
        if config.get("workflow_type") == workflow_type:
            return len(config.get("steps", []))

    return 0


# =============================================================================
# DAEMON COMMUNICATION
# =============================================================================

def run_daemon_cmd(*args) -> dict:
    """Run daemon command and return parsed response."""
    daemon_path = SCRIPTS_DIR / "forge-state-daemon.py"

    if not daemon_path.exists():
        return {"status": "error", "message": "daemon not found"}

    cmd = ["python3", str(daemon_path)] + [str(a) for a in args]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_DIR),
            timeout=5,
        )
        if result.stdout:
            return json.loads(result.stdout)
        return {"status": "error", "message": "no output"}
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"status": "error", "message": str(e)}


def get_session_id() -> str:
    """Get session ID from environment."""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not session_id:
        session_id = f"s{abs(hash(str(PROJECT_DIR))) % 100000:05d}"
    return session_id


# =============================================================================
# COMPLETION TRIGGER CHECKERS
# =============================================================================

def check_task_agent_trigger(trigger: dict, tool_name: str, tool_input: dict, tool_output: str) -> bool:
    """Check if Task with specific agent pattern completed."""
    if tool_name != "Task":
        return False

    agent_pattern = trigger.get("agent_pattern", "").lower()
    if not agent_pattern:
        return False

    # Check subagent_type and prompt for pattern
    subagent = (tool_input.get("subagent_type", "") or "").lower()
    prompt = (tool_input.get("prompt", "") or "").lower()

    pattern_found = agent_pattern in subagent or agent_pattern in prompt

    if not pattern_found:
        return False

    # Check if require_pass
    if trigger.get("require_pass", False):
        output_lower = tool_output.lower()

        # Check for fail patterns first
        if any(p in output_lower for p in FAIL_PATTERNS):
            return False

        # Check for pass patterns
        return any(p in output_lower for p in PASS_PATTERNS)

    return True


def check_bash_exit_code_trigger(trigger: dict, tool_name: str, tool_input: dict, tool_output: str) -> bool:
    """Check if Bash command with specific exit code completed."""
    if tool_name != "Bash":
        return False

    command_pattern = trigger.get("command_pattern", "")
    expected_code = trigger.get("exit_code", 0)

    command = tool_input.get("command", "")

    if command_pattern and command_pattern not in command:
        return False

    # PostToolUse doesn't directly get exit code, but we can infer success
    # from lack of error messages in output
    output_lower = tool_output.lower()

    # If expected code is 0, check for success
    if expected_code == 0:
        # Check for error indicators
        error_indicators = ["error", "failed", "exception", "traceback"]
        if any(e in output_lower for e in error_indicators):
            return False
        return True

    return False


def check_bash_pattern_trigger(trigger: dict, tool_name: str, tool_input: dict, tool_output: str) -> bool:
    """Check if Bash command contains pattern."""
    if tool_name != "Bash":
        return False

    pattern = trigger.get("pattern", "")
    if not pattern:
        return False

    command = tool_input.get("command", "")
    return pattern in command


def check_validation_passed_trigger(trigger: dict, tool_name: str, tool_input: dict, tool_output: str) -> bool:
    """Check if daemon validation status is passed."""
    validation_name = trigger.get("validation")
    if not validation_name:
        return False

    session_id = get_session_id()

    # Get workflow type from daemon
    step_resp = run_daemon_cmd("get-command-step", session_id)
    workflow_type = step_resp.get("workflow_type")

    if not workflow_type:
        return False

    # Check validation status
    val_resp = run_daemon_cmd("get-validation", session_id, workflow_type, validation_name)

    return val_resp.get("validation_status") == "passed"


def check_task_complete_trigger(trigger: dict, tool_name: str, tool_input: dict, tool_output: str) -> bool:
    """Check if any Task completed (simple completion)."""
    return tool_name == "Task"


# Trigger checker registry
TRIGGER_CHECKERS = {
    "task_agent": check_task_agent_trigger,
    "bash_exit_code": check_bash_exit_code_trigger,
    "bash_pattern": check_bash_pattern_trigger,
    "validation_passed": check_validation_passed_trigger,
    "task_complete": check_task_complete_trigger,
    # "manual" trigger is not auto-checked
}


# =============================================================================
# COMPLETION DETECTION
# =============================================================================

def check_step_completion(session_id: str, tool_name: str, tool_input: dict, tool_output: str) -> dict:
    """
    Check if current step's completion triggers are satisfied.

    Returns:
        {"advance": True, "step_name": "...", ...} or {"advance": False}
    """
    # Get current step from daemon
    step_resp = run_daemon_cmd("get-command-step", session_id)

    if step_resp.get("status") == "error":
        return {"advance": False, "reason": "daemon_error"}

    workflow_type = step_resp.get("workflow_type")
    if not workflow_type:
        return {"advance": False, "reason": "no_active_workflow"}

    current_step = step_resp.get("step", 1)

    # Load step definition
    step_def = get_step_definition(workflow_type, current_step)

    if not step_def:
        return {"advance": False, "reason": "no_step_definition"}

    # Check each trigger
    triggers = step_def.get("completion_triggers", [])

    for trigger in triggers:
        trigger_type = trigger.get("type")

        if trigger_type == "manual":
            # Manual triggers are never auto-checked
            continue

        checker = TRIGGER_CHECKERS.get(trigger_type)

        if checker and checker(trigger, tool_name, tool_input, tool_output):
            return {
                "advance": True,
                "trigger_type": trigger_type,
                "workflow_type": workflow_type,
                "current_step": current_step,
                "step_name": step_def.get("name"),
                "command": get_command_from_workflow(workflow_type),
            }

    return {"advance": False}


def advance_step(session_id: str) -> dict:
    """Advance to next step via daemon."""
    return run_daemon_cmd("advance-command-step", session_id)


# =============================================================================
# OUTPUT
# =============================================================================

def print_advance_message(result: dict, new_step: int):
    """Print step advancement message."""
    command = result.get("command", "Unknown")
    prev_step = result.get("current_step", 0)
    step_name = result.get("step_name", "Unknown")
    workflow_type = result.get("workflow_type")
    total_steps = get_total_steps(workflow_type) if workflow_type else 0

    # Get new step definition for guidance
    new_step_def = get_step_definition(workflow_type, new_step) if workflow_type else None

    print(f"[STEP] Advanced from step {prev_step} ({step_name}) to step {new_step}/{total_steps}")

    if new_step_def:
        new_name = new_step_def.get("name", "Unknown")
        new_desc = new_step_def.get("description", "")
        allowed = new_step_def.get("allowed_tools", [])

        print(f"[STEP] New step: {new_name}")
        if new_desc:
            print(f"[STEP] Description: {new_desc}")
        if allowed:
            print(f"[STEP] Allowed tools: {', '.join(allowed)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    # Read hook input from stdin
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        input_data = {}

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Get tool output from tool_response
    tool_response = input_data.get("tool_response", {})
    tool_output = tool_response.get("output", "") if isinstance(tool_response, dict) else str(tool_response)

    session_id = get_session_id()

    # Check for step completion
    result = check_step_completion(session_id, tool_name, tool_input, tool_output)

    if result.get("advance"):
        # Advance step
        advance_resp = advance_step(session_id)

        if advance_resp.get("status") == "ok":
            new_step = advance_resp.get("current_step", 0)
            print_advance_message(result, new_step)

    # PostToolUse hooks always exit 0
    sys.exit(0)


if __name__ == "__main__":
    main()
