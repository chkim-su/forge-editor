# Gate Design

## Gate Types

### 1. Validation Gate

Ensures quality before proceeding.

```
validation → check result → pass/fail → gate
```

| Trigger | Gate Name | Blocks |
|---------|-----------|--------|
| `validate_all.py` pass | `validation_passed` | Task, Bash (git) |

### 2. Approval Gate

Requires user confirmation.

```
proposal → AskUserQuestion → user approves → gate
```

| Trigger | Gate Name | Blocks |
|---------|-----------|--------|
| User confirms plan | `plan_approved` | Implementation agents |

### 3. Evidence Gate

Requires proof of work.

```
action → generate evidence → verify → gate
```

| Trigger | Gate Name | Blocks |
|---------|-----------|--------|
| Tests pass + evidence file | `tests_passed` | Deployment |

## Gate Placement

### Pre-Creation

```
Plan connectivity → connectivity_planned gate → Create component
```

Purpose: Prevent orphan components.

### Pre-Deployment

```
Validation → validation_passed gate
Analysis → analysis_complete gate
→ Both gates → Publish
```

Purpose: Ensure quality before deployment.

### Pre-Agent

```
validation_passed gate → Task tool → Agent spawned
```

Purpose: No agents without passing validation.

## Gate Granularity

### Too Coarse

```
# Only one gate for entire workflow
start → [all work] → final_gate → end
```

Problem: No intermediate checkpoints.

### Too Fine

```
# Gate for every small action
edit → gate → save → gate → format → gate
```

Problem: Too much overhead.

### Just Right

```
# Gate at meaningful checkpoints
plan → [plan_gate] → implement → [impl_gate] → test → [test_gate] → deploy
```

Balance: Meaningful checkpoints without friction.

## Gate Naming Convention

```
{phase}_{action}
```

Examples:
- `connectivity_planned`
- `component_created`
- `validation_passed`
- `analysis_complete`
- `tests_passed`

## Hook Integration

```json
{
  "PreToolUse": [
    {
      "matcher": "Task",
      "hooks": [
        {
          "type": "command",
          "command": "forge-state.py require-gate validation_passed",
          "timeout": 3
        }
      ]
    }
  ]
}
```

Key points:
- Gate check must exit(2) to block
- exit(0) allows operation
- Timeout should be short (gates are fast)
