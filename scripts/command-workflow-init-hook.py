#!/usr/bin/env python3
"""
Command-to-Workflow Init Hook (UserPromptSubmit)

Command 실행 시 workflow stack의 root를 초기화.
Routing은 나중에 push-workflow로 nested workflow 추가.

Usage:
    echo '{"prompt": "/wizard"}' | python3 command-workflow-init-hook.py

Workflow Stack Model:
    - Command triggers root workflow push
    - Routing can push nested workflows
    - Pop returns to parent workflow
"""

import sys
import json
import os
import re
import subprocess
from pathlib import Path

# =============================================================================
# COMMAND TO WORKFLOW MAPPING
# =============================================================================

COMMAND_TO_WORKFLOW = {
    # Commands that trigger workflow initialization
    "wizard": "wizard_routing",
    "validate-full": "quick_fix",
    "validate-plugin": "plugin_publish",
    "diagnose": "analyze_only",
    "run-tests": "quick_fix",
    "test-env": "quick_fix",

    # No-workflow commands (always allowed, no state change)
    "skills": None,
    "load": None,
    "suggest": None,
}

# Commands that should never trigger workflow init
NO_WORKFLOW_COMMANDS = {"skills", "load", "suggest"}

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPTS_DIR = Path(__file__).parent
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", SCRIPTS_DIR.parent))
STEP_DEFS_FILE = PLUGIN_ROOT / "config" / "step-definitions.json"


# =============================================================================
# STEP DEFINITIONS LOADING
# =============================================================================

def load_step_definitions() -> dict:
    """Load step definitions from config file."""
    if not STEP_DEFS_FILE.exists():
        return {"commands": {}, "global_settings": {}}

    try:
        with open(STEP_DEFS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"commands": {}, "global_settings": {}}


def get_first_step_info(workflow_type: str) -> dict | None:
    """Get info about the first step of a workflow."""
    defs = load_step_definitions()
    for cmd, config in defs.get("commands", {}).items():
        if config.get("workflow_type") == workflow_type:
            steps = config.get("steps", [])
            if steps:
                return steps[0]
    return None

# Regex to detect slash commands: /wizard, /forge-editor:wizard, etc.
COMMAND_PATTERN = re.compile(
    r"/(?:forge-editor:)?(\w+[-\w]*)",
    re.IGNORECASE
)


# =============================================================================
# DAEMON CLIENT
# =============================================================================

def run_daemon_cmd(*args) -> dict:
    """
    Run daemon command and return parsed response.

    Falls back gracefully if daemon unavailable.
    """
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
        # Graceful degradation
        return {"status": "error", "message": str(e)}


# =============================================================================
# COMMAND DETECTION
# =============================================================================

def detect_command(prompt: str) -> str | None:
    """
    Detect slash command in user prompt.

    Returns command name (lowercase) or None if not a command.
    """
    prompt = prompt.strip()
    match = COMMAND_PATTERN.match(prompt)
    if match:
        return match.group(1).lower()
    return None


def get_workflow_for_command(command: str) -> str | None:
    """
    Get workflow type for a command.

    Returns None for no-workflow commands.
    """
    if command in NO_WORKFLOW_COMMANDS:
        return None
    return COMMAND_TO_WORKFLOW.get(command)


# =============================================================================
# MAIN HANDLER
# =============================================================================

def handle_user_prompt_submit(input_data: dict):
    """Main UserPromptSubmit handler."""
    prompt = input_data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    # Detect command
    command = detect_command(prompt)
    if not command:
        sys.exit(0)  # Not a slash command

    # Get workflow for this command
    target_workflow = get_workflow_for_command(command)

    if target_workflow is None:
        # No-workflow command, always allowed
        sys.exit(0)

    # Get session context
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")

    # Check current stack
    stack_resp = run_daemon_cmd("get-workflow-stack", session_id)
    stack = stack_resp.get("stack", [])

    if len(stack) == 0:
        # Empty stack → push root workflow
        resp = run_daemon_cmd("push-workflow", session_id, target_workflow)
        if resp.get("status") == "ok":
            # Initialize step counter to 1
            run_daemon_cmd("set-command-step", session_id, "1")

            # Get step info for guidance
            step_info = get_first_step_info(target_workflow)
            step_guidance = ""
            if step_info:
                step_name = step_info.get("name", "init")
                step_desc = step_info.get("description", "")
                allowed_tools = step_info.get("allowed_tools", [])
                step_guidance = f"""
### Current Step: 1 ({step_name})
{step_desc}

**Allowed tools**: {', '.join(allowed_tools) if allowed_tools else 'All'}
"""

            print(json.dumps({
                "additionalContext": f"""## Workflow Started: {target_workflow}

Stack depth: 1
{step_guidance}
Status: `python3 scripts/forge-state.py status`
"""
            }))
        sys.exit(0)

    # Stack not empty - check root workflow
    root_workflow = stack[0].get("workflow_type")

    if root_workflow != target_workflow:
        # Different root workflow → BLOCK
        current_depth = len(stack)
        active_workflow = stack[-1].get("workflow_type") if stack else None

        print(json.dumps({
            "additionalContext": f"""## ⛔ WORKFLOW CONFLICT

**Current root**: {root_workflow}
**Active workflow**: {active_workflow} (depth: {current_depth})
**Requested**: {target_workflow}

Complete or reset current workflow first.

**Options:**
1. Complete current workflow
2. Reset: `python3 scripts/forge-state.py reset`
3. Use no-workflow commands: /skills, /load, /suggest
"""
        }))
        sys.exit(2)  # BLOCK

    # Same root workflow, continue
    sys.exit(0)


def main():
    """Main entry point."""
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    handle_user_prompt_submit(input_data)


if __name__ == "__main__":
    main()
