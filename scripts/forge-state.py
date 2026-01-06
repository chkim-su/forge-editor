#!/usr/bin/env python3
"""
Forge-Editor State Machine Script

Manages workflow state for wizard routes and validation enforcement.
Based on strict-migration's state machine pattern.

State file: .claude/local/forge-state.json

Usage:
    python3 forge-state.py init                     # Initialize workflow
    python3 forge-state.py start-phase <name>       # Start a phase
    python3 forge-state.py complete-phase <name>    # Complete a phase
    python3 forge-state.py pass-gate <name>         # Mark gate as passed
    python3 forge-state.py fail-gate <name>         # Mark gate as failed
    python3 forge-state.py check-gate <name>        # Check gate status (exit 0=passed, 1=not passed)
    python3 forge-state.py require-gate <name>      # Require gate (exit 2 if not passed = BLOCKS)
    python3 forge-state.py status                   # Show current status
    python3 forge-state.py reset                    # Reset workflow
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# State file location
STATE_DIR = Path(".claude/local")
STATE_FILE = STATE_DIR / "forge-state.json"

# Phase order - must complete in sequence
PHASES = [
    "connectivity_planning",
    "component_creation",
    "validation",
    "error_fixing",
    "analysis",
    "deployment"
]

# Gates - checkpoints that must be passed
GATES = [
    "connectivity_planned",
    "component_created",
    "validation_passed",
    "errors_fixed",
    "analysis_complete"
]


def get_state_path() -> Path:
    """Get the state file path, relative to git root or cwd."""
    # Try to find git root
    cwd = Path.cwd()
    git_dir = cwd
    while git_dir != git_dir.parent:
        if (git_dir / ".git").exists():
            return git_dir / STATE_FILE
        git_dir = git_dir.parent
    # Fallback to cwd
    return cwd / STATE_FILE


def load_state() -> Optional[Dict[str, Any]]:
    """Load workflow state from file."""
    state_path = get_state_path()
    if not state_path.exists():
        return None
    try:
        with open(state_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_state(state: Dict[str, Any]):
    """Save workflow state to file."""
    state_path = get_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)


def create_initial_state() -> Dict[str, Any]:
    """Create initial workflow state."""
    return {
        "workflow_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "current_phase": "not_started",
        "phases": {phase: {"status": "pending", "started_at": None, "completed_at": None} for phase in PHASES},
        "gates_passed": {gate: False for gate in GATES},
        "history": [],
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }


def add_history(state: Dict[str, Any], action: str, details: str = ""):
    """Add entry to workflow history."""
    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details
    })


def cmd_init():
    """Initialize a new workflow."""
    existing = load_state()
    if existing and existing.get("current_phase") != "not_started":
        print(f"Warning: Existing workflow found (phase: {existing.get('current_phase')})")
        print("Use 'reset' to clear existing workflow first.")
        sys.exit(1)

    state = create_initial_state()
    add_history(state, "init", "Workflow initialized")
    save_state(state)
    print(f"Workflow initialized: {state['workflow_id']}")
    print(f"State file: {get_state_path()}")


def cmd_start_phase(name: str):
    """Start a phase."""
    state = load_state()
    if not state:
        print("Error: No workflow initialized. Run 'init' first.")
        sys.exit(2)

    if name not in PHASES:
        print(f"Error: Unknown phase '{name}'. Valid phases: {', '.join(PHASES)}")
        sys.exit(1)

    # Check if previous phases are complete
    phase_idx = PHASES.index(name)
    for i in range(phase_idx):
        prev_phase = PHASES[i]
        if state["phases"][prev_phase]["status"] != "completed":
            print(f"BLOCKED: Cannot start '{name}' - phase '{prev_phase}' not completed")
            sys.exit(2)

    state["current_phase"] = name
    state["phases"][name]["status"] = "in_progress"
    state["phases"][name]["started_at"] = datetime.now().isoformat()
    add_history(state, "start_phase", name)
    save_state(state)
    print(f"Phase started: {name}")


def cmd_complete_phase(name: str):
    """Complete a phase."""
    state = load_state()
    if not state:
        print("Error: No workflow initialized. Run 'init' first.")
        sys.exit(2)

    if name not in PHASES:
        print(f"Error: Unknown phase '{name}'. Valid phases: {', '.join(PHASES)}")
        sys.exit(1)

    if state["phases"][name]["status"] != "in_progress":
        print(f"Error: Phase '{name}' is not in progress (current: {state['phases'][name]['status']})")
        sys.exit(1)

    state["phases"][name]["status"] = "completed"
    state["phases"][name]["completed_at"] = datetime.now().isoformat()
    add_history(state, "complete_phase", name)
    save_state(state)
    print(f"Phase completed: {name}")


def cmd_pass_gate(name: str):
    """Mark a gate as passed."""
    state = load_state()
    if not state:
        print("Error: No workflow initialized. Run 'init' first.")
        sys.exit(2)

    if name not in GATES:
        print(f"Error: Unknown gate '{name}'. Valid gates: {', '.join(GATES)}")
        sys.exit(1)

    state["gates_passed"][name] = True
    add_history(state, "pass_gate", name)
    save_state(state)
    print(f"Gate passed: {name}")


def cmd_fail_gate(name: str):
    """Mark a gate as failed (reset to not passed)."""
    state = load_state()
    if not state:
        print("Error: No workflow initialized. Run 'init' first.")
        sys.exit(2)

    if name not in GATES:
        print(f"Error: Unknown gate '{name}'. Valid gates: {', '.join(GATES)}")
        sys.exit(1)

    state["gates_passed"][name] = False
    add_history(state, "fail_gate", name)
    save_state(state)
    print(f"Gate failed: {name}")


def cmd_check_gate(name: str):
    """Check if a gate is passed. Exit 0 if passed, 1 if not."""
    state = load_state()
    if not state:
        print("No workflow initialized")
        sys.exit(1)

    if name not in GATES:
        print(f"Unknown gate: {name}")
        sys.exit(1)

    passed = state["gates_passed"].get(name, False)
    if passed:
        print(f"Gate '{name}': PASSED")
        sys.exit(0)
    else:
        print(f"Gate '{name}': NOT PASSED")
        sys.exit(1)


def cmd_require_gate(name: str):
    """Require a gate to be passed. Exit 2 (BLOCKS hooks) if not passed.

    If no workflow is active, this ALLOWS the operation (exit 0).
    Gates only enforce during active wizard workflows.
    """
    state = load_state()
    if not state:
        # No active workflow - allow operation (non-wizard context)
        sys.exit(0)

    if name not in GATES:
        print(f"BLOCKED: Unknown gate '{name}'")
        sys.exit(2)

    passed = state["gates_passed"].get(name, False)
    if passed:
        sys.exit(0)
    else:
        print(f"BLOCKED: Gate '{name}' not passed")
        print(f"Current phase: {state.get('current_phase', 'unknown')}")

        # Provide helpful hints based on gate
        hints = {
            "connectivity_planned": "Run '/wizard' and complete connectivity planning first",
            "component_created": "Complete component creation in wizard workflow",
            "validation_passed": "Run validation and fix all blocking errors",
            "errors_fixed": "Fix all validation errors before proceeding",
            "analysis_complete": "Complete analysis phase before deployment"
        }
        if name in hints:
            print(f"Hint: {hints[name]}")

        sys.exit(2)


def cmd_status():
    """Show current workflow status."""
    state = load_state()
    if not state:
        print("No active workflow")
        print("Run 'python3 forge-state.py init' to start a workflow")
        return

    print("=" * 50)
    print("FORGE-EDITOR WORKFLOW STATUS")
    print("=" * 50)
    print(f"Workflow ID: {state.get('workflow_id', 'unknown')}")
    print(f"Current Phase: {state.get('current_phase', 'unknown')}")
    print(f"Last Updated: {state.get('last_updated', 'unknown')}")
    print()

    print("PHASES:")
    for phase in PHASES:
        info = state["phases"].get(phase, {})
        status = info.get("status", "unknown")
        icon = {"completed": "[OK]", "in_progress": "[..]", "pending": "[  ]"}.get(status, "[??]")
        print(f"  {icon} {phase}: {status}")
    print()

    print("GATES:")
    for gate in GATES:
        passed = state["gates_passed"].get(gate, False)
        icon = "[OK]" if passed else "[  ]"
        print(f"  {icon} {gate}")
    print()

    # Show recent history
    history = state.get("history", [])[-5:]
    if history:
        print("RECENT HISTORY:")
        for entry in history:
            ts = entry.get("timestamp", "")[:19]
            action = entry.get("action", "")
            details = entry.get("details", "")
            print(f"  {ts} {action}: {details}")


def cmd_reset():
    """Reset workflow state."""
    state_path = get_state_path()
    if state_path.exists():
        state_path.unlink()
        print("Workflow reset")
    else:
        print("No workflow to reset")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init()
    elif cmd == "start-phase":
        if len(sys.argv) < 3:
            print("Error: Phase name required")
            sys.exit(1)
        cmd_start_phase(sys.argv[2])
    elif cmd == "complete-phase":
        if len(sys.argv) < 3:
            print("Error: Phase name required")
            sys.exit(1)
        cmd_complete_phase(sys.argv[2])
    elif cmd == "pass-gate":
        if len(sys.argv) < 3:
            print("Error: Gate name required")
            sys.exit(1)
        cmd_pass_gate(sys.argv[2])
    elif cmd == "fail-gate":
        if len(sys.argv) < 3:
            print("Error: Gate name required")
            sys.exit(1)
        cmd_fail_gate(sys.argv[2])
    elif cmd == "check-gate":
        if len(sys.argv) < 3:
            print("Error: Gate name required")
            sys.exit(1)
        cmd_check_gate(sys.argv[2])
    elif cmd == "require-gate":
        if len(sys.argv) < 3:
            print("Error: Gate name required")
            sys.exit(1)
        cmd_require_gate(sys.argv[2])
    elif cmd == "status":
        cmd_status()
    elif cmd == "reset":
        cmd_reset()
    else:
        print(f"Unknown command: {cmd}")
        print("Run without arguments to see usage")
        sys.exit(1)


if __name__ == "__main__":
    main()
