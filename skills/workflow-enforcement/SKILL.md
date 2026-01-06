---
name: workflow-enforcement
description: Protocol-based workflow enforcement with validation dependencies and anti-bypass protection
category: architecture
tools: []
---

# Workflow Enforcement Patterns

Protocol-based workflow enforcement with dependency graphs and anti-bypass protection.

## Core Concept

```
validate_all ──┬──> content_quality_audit
               │
form_audit ────┼──> functional_test ──> plugin_test
               │
               └──> (MCP workflows)
```

## Workflow Types

| Type | Description | Required Validations |
|------|-------------|---------------------|
| `skill_creation` | Creating new skills | validate_all, form_audit, functional_test |
| `agent_creation` | Creating new agents | validate_all, form_audit |
| `command_creation` | Creating commands | validate_all |
| `plugin_publish` | Marketplace deployment | ALL validations + content_quality (blocking) |
| `quick_fix` | Simple error fixes | validate_all only |
| `analyze_only` | Read-only analysis | validate_all |

## Validation Dependencies

```
validate_all (no deps) ──┬──> content_quality_audit
                         │
form_selection_audit ────┼──> functional_test ──> plugin_test
(no deps)                │
```

- Parallel: `validate_all` and `form_selection_audit` can run together
- Sequential: `functional_test` requires both to pass first

## Anti-Bypass Protection

Agent-required validations cannot be manually passed:

```bash
# This will FAIL (manual bypass attempt)
python3 forge-state.py mark-validation form_selection_audit passed

# This will SUCCEED (triggered by hook after agent completes)
python3 forge-state.py mark-validation form_selection_audit passed --from-hook
```

Protected validations: `form_selection_audit`, `functional_test`, `plugin_test`

## Quick Start

```bash
# Initialize workflow
python3 scripts/forge-state.py init skill_creation

# Check status
python3 scripts/forge-state.py status

# Check dependencies before validation
python3 scripts/forge-state.py check-deps functional_test

# Mark validation (via hook only for protected ones)
python3 scripts/forge-state.py mark-validation validate_all passed

# Verify protocol completion
python3 scripts/forge-state.py verify-protocol
```

## Exit Code Policy

| Exit Code | Meaning | Hook Behavior |
|-----------|---------|---------------|
| `exit(0)` | ALLOW | Proceed |
| `exit(1)` | WARN | May block |
| `exit(2)` | BLOCK | Always blocks in PreToolUse |

## Content Quality Validation

W037 (Korean) and W038 (emoji) warnings:
- **Normal mode**: Warning only (exit 0)
- **Publish mode**: Blocking (exit 2) via `--publish-mode` flag

## MCP Integration

- SessionStart hook auto-starts MCP daemons
- `mcp-health-check.py` verifies daemon status
- Optional `mcp_initialized` validation for MCP-dependent workflows

## References

- `references/state-machine-patterns.md` - State machine design
- `references/gate-design.md` - Gate placement and design
- `references/phase-transition.md` - Phase sequencing rules
- `references/exit-code-guide.md` - Exit code classification
- `references/protocol-design.md` - 6 workflow types detailed
