#!/usr/bin/env python3
"""
Enforce Plugin Test Hook (Stop Event)

Checks if plugin testing was performed during the session.
Blocks session termination if plugin components were modified but not tested.

Exit codes:
- 0: Allow (tests passed or no testing needed)
- 2: Block (tests required but not run)
"""

import sys
import json
import os
from pathlib import Path


def get_session_state():
    """Check if testing was performed in this session."""
    state_file = Path("/tmp/skillmaker-test-state.json")
    if state_file.exists():
        try:
            with open(state_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {"tested": False, "modified_components": []}


def check_plugin_modifications(input_data: dict) -> list:
    """Check if plugin components were modified based on session context."""
    modified = []

    # Get the stop reason from input
    stop_reason = input_data.get("stop_reason", "")

    # Check for plugin-related paths in any accumulated context
    plugin_paths = [
        ".claude-plugin/",
        "skills/",
        "agents/",
        "commands/",
        "hooks/",
    ]

    # Simple heuristic: check if we're in a skillmaker project
    cwd = os.getcwd()
    for path in plugin_paths:
        full_path = Path(cwd) / path
        if full_path.exists():
            modified.append(path)

    return modified


def main():
    input_data = {}
    try:
        raw_input = sys.stdin.read()
        if raw_input.strip():
            input_data = json.loads(raw_input)
    except Exception:
        pass

    # Get session state
    state = get_session_state()

    # If already tested, allow
    if state.get("tested", False):
        # Clear state file
        try:
            os.remove("/tmp/skillmaker-test-state.json")
        except Exception:
            pass
        print(json.dumps({"status": "allow", "reason": "Plugin tests passed"}))
        sys.exit(0)

    # Check if we're in a skillmaker/plugin project
    cwd = os.getcwd()
    is_plugin_project = (
        Path(cwd, ".claude-plugin").exists() or
        Path(cwd, "marketplace.json").exists() or
        Path(cwd, ".claude-plugin/marketplace.json").exists()
    )

    if not is_plugin_project:
        # Not a plugin project, allow
        print(json.dumps({"status": "allow", "reason": "Not a plugin project"}))
        sys.exit(0)

    # Check if plugin-tester was invoked or validate_all.py passed
    validation_marker = Path("/tmp/skillmaker-validation-passed.marker")
    if validation_marker.exists():
        # Clear marker
        try:
            os.remove(validation_marker)
        except Exception:
            pass
        print(json.dumps({"status": "allow", "reason": "Validation passed"}))
        sys.exit(0)

    # Check for quiet mode (when explicitly bypassing)
    if os.environ.get("SKILLMAKER_SKIP_TEST_ENFORCEMENT"):
        print(json.dumps({"status": "allow", "reason": "Enforcement skipped by environment"}))
        sys.exit(0)

    # Block with guidance
    guidance = """
❌ Plugin test not performed in this session.

Before ending the session, please run:
1. `python3 scripts/validate_all.py` - Schema validation
2. `Task(plugin-tester)` - Isolated plugin testing

Or skip enforcement with: SKILLMAKER_SKIP_TEST_ENFORCEMENT=1
"""

    print(guidance, file=sys.stderr)

    # Output JSON for Claude to process
    print(json.dumps({
        "status": "block",
        "reason": "Plugin testing not performed",
        "guidance": "Run validate_all.py or spawn plugin-tester agent"
    }))

    sys.exit(2)  # Block


if __name__ == "__main__":
    main()
