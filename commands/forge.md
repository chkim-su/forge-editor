---
name: forge
description: "Start Forge design workflow (full 6-phase)"
---

# /forge - Start Design Workflow

You are starting the Forge design workflow. This is a 6-phase deterministic process for designing any solution type.

## Activate Forge

First, activate the forge workflow by running:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py activate
```

## Workflow Phases

| Phase | Name | Agent | Purpose |
|-------|------|-------|---------| 
| 0 | Input | `forge:input-agent` | Normalize user intent into clear problem statement |
| 1 | Analysis | `forge:analysis-agent` | Analyze codebase reality and identify patterns |
| 2 | Design | `forge:design-agent` | Propose design options with neutral trade-offs |
| 3 | Preview | `forge:preview-agent` | Preview changes before execution (dry-run) |
| 4 | Execute | `forge:execute-agent` | Implement the confirmed design (requires confirmation) |
| 5 | Validate | `forge:validate-agent` | Validate structure and schema |

## How It Works

1. **Sequential Progress**: Phases must be completed in order (0 → 1 → 2 → 3 → 4 → 5)
2. **Strict Enforcement**: Write/Edit blocked in phases 0, 2, 3 until appropriate
3. **Preview Before Execute**: See exactly what will change
4. **Confirmation Gate**: Execute phase (4) requires user confirmation
5. **Auto-Validation**: Runs validation on session end

## Strict Phase Rules

| Phase | Blocked Tools | Reason |
|-------|--------------|--------|
| 0 (Input) | Write, Edit, Bash | Gather requirements only |
| 2 (Design) | Write, Edit | Create options only |
| 3 (Preview) | Write, Edit | Dry-run only |
| 4 (Execute) | Write, Edit, Bash | Until confirmed |

## Start Phase 0

Now prompt the user to describe what they want to build.

**Ask the user:**
> What would you like to design? Describe the functionality, use case, or problem you want to solve.

Once they respond, launch the Input agent:

```
Task(subagent_type="forge:input-agent", prompt="[user's description]")
```

## Solution Types

Forge can guide design for:

| Type | Description |
|------|-------------|
| **Plugin** | Extend Claude Code capabilities |
| **Script** | Standalone utilities |
| **Refactor** | Improve existing code |
| **Feature** | Add to existing project |
| **Integration** | Connect systems |

The Analysis phase will help determine the best approach.

## Alternative Entry Points

For quick tasks without full workflow:

- `/diagnose` - Quick analysis only
- `/design` - Design options only  
- `/refactor` - Refactoring workflow

## Commands During Workflow

```bash
# Check current state
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py get

# Check current phase
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py get-phase

# Confirm execution (at phase 4)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py confirm

# Deactivate (if needed)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py deactivate
```
