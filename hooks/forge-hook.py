#!/usr/bin/env python3
"""
Forge Unified Hook - Handles all forge workflow events.

CRITICAL: This hook is COMPLETELY PASSIVE unless forge is explicitly activated
for the current workspace. It never creates files, starts daemons, or modifies
state unless forge_active=true in the state file for THIS workspace.

Called with event type as first argument:
  session-start  - Check if forge is active (read-only)
  pre-tool       - Block dangerous tools in strict phases
  post-tool      - Detect agent execution, record checkpoint
  user-prompt    - Detect confirmation signals
  stop           - Auto-validate on session end

Reads hook input from stdin (JSON).
Outputs hook response to stdout (JSON).
"""

import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

# Phase configuration (6 phases with Preview)
PHASES = {
    0: {"name": "Input", "agent": "forge:input-agent"},
    1: {"name": "Analysis", "agent": "forge:analysis-agent"},
    2: {"name": "Design", "agent": "forge:design-agent"},
    3: {"name": "Preview", "agent": "forge:preview-agent"},
    4: {"name": "Execute", "agent": "forge:execute-agent"},
    5: {"name": "Validate", "agent": "forge:validate-agent"}
}

# Strict phase configuration - blocks dangerous actions
STRICT_PHASES = {
    0: {
        "block": ["Write", "Edit", "Bash"],
        "reason": "Input phase: Gather requirements only, no file modifications allowed"
    },
    2: {
        "block": ["Write", "Edit"],
        "reason": "Design phase: Create design options only, no implementation allowed"
    },
    3: {
        "block": ["Write", "Edit"],
        "reason": "Preview phase: Dry-run only, no file modifications allowed"
    },
    4: {
        "block_unless_confirmed": True,
        "block": ["Write", "Edit", "Bash"],
        "reason": "Execute phase: Requires user confirmation before implementation"
    }
}

# Confirmation patterns for Execute phase
CONFIRM_PATTERNS = [
    r"\byes\b",
    r"\bproceed\b",
    r"\bgo ahead\b",
    r"\bconfirm\b",
    r"\bapproved?\b",
    r"\blgtm\b",
    r"\bdo it\b",
    r"\bexecute\b",
]


def get_workspace_root() -> str:
    """Get workspace root from environment."""
    for var in ["CLAUDE_WORKING_DIR", "PWD"]:
        if var in os.environ:
            return os.environ[var]
    return os.getcwd()


def get_plugin_root() -> str:
    """Get plugin root from environment."""
    return os.environ.get("CLAUDE_PLUGIN_ROOT", str(Path(__file__).parent.parent))


def get_socket_path(workspace_root: str) -> Path:
    """Get socket path for workspace."""
    return Path(workspace_root) / ".claude" / "local" / "forge.sock"


def get_state_file(workspace_root: str) -> Path:
    """Get state file path."""
    return Path(workspace_root) / ".claude" / "local" / "forge-state.json"


def is_forge_active_for_workspace(workspace_root: str) -> bool:
    """
    Check if forge is active for THIS workspace.
    Returns False if:
    - State file doesn't exist
    - State file is invalid JSON
    - forge_active is False
    - workspace_root doesn't match (ownership guard)
    """
    state_file = get_state_file(workspace_root)
    if not state_file.exists():
        return False

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)

        # Check forge_active flag
        if not state.get("forge_active", False):
            return False

        # Ownership guard: workspace must match
        if state.get("workspace_root") != workspace_root:
            return False

        return True
    except (json.JSONDecodeError, IOError, KeyError):
        return False


def read_state_file(workspace_root: str) -> dict:
    """Read state from file. Returns empty dict if not valid."""
    state_file = get_state_file(workspace_root)
    if not state_file.exists():
        return {}
    try:
        with open(state_file, 'r') as f:
            return json.load(f)
    except:
        return {}


def daemon_running(workspace_root: str) -> bool:
    """Check if daemon is running (non-blocking check)."""
    socket_path = get_socket_path(workspace_root)
    if not socket_path.exists():
        return False
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        sock.connect(str(socket_path))
        sock.close()
        return True
    except (socket.error, OSError):
        return False


def send_command(workspace_root: str, command: dict) -> dict:
    """Send command to daemon. Returns error dict on failure."""
    socket_path = get_socket_path(workspace_root)
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(str(socket_path))
        sock.sendall((json.dumps(command) + "\n").encode('utf-8'))

        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        sock.close()
        return json.loads(data.decode('utf-8').strip())
    except Exception as e:
        return {"error": str(e)}


def output_response(decision: str = "approve", message: str = ""):
    """
    Output hook response and exit.
    
    For PreToolUse hooks:
    - "approve": Allow the tool to execute
    - "block": Block the tool with message
    - "modify": Modify tool input (not used here)
    
    For other hooks:
    - "continue": Continue normally
    """
    response = {"decision": decision}
    if message:
        response["message"] = message
    print(json.dumps(response))
    sys.exit(0)


def run_validation(workspace_root: str, target_dir: str = None, fix: bool = False) -> dict:
    """
    Run schema validation script.
    
    Args:
        workspace_root: The workspace directory
        target_dir: Target plugin directory to validate (defaults to workspace_root)
        fix: Whether to attempt auto-fixes
    
    Returns:
        Dict with success status, output, and any errors
    """
    plugin_root = get_plugin_root()
    validate_script = Path(plugin_root) / "scripts" / "schema-validator.py"
    
    if not validate_script.exists():
        # Fallback to legacy script
        validate_script = Path(plugin_root) / "tests" / "validate-plugin.py"
        if not validate_script.exists():
            return {"success": False, "error": "Validation script not found"}
    
    # Determine target directory
    target = target_dir if target_dir else workspace_root
    
    # Build command
    cmd = ["python3", str(validate_script), target, "--json"]
    if fix:
        cmd.append("--fix")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": target}
        )
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            return {
                "success": data.get("is_valid", False),
                "data": data,
                "output": result.stdout,
                "errors": result.stderr
            }
        except json.JSONDecodeError:
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Validation timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_validation_result(validation: dict) -> str:
    """Format validation result for display."""
    if validation.get("success"):
        data = validation.get("data", {})
        summary = data.get("summary", {})
        warnings = summary.get("warning_count", 0)
        fixes = summary.get("fix_count", 0)
        
        msg = "✓ Plugin validation passed"
        if warnings > 0 or fixes > 0:
            parts = []
            if warnings > 0:
                parts.append(f"{warnings} warning(s)")
            if fixes > 0:
                parts.append(f"{fixes} auto-fix(es) applied")
            msg += f" ({', '.join(parts)})"
        return msg
    else:
        error = validation.get("error")
        if error:
            return f"✗ Plugin validation failed: {error}"
        
        # Parse detailed errors from data
        data = validation.get("data", {})
        errors = data.get("errors", [])
        summary = data.get("summary", {})
        
        msg = f"✗ Plugin validation failed ({summary.get('error_count', len(errors))} error(s))"
        
        # Show first few errors
        if errors:
            msg += "\n\nErrors:"
            for err in errors[:3]:
                component = err.get("component", "unknown")
                message = err.get("message", "Unknown error")
                msg += f"\n  • [{component}] {message}"
            
            if len(errors) > 3:
                msg += f"\n  ... and {len(errors) - 3} more"
            
            # Show fixable count
            fixable = summary.get("fixable_count", 0)
            if fixable > 0:
                msg += f"\n\n💡 {fixable} issue(s) can be auto-fixed with schema-validator.py --fix"
        
        return msg


def handle_session_start(hook_input: dict):
    """
    Handle SessionStart event.
    READ-ONLY: Only checks if forge is active, never creates files or starts daemon.
    """
    workspace_root = get_workspace_root()

    # Early exit if forge not active for this workspace
    if not is_forge_active_for_workspace(workspace_root):
        output_response("approve")  # Silent exit

    # Forge is active - show status
    state = read_state_file(workspace_root)
    phase = state.get("phase", 0)
    phase_info = PHASES.get(phase, {})

    output_response(
        "approve",
        f"Forge active - Phase {phase} ({phase_info.get('name', 'Unknown')})"
    )


def handle_pre_tool(hook_input: dict):
    """
    Handle PreToolUse event for strict phase enforcement.
    Can BLOCK dangerous tools in strict phases.
    """
    workspace_root = get_workspace_root()

    # Early exit if forge not active
    if not is_forge_active_for_workspace(workspace_root):
        output_response("approve")

    # Get tool info
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Read current state
    state = read_state_file(workspace_root)
    phase = state.get("phase", 0)
    confirmed = state.get("confirmed", False)

    # Check strict phase rules
    if phase in STRICT_PHASES:
        config = STRICT_PHASES[phase]

        # Check if confirmation is required (Execute phase)
        if config.get("block_unless_confirmed") and not confirmed:
            if tool_name in config.get("block", []):
                output_response(
                    "block",
                    f"⛔ BLOCKED: {config['reason']}\n\n"
                    f"Type 'yes', 'proceed', or 'confirm' to approve execution."
                )

        # Check block list (non-confirmation phases)
        elif not config.get("block_unless_confirmed"):
            if tool_name in config.get("block", []):
                output_response(
                    "block",
                    f"⛔ BLOCKED: {config['reason']}\n\n"
                    f"Complete this phase before modifying files."
                )

    # Allow the tool
    output_response("approve")


def handle_post_tool(hook_input: dict):
    """
    Handle PostToolUse event for Task tool.
    Only processes if forge is active for this workspace.
    """
    workspace_root = get_workspace_root()

    # Early exit if forge not active
    if not is_forge_active_for_workspace(workspace_root):
        output_response("approve")

    # Get tool info
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only process Task tool
    if tool_name != "Task":
        output_response("approve")

    # Check if it's a forge agent
    subagent_type = tool_input.get("subagent_type", "")
    if not subagent_type.startswith("forge:"):
        output_response("approve")

    # Try daemon first, fall back to file
    if daemon_running(workspace_root):
        state = send_command(workspace_root, {"cmd": "get"})
        if "error" in state:
            state = read_state_file(workspace_root)
    else:
        state = read_state_file(workspace_root)

    current_phase = state.get("phase", 0)
    expected_agent = PHASES.get(current_phase, {}).get("agent", "")

    # Check if agent matches current phase
    if subagent_type != expected_agent:
        output_response(
            "approve",
            f"Agent {subagent_type} does not match phase {current_phase} (expected {expected_agent})"
        )

    # Record checkpoint via daemon (requires daemon running)
    if not daemon_running(workspace_root):
        output_response(
            "approve",
            f"Phase {current_phase} agent completed. Run 'forge-state.py checkpoint {subagent_type}' to advance."
        )

    checkpoint_result = send_command(workspace_root, {"cmd": "checkpoint", "agent": subagent_type})

    if checkpoint_result.get("success"):
        if checkpoint_result.get("completed"):
            output_response(
                "approve",
                "✓ Forge workflow completed! Plugin design finished."
            )
        elif checkpoint_result.get("advanced"):
            new_phase = checkpoint_result.get("to_phase", 0)
            guidance = checkpoint_result.get("guidance", "")
            next_step = checkpoint_result.get("next", "")

            if new_phase == 4:
                output_response(
                    "approve",
                    f"✓ Phase {current_phase} complete → Phase {new_phase} (Execute)\n\n"
                    f"{guidance}\n\n"
                    f"⚠️ Preview complete. Type 'yes', 'proceed', or 'confirm' to approve execution."
                )
            else:
                output_response(
                    "approve",
                    f"✓ Phase {current_phase} complete → Phase {new_phase}\n\n"
                    f"{guidance}\n\n"
                    f"Next: {next_step}"
                )
    else:
        error = checkpoint_result.get("error", "Unknown error")
        output_response("approve", f"Checkpoint not recorded: {error}")


def handle_user_prompt(hook_input: dict):
    """
    Handle UserPromptSubmit event for confirmation detection.
    Only processes if forge is active and in Execute phase awaiting confirmation.
    """
    workspace_root = get_workspace_root()

    # Early exit if forge not active
    if not is_forge_active_for_workspace(workspace_root):
        output_response("approve")

    # Read state
    if daemon_running(workspace_root):
        state = send_command(workspace_root, {"cmd": "get"})
        if "error" in state:
            state = read_state_file(workspace_root)
    else:
        state = read_state_file(workspace_root)

    current_phase = state.get("phase", 0)
    confirmed = state.get("confirmed", False)

    # Only check confirmation for Execute phase (4) when not yet confirmed
    if current_phase != 4 or confirmed:
        output_response("approve")

    # Get user prompt
    user_prompt = hook_input.get("prompt", "").lower()

    # Check for confirmation patterns
    for pattern in CONFIRM_PATTERNS:
        if re.search(pattern, user_prompt, re.IGNORECASE):
            # Try to confirm via daemon
            if daemon_running(workspace_root):
                confirm_result = send_command(workspace_root, {"cmd": "confirm"})
                if confirm_result.get("success"):
                    output_response(
                        "approve",
                        "✓ Execution confirmed! You may now run the Execute agent (forge:execute-agent)"
                    )
            break

    output_response("approve")


def handle_stop(hook_input: dict):
    """
    Handle Stop event for auto-validation.
    Runs validation if forge was active and past Design phase.
    """
    workspace_root = get_workspace_root()

    # Early exit if forge not active
    if not is_forge_active_for_workspace(workspace_root):
        output_response("approve")

    state = read_state_file(workspace_root)
    phase = state.get("phase", 0)

    # If past Design phase (3+), run validation
    if phase >= 3:
        validation = run_validation(workspace_root)
        msg = format_validation_result(validation)
        output_response(
            "approve",
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 AUTO-VALIDATION ON SESSION END\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{msg}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    output_response("approve")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"decision": "approve"}))
        sys.exit(0)

    event_type = sys.argv[1]

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except:
        hook_input = {}

    if event_type == "session-start":
        handle_session_start(hook_input)
    elif event_type == "pre-tool":
        handle_pre_tool(hook_input)
    elif event_type == "post-tool":
        handle_post_tool(hook_input)
    elif event_type == "user-prompt":
        handle_user_prompt(hook_input)
    elif event_type == "stop":
        handle_stop(hook_input)
    else:
        output_response("approve")


if __name__ == "__main__":
    main()
