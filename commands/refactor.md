---
name: refactor
description: "Guided refactoring workflow with safety checkpoints"
---

# /refactor - Safe Refactoring Workflow

Start a structured refactoring workflow with analysis, design, preview, and safety checkpoints.

## Purpose

Safely improve existing code through:
- Incremental changes
- Rollback capability
- Behavior preservation
- Test verification

## Usage

Describe what needs refactoring:

```
/refactor [description of what to improve]
```

## Examples

```
/refactor the authentication module for better separation of concerns
/refactor database queries to use the repository pattern
/refactor error handling to be consistent across the codebase
/refactor test utilities to reduce duplication
```

## Workflow Phases

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: ANALYZE                                           │
│  └─ Understand current state, identify issues               │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: DESIGN                                            │
│  └─ Propose improvements with trade-offs                    │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: PREVIEW                                           │
│  └─ Show exactly what will change (dry-run)                 │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: EXECUTE                                           │
│  └─ Apply changes incrementally with checkpoints            │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: VERIFY                                            │
│  └─ Confirm behavior preserved, tests pass                  │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

1. **Analyze** - Use `/diagnose` or Analysis agent to understand current state
2. **Design** - Use Design agent to propose improvement options
3. **Preview** - Show diff of proposed changes before execution
4. **Execute** - Make changes with git checkpoints
5. **Verify** - Run tests, check behavior preserved

## Safety Features

### Git Checkpoints
```bash
# Automatic before each step
git add -A && git commit -m "Checkpoint before [step]"
```

### Rollback Commands
```bash
# Undo last step
git revert HEAD --no-edit

# Undo to checkpoint
git reset --hard <sha>
```

### Test Verification
- Run tests after each step
- Stop on failure
- Report what changed

## Refactoring Categories

| Category | Description | Risk |
|----------|-------------|------|
| **Rename** | Change names of symbols | Low |
| **Move** | Relocate code to different files | Low |
| **Extract** | Split large units into smaller | Medium |
| **Inline** | Remove unnecessary abstraction | Medium |
| **Restructure** | Change architecture | High |

## Output

Each phase produces specific output:

### After Analyze
```markdown
## Current State Analysis
[Structure, issues, dependencies, coverage]
```

### After Design
```markdown
## Refactoring Options
[Options with trade-offs]
```

### After Preview
```markdown
## Preview: Changes That Will Be Made
[Diff preview, file list, rollback commands]
```

### After Execute
```markdown
## Execution Summary
[What was changed, commits made]
```

### After Verify
```markdown
## Verification Results
[Test results, behavior check]
```

## Best Practices

1. **Analyze before changing** - Never refactor blind
2. **Preserve behavior** - Refactoring ≠ feature change
3. **Incremental steps** - Small, verifiable changes
4. **Test boundaries** - Know what needs testing
5. **Rollback plan** - How to undo if needed

## Quick vs Full Refactor

| Aspect | Quick | Full Workflow |
|--------|-------|---------------|
| Scope | Single file/function | Cross-cutting |
| Safety | Manual | Checkpoints |
| Preview | Optional | Required |
| Tests | Manual | Automated |

For simple renames or small changes, skip the workflow.
For larger refactorings, use the full workflow.
