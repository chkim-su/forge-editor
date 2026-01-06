#!/usr/bin/env python3
"""
Forge-Editor State Machine Script

Manages workflow state for wizard routes and validation enforcement.
Protocol-based dependency graph with parallel/sequential task support.

State file: .claude/local/forge-state.json

Usage:
    python3 forge-state.py init <workflow_type>   # Initialize workflow with protocol
    python3 forge-state.py start-phase <name>     # Start a phase
    python3 forge-state.py complete-phase <name>  # Complete a phase
    python3 forge-state.py pass-gate <name>       # Mark gate as passed
    python3 forge-state.py fail-gate <name>       # Mark gate as failed
    python3 forge-state.py check-gate <name>      # Check gate status (exit 0=passed, 1=not)
    python3 forge-state.py require-gate <name>    # Require gate (exit 2 if not passed)

    # Protocol-based validation commands
    python3 forge-state.py mark-validation <name> executed  # Mark validation as executed
    python3 forge-state.py mark-validation <name> passed    # Mark validation as passed
    python3 forge-state.py mark-validation <name> failed    # Mark validation as failed
    python3 forge-state.py check-deps <name>                # Check dependencies (exit 2 if blocked)
    python3 forge-state.py verify-protocol                  # Verify all required validations
    python3 forge-state.py suggest-parallel                 # Show parallel-runnable validations

    python3 forge-state.py status                 # Show current status
    python3 forge-state.py reset                  # Reset workflow

Workflow Types:
    skill_creation, agent_creation, command_creation, plugin_publish, quick_fix, analyze_only
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

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

# =============================================================================
# WORKFLOW PROTOCOLS - Defines required validations and dependencies per type
# =============================================================================

# =============================================================================
# WIZARD ROUTING PHASES - Semantic routing with mandatory context analysis
# =============================================================================

WIZARD_PHASES = [
    "context_analysis",      # Extract keywords/topics from conversation
    "intent_classification", # Classify intent using context
    "route_execution"        # Execute route or context-aware Q&A
]

WIZARD_GATES = [
    "context_extracted",     # Context analysis complete
    "intent_classified",     # Intent classified with confidence
    "route_determined"       # Route selected (direct or via Q&A)
]

WORKFLOW_PROTOCOLS = {
    "wizard_routing": {
        "description": "Wizard semantic routing with mandatory context analysis",
        "validations": {
            "context_analysis": {
                "required": True,
                "dependencies": [],
                "description": "Extract conversation context (keywords, topics, user_work)"
            },
            "intent_classification": {
                "required": True,
                "dependencies": ["context_analysis"],
                "description": "Classify intent using input + context"
            },
            "route_execution": {
                "required": True,
                "dependencies": ["intent_classification"],
                "description": "Execute classified route or context-aware Q&A"
            }
        },
        "phases": WIZARD_PHASES,
        "gates": WIZARD_GATES
    },
    "skill_creation": {
        "description": "Creating a new skill",
        "validations": {
            "validate_all": {
                "required": True,
                "dependencies": [],
                "description": "Schema and structure validation"
            },
            "form_selection_audit": {
                "required": True,
                "dependencies": [],
                "description": "Agent/Skill/Hook/Command form appropriateness"
            },
            "content_quality_audit": {
                "required": False,
                "dependencies": ["validate_all"],
                "description": "Korean/emoji/comment quality check (W037/W038)"
            },
            "functional_test": {
                "required": True,
                "dependencies": ["validate_all", "form_selection_audit"],
                "description": "Registration and dependency checks"
            },
            "plugin_test": {
                "required": False,
                "dependencies": ["functional_test"],
                "description": "Isolated environment testing"
            }
        }
    },
    "agent_creation": {
        "description": "Creating a new agent",
        "validations": {
            "validate_all": {
                "required": True,
                "dependencies": [],
                "description": "Schema and structure validation"
            },
            "form_selection_audit": {
                "required": True,
                "dependencies": [],
                "description": "Agent/Skill/Hook/Command form appropriateness"
            },
            "content_quality_audit": {
                "required": False,
                "dependencies": ["validate_all"],
                "description": "Korean/emoji/comment quality check (W037/W038)"
            },
            "functional_test": {
                "required": False,
                "dependencies": ["validate_all"],
                "description": "Registration and dependency checks"
            }
        }
    },
    "command_creation": {
        "description": "Creating a new command",
        "validations": {
            "validate_all": {
                "required": True,
                "dependencies": [],
                "description": "Schema and structure validation"
            },
            "content_quality_audit": {
                "required": False,
                "dependencies": ["validate_all"],
                "description": "Korean/emoji/comment quality check (W037/W038)"
            },
            "functional_test": {
                "required": False,
                "dependencies": ["validate_all"],
                "description": "Registration checks"
            }
        }
    },
    "plugin_publish": {
        "description": "Publishing plugin to marketplace",
        "validations": {
            "validate_all": {
                "required": True,
                "dependencies": [],
                "description": "Schema and structure validation"
            },
            "form_selection_audit": {
                "required": True,
                "dependencies": [],
                "description": "All components form appropriateness"
            },
            "content_quality_audit": {
                "required": True,
                "dependencies": ["validate_all"],
                "description": "Korean/emoji/comment quality check - BLOCKING for publish"
            },
            "functional_test": {
                "required": True,
                "dependencies": ["validate_all"],
                "description": "Registration and dependency checks"
            },
            "plugin_test": {
                "required": True,
                "dependencies": ["functional_test"],
                "description": "Full isolated environment testing"
            },
            "marketplace_schema": {
                "required": True,
                "dependencies": ["validate_all"],
                "description": "Marketplace.json schema validation"
            }
        }
    },
    "quick_fix": {
        "description": "Quick validation fix",
        "validations": {
            "validate_all": {
                "required": True,
                "dependencies": [],
                "description": "Schema and structure validation"
            }
        }
    },
    "analyze_only": {
        "description": "Analysis without modification",
        "validations": {
            "validate_all": {
                "required": True,
                "dependencies": [],
                "description": "Schema and structure validation"
            },
            "form_selection_audit": {
                "required": False,
                "dependencies": ["validate_all"],
                "description": "Component form analysis"
            },
            "content_quality_audit": {
                "required": False,
                "dependencies": ["validate_all"],
                "description": "Korean/emoji/comment quality analysis"
            }
        }
    }
}


def get_state_path() -> Path:
    """Get the state file path, relative to git root or cwd."""
    cwd = Path.cwd()
    git_dir = cwd
    while git_dir != git_dir.parent:
        if (git_dir / ".git").exists():
            return git_dir / STATE_FILE
        git_dir = git_dir.parent
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


def get_protocol(workflow_type: str) -> Optional[Dict[str, Any]]:
    """Get protocol definition for workflow type."""
    return WORKFLOW_PROTOCOLS.get(workflow_type)


def create_initial_state(workflow_type: str = "skill_creation") -> Dict[str, Any]:
    """Create initial workflow state with protocol."""
    protocol = get_protocol(workflow_type)

    # Initialize validation states from protocol
    validations = {}
    if protocol:
        for name, config in protocol["validations"].items():
            validations[name] = {
                "status": "pending",  # pending, executed, passed, failed
                "required": config["required"],
                "dependencies": config["dependencies"],
                "executed_at": None,
                "passed_at": None
            }

    return {
        "workflow_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "workflow_type": workflow_type,
        "current_phase": "not_started",
        "phases": {phase: {"status": "pending", "started_at": None, "completed_at": None} for phase in PHASES},
        "gates_passed": {gate: False for gate in GATES},
        "validations": validations,
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


# =============================================================================
# ORIGINAL COMMANDS (Phase/Gate management)
# =============================================================================

def cmd_init(workflow_type: str = "skill_creation"):
    """Initialize a new workflow with protocol."""
    if workflow_type not in WORKFLOW_PROTOCOLS:
        print(f"Error: Unknown workflow type '{workflow_type}'")
        print(f"Valid types: {', '.join(WORKFLOW_PROTOCOLS.keys())}")
        sys.exit(1)

    existing = load_state()
    if existing and existing.get("current_phase") != "not_started":
        print(f"Warning: Existing workflow found (type: {existing.get('workflow_type')})")
        print("Use 'reset' to clear existing workflow first.")
        sys.exit(1)

    state = create_initial_state(workflow_type)
    add_history(state, "init", f"Workflow initialized: {workflow_type}")
    save_state(state)

    protocol = get_protocol(workflow_type)
    print(f"Workflow initialized: {state['workflow_id']}")
    print(f"Type: {workflow_type} - {protocol['description']}")
    print(f"State file: {get_state_path()}")
    print()
    print("Required validations:")
    for name, config in protocol["validations"].items():
        req = "[REQ]" if config["required"] else "[OPT]"
        deps = f" (after: {', '.join(config['dependencies'])})" if config["dependencies"] else ""
        print(f"  {req} {name}{deps}")


def cmd_start_phase(name: str):
    """Start a phase."""
    state = load_state()
    if not state:
        print("Error: No workflow initialized. Run 'init' first.")
        sys.exit(2)

    if name not in PHASES:
        print(f"Error: Unknown phase '{name}'. Valid phases: {', '.join(PHASES)}")
        sys.exit(1)

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
    """Require a gate to be passed. Exit 2 (BLOCKS hooks) if not passed."""
    state = load_state()
    if not state:
        sys.exit(0)  # No workflow - allow

    if name not in GATES:
        print(f"BLOCKED: Unknown gate '{name}'")
        sys.exit(2)

    passed = state["gates_passed"].get(name, False)
    if passed:
        sys.exit(0)
    else:
        print(f"BLOCKED: Gate '{name}' not passed")
        print(f"Current phase: {state.get('current_phase', 'unknown')}")
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


# =============================================================================
# PROTOCOL-BASED VALIDATION COMMANDS
# =============================================================================

def cmd_mark_validation(name: str, status: str, from_hook: bool = False):
    """Mark a validation as executed/passed/failed.

    IMPORTANT: For 'passed' status, this should only be called from hooks
    (via --from-hook flag) to prevent manual bypassing. Direct calls without
    --from-hook will emit a warning and mark as 'claimed' instead of 'passed'.

    Validations that require agent execution:
    - form_selection_audit: Must be verified by form-selection-auditor agent
    - functional_test: Must be verified by functional-test agent
    - plugin_test: Must be verified by plugin-tester agent
    """
    # Validations that MUST be performed by agents
    AGENT_REQUIRED = ["form_selection_audit", "functional_test", "plugin_test"]

    state = load_state()
    if not state:
        print("Error: No workflow initialized. Run 'init' first.")
        sys.exit(2)

    if name not in state.get("validations", {}):
        # Add dynamic validation if not in protocol
        state.setdefault("validations", {})[name] = {
            "status": "pending",
            "required": False,
            "dependencies": [],
            "executed_at": None,
            "passed_at": None,
            "verified_by": None
        }

    now = datetime.now().isoformat()

    if status == "executed":
        state["validations"][name]["status"] = "executed"
        state["validations"][name]["executed_at"] = now
        add_history(state, "validation_executed", name)
        print(f"Validation executed: {name}")

    elif status == "passed":
        # Check if this validation requires agent verification
        if name in AGENT_REQUIRED and not from_hook:
            print("=" * 60)
            print(f"  WARNING: '{name}' requires agent verification")
            print("=" * 60)
            print()
            print("  This validation must be performed by an agent:")
            agent_map = {
                "form_selection_audit": "form-selection-auditor",
                "functional_test": "functional-test (via Task tool)",
                "plugin_test": "plugin-tester"
            }
            print(f"    Required agent: {agent_map.get(name, 'unknown')}")
            print()
            print("  Manual bypass is not allowed. The validation will be")
            print("  marked as 'claimed' but NOT 'passed'.")
            print()
            print("  To properly pass this validation:")
            print(f"    Launch Task with {agent_map.get(name, 'the appropriate agent')}")
            print("=" * 60)

            # Mark as 'claimed' instead of 'passed' - prevents completion
            state["validations"][name]["status"] = "claimed"
            state["validations"][name]["claimed_at"] = now
            state["validations"][name]["verified_by"] = "manual_attempt"
            add_history(state, "validation_claimed_manually", f"{name} (blocked - requires agent)")
            save_state(state)
            sys.exit(1)  # Indicate failure

        # Legitimate pass (from hook or non-agent-required validation)
        state["validations"][name]["status"] = "passed"
        state["validations"][name]["passed_at"] = now
        state["validations"][name]["verified_by"] = "hook" if from_hook else "script"
        if not state["validations"][name].get("executed_at"):
            state["validations"][name]["executed_at"] = now
        add_history(state, "validation_passed", f"{name} (via {'hook' if from_hook else 'script'})")
        print(f"Validation passed: {name}")

        # Auto-pass validation_passed gate if validate_all passes
        if name == "validate_all":
            state["gates_passed"]["validation_passed"] = True
            add_history(state, "auto_pass_gate", "validation_passed")

    elif status == "failed":
        state["validations"][name]["status"] = "failed"
        if not state["validations"][name].get("executed_at"):
            state["validations"][name]["executed_at"] = now
        add_history(state, "validation_failed", name)
        print(f"Validation failed: {name}")
    else:
        print(f"Error: Unknown status '{status}'. Use: executed, passed, failed")
        sys.exit(1)

    save_state(state)


def cmd_check_deps(name: str):
    """Check if dependencies are satisfied. Exit 2 if blocked."""
    state = load_state()
    if not state:
        # No workflow - allow
        sys.exit(0)

    validations = state.get("validations", {})

    if name not in validations:
        # Unknown validation - allow (might be dynamic)
        sys.exit(0)

    deps = validations[name].get("dependencies", [])

    if not deps:
        # No dependencies - allow
        sys.exit(0)

    failed_deps = []
    for dep in deps:
        dep_status = validations.get(dep, {}).get("status", "pending")
        if dep_status != "passed":
            failed_deps.append((dep, dep_status))

    if failed_deps:
        print("=" * 60)
        print(f"  BLOCKED: Cannot run '{name}'")
        print("=" * 60)
        print()
        print("  Dependencies not satisfied:")
        for dep, status in failed_deps:
            icon = {"pending": "[ ]", "executed": "[~]", "failed": "[X]"}.get(status, "[?]")
            print(f"    {icon} {dep}: {status}")
        print()
        print("  Complete these validations first, then retry.")
        print("=" * 60)
        sys.exit(2)
    else:
        print(f"Dependencies satisfied for '{name}'")
        sys.exit(0)


def cmd_verify_protocol():
    """Verify all required validations are passed. Exit 2 if not complete."""
    state = load_state()
    if not state:
        # No workflow - allow
        sys.exit(0)

    workflow_type = state.get("workflow_type", "skill_creation")
    protocol = get_protocol(workflow_type)
    validations = state.get("validations", {})

    if not protocol:
        sys.exit(0)

    missing = []
    failed = []

    for name, config in protocol["validations"].items():
        if not config["required"]:
            continue

        v_state = validations.get(name, {})
        status = v_state.get("status", "pending")

        if status == "pending":
            missing.append(name)
        elif status == "executed":
            missing.append(f"{name} (executed but not verified)")
        elif status == "failed":
            failed.append(name)

    if missing or failed:
        print("=" * 60)
        print("  COMPLETION BLOCKED - Protocol Not Fulfilled")
        print("=" * 60)
        print()
        print(f"  Workflow: {workflow_type}")
        print()
        print("  Validation Status:")
        for name, config in protocol["validations"].items():
            v_state = validations.get(name, {})
            status = v_state.get("status", "pending")
            req = "[REQ]" if config["required"] else "[OPT]"
            icon = {
                "passed": "[OK]",
                "executed": "[~~]",
                "failed": "[XX]",
                "pending": "[  ]"
            }.get(status, "[??]")
            print(f"    {icon} {req} {name}: {status}")
        print()

        if missing:
            print("  Missing validations:")
            for m in missing:
                print(f"    - {m}")
        if failed:
            print("  Failed validations:")
            for f in failed:
                print(f"    - {f}")
        print()
        print("  Complete all required validations before finishing.")
        print("=" * 60)
        sys.exit(2)
    else:
        print("Protocol fulfilled - all required validations passed")
        sys.exit(0)


def cmd_suggest_parallel():
    """Show validations that can run in parallel now."""
    state = load_state()
    if not state:
        print("No active workflow")
        return

    validations = state.get("validations", {})

    runnable = []
    for name, v_state in validations.items():
        status = v_state.get("status", "pending")
        if status not in ["pending"]:
            continue

        deps = v_state.get("dependencies", [])
        all_deps_passed = all(
            validations.get(d, {}).get("status") == "passed"
            for d in deps
        )
        if all_deps_passed:
            runnable.append(name)

    if runnable:
        print("Parallel-runnable validations:")
        for r in runnable:
            desc = validations[r].get("description", "")
            print(f"  -> {r}")
    else:
        print("No validations ready to run (check dependencies or status)")


def cmd_status():
    """Show current workflow status with protocol info."""
    state = load_state()
    if not state:
        print("No active workflow")
        print("Run 'python3 forge-state.py init <type>' to start")
        print(f"Types: {', '.join(WORKFLOW_PROTOCOLS.keys())}")
        return

    print("=" * 60)
    print("FORGE-EDITOR WORKFLOW STATUS")
    print("=" * 60)
    print(f"Workflow ID: {state.get('workflow_id', 'unknown')}")
    print(f"Type: {state.get('workflow_type', 'unknown')}")
    print(f"Last Updated: {state.get('last_updated', 'unknown')}")
    print()

    # Validations (Protocol)
    validations = state.get("validations", {})
    if validations:
        print("VALIDATIONS (Protocol):")
        for name, v_state in validations.items():
            status = v_state.get("status", "pending")
            req = "[REQ]" if v_state.get("required") else "[OPT]"
            icon = {
                "passed": "[OK]",
                "executed": "[~~]",
                "failed": "[XX]",
                "pending": "[  ]"
            }.get(status, "[??]")
            deps = v_state.get("dependencies", [])
            deps_str = f" (after: {', '.join(deps)})" if deps else ""
            print(f"  {icon} {req} {name}: {status}{deps_str}")
        print()

    # Gates
    print("GATES:")
    for gate in GATES:
        passed = state["gates_passed"].get(gate, False)
        icon = "[OK]" if passed else "[  ]"
        print(f"  {icon} {gate}")
    print()

    # Recent history
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


# =============================================================================
# WIZARD ROUTING COMMANDS
# =============================================================================

WIZARD_STATE_FILE = STATE_DIR / "wizard-routing.json"


def get_wizard_state_path() -> Path:
    """Get the wizard state file path."""
    cwd = Path.cwd()
    git_dir = cwd
    while git_dir != git_dir.parent:
        if (git_dir / ".git").exists():
            return git_dir / WIZARD_STATE_FILE
        git_dir = git_dir.parent
    return cwd / WIZARD_STATE_FILE


def load_wizard_state() -> Optional[Dict[str, Any]]:
    """Load wizard routing state."""
    state_path = get_wizard_state_path()
    if not state_path.exists():
        return None
    try:
        with open(state_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_wizard_state(state: Dict[str, Any]):
    """Save wizard routing state."""
    state_path = get_wizard_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)


def cmd_wizard_init(user_input: str = ""):
    """Initialize wizard routing workflow."""
    state = {
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "user_input": user_input,
        "phases": {
            "context_analysis": {"status": "pending", "result": None},
            "intent_classification": {"status": "pending", "result": None},
            "route_execution": {"status": "pending", "result": None}
        },
        "context": {
            "keywords": [],
            "topics": [],
            "is_followup": False
        },
        "classification": {
            "route": None,
            "confidence": None
        },
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }
    save_wizard_state(state)
    print(f"Wizard routing initialized: {state['session_id']}")
    print(f"Input: {user_input[:50]}..." if len(user_input) > 50 else f"Input: {user_input}")


def cmd_wizard_phase(phase: str, status: str, result: str = ""):
    """Mark wizard phase status. Status: pending, in_progress, completed, skipped."""
    state = load_wizard_state()
    if not state:
        print("Error: No wizard routing session. Run 'wizard-init' first.")
        sys.exit(2)

    if phase not in WIZARD_PHASES:
        print(f"Error: Unknown phase '{phase}'. Valid: {', '.join(WIZARD_PHASES)}")
        sys.exit(1)

    if status not in ["pending", "in_progress", "completed", "skipped"]:
        print(f"Error: Unknown status '{status}'")
        sys.exit(1)

    # Check dependencies for completed status
    if status == "completed":
        phase_idx = WIZARD_PHASES.index(phase)
        for i in range(phase_idx):
            prev_phase = WIZARD_PHASES[i]
            prev_status = state["phases"][prev_phase]["status"]
            if prev_status not in ["completed", "skipped"]:
                print("=" * 60)
                print(f"  BLOCKED: Cannot complete '{phase}'")
                print("=" * 60)
                print()
                print(f"  Previous phase '{prev_phase}' is '{prev_status}'")
                print("  Complete previous phases first.")
                print("=" * 60)
                sys.exit(2)

    state["phases"][phase]["status"] = status
    if result:
        state["phases"][phase]["result"] = result
    state["phases"][phase]["updated_at"] = datetime.now().isoformat()

    save_wizard_state(state)
    print(f"Wizard phase '{phase}': {status}")


def cmd_wizard_context(keywords: str = "", topics: str = "", is_followup: str = "false"):
    """Set wizard context analysis result."""
    state = load_wizard_state()
    if not state:
        print("Error: No wizard routing session.")
        sys.exit(2)

    state["context"]["keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]
    state["context"]["topics"] = [t.strip() for t in topics.split(",") if t.strip()]
    state["context"]["is_followup"] = is_followup.lower() == "true"

    # Auto-complete context_analysis phase
    state["phases"]["context_analysis"]["status"] = "completed"
    state["phases"]["context_analysis"]["result"] = f"keywords={keywords}, topics={topics}"
    state["phases"]["context_analysis"]["updated_at"] = datetime.now().isoformat()

    save_wizard_state(state)
    print("Context analysis completed:")
    print(f"  Keywords: {state['context']['keywords']}")
    print(f"  Topics: {state['context']['topics']}")
    print(f"  Is followup: {state['context']['is_followup']}")


def cmd_wizard_classify(route: str, confidence: str = "medium"):
    """Set wizard classification result."""
    state = load_wizard_state()
    if not state:
        print("Error: No wizard routing session.")
        sys.exit(2)

    # Check context_analysis is completed
    if state["phases"]["context_analysis"]["status"] != "completed":
        print("=" * 60)
        print("  BLOCKED: Cannot classify without context analysis")
        print("=" * 60)
        print()
        print("  Run context analysis first:")
        print("    python3 forge-state.py wizard-context 'keywords' 'topics'")
        print("=" * 60)
        sys.exit(2)

    valid_routes = ["VALIDATE", "SKILL", "AGENT", "COMMAND", "ANALYZE", "PUBLISH",
                    "MCP", "HOOK_DESIGN", "FORGE", "PROJECT_INIT", "LLM_INTEGRATION",
                    "SKILL_RULES", "MENU", "CONTEXT_QA"]
    if route.upper() not in valid_routes:
        print(f"Warning: Non-standard route '{route}' (valid: {', '.join(valid_routes)})")

    state["classification"]["route"] = route.upper()
    state["classification"]["confidence"] = confidence

    # Auto-complete intent_classification phase
    state["phases"]["intent_classification"]["status"] = "completed"
    state["phases"]["intent_classification"]["result"] = f"route={route}, confidence={confidence}"
    state["phases"]["intent_classification"]["updated_at"] = datetime.now().isoformat()

    save_wizard_state(state)
    print(f"Intent classified: {route} (confidence: {confidence})")


def cmd_wizard_require(phase: str):
    """Require a wizard phase to be completed. Exit 2 if not."""
    state = load_wizard_state()
    if not state:
        # No wizard session - this is a PROBLEM for semantic routing
        print("=" * 60)
        print("  BLOCKED: No wizard routing session")
        print("=" * 60)
        print()
        print("  Semantic routing requires initialized session.")
        print("  The wizard MUST call 'wizard-init' first.")
        print("=" * 60)
        sys.exit(2)

    if phase not in WIZARD_PHASES:
        print(f"Unknown phase: {phase}")
        sys.exit(1)

    status = state["phases"][phase]["status"]
    if status == "completed":
        sys.exit(0)
    else:
        print("=" * 60)
        print(f"  BLOCKED: Wizard phase '{phase}' not completed")
        print("=" * 60)
        print()
        print(f"  Current status: {status}")
        print()

        hints = {
            "context_analysis": "Extract keywords and topics from conversation context",
            "intent_classification": "Classify user intent using input + context",
            "route_execution": "Execute the classified route or show context-aware Q&A"
        }
        print(f"  Required: {hints.get(phase, phase)}")
        print()

        # Show what's done
        print("  Phase Status:")
        for p in WIZARD_PHASES:
            s = state["phases"][p]["status"]
            icon = "[OK]" if s == "completed" else "[  ]" if s == "pending" else "[~~]"
            print(f"    {icon} {p}: {s}")

        print("=" * 60)
        sys.exit(2)


def cmd_wizard_status():
    """Show wizard routing status."""
    state = load_wizard_state()
    if not state:
        print("No active wizard routing session")
        return

    print("=" * 60)
    print("WIZARD ROUTING STATUS")
    print("=" * 60)
    print(f"Session: {state.get('session_id', 'unknown')}")
    print(f"Input: {state.get('user_input', '')[:60]}...")
    print()

    print("PHASES:")
    for phase in WIZARD_PHASES:
        p_state = state["phases"].get(phase, {})
        status = p_state.get("status", "pending")
        icon = {"completed": "[OK]", "in_progress": "[~~]", "pending": "[  ]", "skipped": "[--]"}.get(status, "[??]")
        result = p_state.get("result", "")
        print(f"  {icon} {phase}: {status}")
        if result:
            print(f"      → {result[:50]}...")

    print()
    print("CONTEXT:")
    ctx = state.get("context", {})
    print(f"  Keywords: {ctx.get('keywords', [])}")
    print(f"  Topics: {ctx.get('topics', [])}")
    print(f"  Is followup: {ctx.get('is_followup', False)}")

    print()
    print("CLASSIFICATION:")
    clf = state.get("classification", {})
    print(f"  Route: {clf.get('route', 'not determined')}")
    print(f"  Confidence: {clf.get('confidence', 'n/a')}")


def cmd_wizard_reset():
    """Reset wizard routing state."""
    state_path = get_wizard_state_path()
    if state_path.exists():
        state_path.unlink()
        print("Wizard routing reset")
    else:
        print("No wizard routing session to reset")


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        workflow_type = sys.argv[2] if len(sys.argv) > 2 else "skill_creation"
        cmd_init(workflow_type)
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
    elif cmd == "mark-validation":
        if len(sys.argv) < 4:
            print("Error: Validation name and status required")
            print("Usage: mark-validation <name> <executed|passed|failed> [--from-hook]")
            sys.exit(1)
        from_hook = "--from-hook" in sys.argv
        cmd_mark_validation(sys.argv[2], sys.argv[3], from_hook=from_hook)
    elif cmd == "check-deps":
        if len(sys.argv) < 3:
            print("Error: Validation name required")
            sys.exit(1)
        cmd_check_deps(sys.argv[2])
    elif cmd == "verify-protocol":
        cmd_verify_protocol()
    elif cmd == "suggest-parallel":
        cmd_suggest_parallel()
    elif cmd == "status":
        cmd_status()
    elif cmd == "reset":
        cmd_reset()
    # Wizard routing commands
    elif cmd == "wizard-init":
        user_input = sys.argv[2] if len(sys.argv) > 2 else ""
        cmd_wizard_init(user_input)
    elif cmd == "wizard-phase":
        if len(sys.argv) < 4:
            print("Error: Phase name and status required")
            print("Usage: wizard-phase <phase> <status> [result]")
            sys.exit(1)
        result = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_wizard_phase(sys.argv[2], sys.argv[3], result)
    elif cmd == "wizard-context":
        keywords = sys.argv[2] if len(sys.argv) > 2 else ""
        topics = sys.argv[3] if len(sys.argv) > 3 else ""
        is_followup = sys.argv[4] if len(sys.argv) > 4 else "false"
        cmd_wizard_context(keywords, topics, is_followup)
    elif cmd == "wizard-classify":
        if len(sys.argv) < 3:
            print("Error: Route required")
            print("Usage: wizard-classify <route> [confidence]")
            sys.exit(1)
        confidence = sys.argv[3] if len(sys.argv) > 3 else "medium"
        cmd_wizard_classify(sys.argv[2], confidence)
    elif cmd == "wizard-require":
        if len(sys.argv) < 3:
            print("Error: Phase required")
            sys.exit(1)
        cmd_wizard_require(sys.argv[2])
    elif cmd == "wizard-status":
        cmd_wizard_status()
    elif cmd == "wizard-reset":
        cmd_wizard_reset()
    else:
        print(f"Unknown command: {cmd}")
        print("Run without arguments to see usage")
        sys.exit(1)


if __name__ == "__main__":
    main()
