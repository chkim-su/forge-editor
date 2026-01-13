#!/usr/bin/env python3
"""
Step Validation Gate - Per-command step enforcement hook.

PreToolUse hook that blocks tools not allowed in the current step of the
active command workflow. Each command has its own step definitions loaded
from config/step-definitions.json.

Exit Codes:
    0 = ALLOW tool execution
    2 = BLOCK tool execution (step violation)

Usage (called by hooks via stdin):
    echo '{"tool_name": "Write", "tool_input": {...}}' | python3 step-validation-gate.py
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

# Tools always allowed regardless of step
ALWAYS_ALLOWED_TOOLS = {"TodoWrite", "WebSearch", "WebFetch", "AskUserQuestion"}

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

    # Find command by workflow type
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
# TOOL PERMISSION CHECKING
# =============================================================================

def check_tool_permission(session_id: str, tool_name: str, tool_input: dict) -> dict:
    """
    Check if tool is permitted in current step.

    Returns:
        {"allowed": True} or {"allowed": False, "reason": "...", ...}
    """
    # Always allowed tools
    defs = load_step_definitions()
    global_always = set(defs.get("global_settings", {}).get("always_allowed_tools", []))

    if tool_name in ALWAYS_ALLOWED_TOOLS or tool_name in global_always:
        return {"allowed": True, "reason": "always_allowed"}

    # Get current step from daemon
    step_resp = run_daemon_cmd("get-command-step", session_id)

    if step_resp.get("status") == "error":
        # Daemon error - graceful degradation (allow)
        return {"allowed": True, "warning": "daemon unavailable"}

    workflow_type = step_resp.get("workflow_type")
    if not workflow_type:
        # No active workflow
        return {"allowed": True, "reason": "no_active_workflow"}

    current_step = step_resp.get("step", 1)

    # Load step definition
    step_def = get_step_definition(workflow_type, current_step)

    if not step_def:
        # No step definition found - allow
        return {"allowed": True, "reason": "no_step_definition"}

    allowed_tools = step_def.get("allowed_tools", [])

    # Check if tool is in allowed list
    if tool_name in allowed_tools:
        return {"allowed": True}

    # Special handling for Bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        allowed_patterns = step_def.get("allowed_bash_patterns", [])

        for pattern in allowed_patterns:
            if pattern in command:
                return {"allowed": True, "reason": "bash_pattern_match"}

    # Tool not allowed
    command_name = get_command_from_workflow(workflow_type)
    total_steps = get_total_steps(workflow_type)

    return {
        "allowed": False,
        "tool_name": tool_name,
        "workflow_type": workflow_type,
        "command": command_name,
        "current_step": current_step,
        "total_steps": total_steps,
        "step_name": step_def.get("name"),
        "step_description": step_def.get("description"),
        "allowed_tools": allowed_tools,
        "reason": f"Tool '{tool_name}' not allowed in step {current_step} ({step_def.get('name')})"
    }


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def print_block_message(result: dict):
    """Print formatted block message to stderr."""
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("STEP VIOLATION - TOOL BLOCKED", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("", file=sys.stderr)

    command = result.get("command", "Unknown")
    current_step = result.get("current_step", "?")
    total_steps = result.get("total_steps", "?")
    step_name = result.get("step_name", "Unknown")
    tool_name = result.get("tool_name", "Unknown")

    print(f"  Command: /{command}", file=sys.stderr)
    print(f"  Current Step: {current_step}/{total_steps} ({step_name})", file=sys.stderr)
    print(f"  Blocked Tool: {tool_name}", file=sys.stderr)
    print("", file=sys.stderr)

    allowed = result.get("allowed_tools", [])
    if allowed:
        print("  Allowed tools for this step:", file=sys.stderr)
        for tool in allowed:
            print(f"    - {tool}", file=sys.stderr)
        print("", file=sys.stderr)

    description = result.get("step_description")
    if description:
        print(f"  Step description: {description}", file=sys.stderr)
        print("", file=sys.stderr)

    print("  Complete this step's requirements to advance.", file=sys.stderr)
    print("  Status: python3 scripts/forge-state.py step-status", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


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
    session_id = get_session_id()

    # Check permission
    result = check_tool_permission(session_id, tool_name, tool_input)

    if not result.get("allowed", True):
        print_block_message(result)
        sys.exit(2)  # BLOCK

    # ALLOW
    sys.exit(0)


if __name__ == "__main__":
    main()
