---
name: workflow-enforcement
description: State machine patterns for enforcing sequential workflows with gates
category: architecture
tools: []
---

# Workflow Enforcement Patterns

Gate-based workflow enforcement for sequential operations.

## Core Concept

```
Phase 1 → Gate 1 → Phase 2 → Gate 2 → Phase 3
   ↓                  ↓                  ↓
 start             require             pass
 complete          check               complete
```

## When to Use

- Multi-step wizards requiring sequential execution
- Operations that must pass validation before proceeding
- Deployment workflows with mandatory checkpoints
- Any workflow where skipping steps is dangerous

## Key Components

| Component | Purpose | Script |
|-----------|---------|--------|
| **Phases** | Sequential work stages | `start-phase`, `complete-phase` |
| **Gates** | Checkpoints between phases | `pass-gate`, `require-gate` |
| **State** | Persistent workflow tracking | `.claude/local/forge-state.json` |

## Exit Code Policy

| Exit Code | Meaning | Hook Behavior |
|-----------|---------|---------------|
| `exit(0)` | ALLOW | Proceed |
| `exit(1)` | WARN | May block (depends on hook type) |
| `exit(2)` | BLOCK | Always blocks in PreToolUse |

## Quick Start

```bash
# Initialize workflow
python3 scripts/forge-state.py init

# Start a phase
python3 scripts/forge-state.py start-phase validation

# Pass a gate
python3 scripts/forge-state.py pass-gate validation_passed

# Complete a phase
python3 scripts/forge-state.py complete-phase validation

# Check status
python3 scripts/forge-state.py status

# Reset workflow
python3 scripts/forge-state.py reset
```

## References

- `references/state-machine-patterns.md` - State machine design patterns
- `references/gate-design.md` - Gate placement and design
- `references/phase-transition.md` - Phase sequencing rules
- `references/exit-code-guide.md` - Exit code classification
