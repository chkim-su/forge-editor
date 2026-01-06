# Phase Transition Rules

## Phase Order

```
not_started
    ↓ init
connectivity_planning
    ↓ pass connectivity_planned gate
component_creation
    ↓ pass component_created gate
validation
    ↓ pass validation_passed gate
error_fixing (if needed)
    ↓ pass errors_fixed gate
analysis
    ↓ pass analysis_complete gate
deployment
    ↓ complete
(reset)
```

## Transition Rules

### Rule 1: Sequential Only

```python
def can_start_phase(phase):
    phase_idx = PHASES.index(phase)
    for i in range(phase_idx):
        prev = PHASES[i]
        if phases[prev]["status"] != "completed":
            return False
    return True
```

Cannot skip phases. Must complete previous phase first.

### Rule 2: One Active Phase

```python
def start_phase(phase):
    if current_phase != "not_started" and current_phase != phase:
        if phases[current_phase]["status"] == "in_progress":
            raise Error("Complete current phase first")
```

Only one phase in_progress at a time.

### Rule 3: Gate Before Proceed

```
Phase N complete
        ↓
Gate N must pass
        ↓
Phase N+1 can start
```

Gates are mandatory checkpoints.

## Phase Lifecycle

```
pending → in_progress → completed
            ↓
          failed (optional)
```

### Starting a Phase

```bash
forge-state.py start-phase validation
```

Effects:
- Sets `current_phase` to phase name
- Sets phase status to `in_progress`
- Records `started_at` timestamp

### Completing a Phase

```bash
forge-state.py complete-phase validation
```

Requirements:
- Phase must be `in_progress`
- Associated gate should be passed first

Effects:
- Sets phase status to `completed`
- Records `completed_at` timestamp

## Error Handling

### Validation Fails

```
validation phase
    ↓
run validate_all.py
    ↓
blocking errors found
    ↓
fail-gate validation_passed
    ↓
enter error_fixing phase
    ↓
fix errors
    ↓
re-run validation
    ↓
pass → pass-gate validation_passed
    ↓
complete validation phase
```

### Phase Skip Attempt

```
User tries to start analysis without completing validation
    ↓
start-phase analysis
    ↓
ERROR: Previous phases not complete
EXIT(2)
```

## Workflow Reset

```bash
forge-state.py reset
```

Use when:
- Workflow completes successfully
- User wants to abort and start fresh
- State becomes inconsistent

Effects:
- Deletes state file
- Next operation starts fresh
