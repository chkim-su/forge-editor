---
name: forge-guide
description: "Usage guide for Forge general-purpose design workflow"
triggers:
  - "how does forge work"
  - "forge workflow"
  - "forge phases"
  - "design workflow"
  - "plugin design"
---

# Forge Design Workflow

Forge is a general-purpose design guidance system with a deterministic 6-phase workflow.

## What Can Forge Do?

Forge guides you through designing and building:

| Solution Type | Description | Entry Point |
|--------------|-------------|-------------|
| **Plugin** | Extend Claude Code | `/forge` |
| **Script** | Standalone utilities | `/forge` or direct |
| **Refactor** | Improve existing code | `/refactor` |
| **Feature** | Add to existing project | `/forge` |
| **Integration** | Connect systems | `/forge` |

## Quick Start

### Full Workflow
```
/forge
```
Starts the complete 6-phase design workflow.

### Quick Analysis
```
/diagnose [what to analyze]
```
Analyze without activating full workflow.

### Quick Design
```
/design [what to design]
```
Get design options without full workflow.

### Refactoring
```
/refactor [what to improve]
```
Guided refactoring with safety checkpoints.

## The 6 Phases

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 0: INPUT                                             │
│  └─ Normalize user intent into clear problem statement      │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: ANALYSIS                                          │
│  └─ Analyze codebase and describe reality                   │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: DESIGN                                            │
│  └─ Propose options with neutral trade-offs                 │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: PREVIEW (New!)                                    │
│  └─ Show exactly what will change (dry-run)                 │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: EXECUTE (Requires confirmation)                   │
│  └─ Implement the confirmed design                          │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: VALIDATE                                          │
│  └─ Validate structure and schema                           │
└─────────────────────────────────────────────────────────────┘
```

## Phase Details

### Phase 0: Input
**Agent:** `forge:input-agent`
**Blocking:** Write, Edit, Bash (no file modifications)

Takes your description and produces a structured problem statement with:
- What needs to be built
- Why it's needed
- Constraints and success criteria

### Phase 1: Analysis
**Agent:** `forge:analysis-agent`

Explores the codebase to understand:
- Project type and technology stack
- Relevant existing code
- Patterns and conventions
- Integration points

### Phase 2: Design
**Agent:** `forge:design-agent`
**Blocking:** Write, Edit (no implementation)

Synthesizes 2-3 design options with:
- Specific components and file structure
- **Neutral** trade-offs (no recommendations!)
- User must select an option

### Phase 3: Preview (New!)
**Agent:** `forge:preview-agent`
**Blocking:** Write, Edit (dry-run only)

Shows exactly what will change:
- Files to create/modify/delete
- Diff previews
- Rollback commands
- Impact assessment

### Phase 4: Execute (Requires Confirmation)
**Agent:** `forge:execute-agent`

After Preview completes, you must confirm:
- Type "yes", "proceed", "confirm", or similar
- The agent then implements the design
- Creates rollback points for safety

### Phase 5: Validate
**Agent:** `forge:validate-agent`

Validates the output:
- Structure correctness
- Schema compliance
- Reference validity
- Syntax checking

## Strict Enforcement

Forge now **blocks** dangerous actions in certain phases:

| Phase | Blocked Tools | Reason |
|-------|--------------|--------|
| 0 (Input) | Write, Edit, Bash | Gather requirements only |
| 2 (Design) | Write, Edit | Create options only |
| 3 (Preview) | Write, Edit | Dry-run only |
| 4 (Execute) | Write, Edit, Bash | Until confirmed |

## State Management

State is stored in `<workspace>/.claude/local/forge-state.json`:

```json
{
  "forge_active": true,
  "workspace_root": "/path/to/workspace",
  "phase": 2,
  "confirmed": false,
  "checkpoints": [...],
  "design_hash": "abc123...",
  "requires_reconfirmation": false,
  "rollback_points": [...]
}
```

## CLI Commands

```bash
# Check current state
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py get

# Check current phase
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py get-phase

# Activate workflow
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py activate

# Deactivate workflow
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py deactivate

# Confirm execution (phase 4)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py confirm

# Add rollback point
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py add-rollback "description"

# List rollback points
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py get-rollbacks
```

## Key Principles

1. **Sequential**: Phases must complete in order
2. **Deterministic**: Agent execution = checkpoint, no LLM judgment
3. **Strict enforcement**: Blocks dangerous tools in key phases
4. **Neutral design**: No recommendations, only trade-offs
5. **Preview before execute**: See changes before they happen
6. **Rollback safety**: Git checkpoints for recovery
7. **Auto-validation**: Runs on session end

## Related Skills

- **solution-router**: Determine solution type
- **schema-registry**: Schema templates and validation
- **refactor-guide**: Refactoring workflow details
- **structured-dialogue**: Question format standards
