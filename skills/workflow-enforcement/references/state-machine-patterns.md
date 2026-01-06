# State Machine Patterns

## Pattern 1: Linear Workflow

```
init → phase1 → gate1 → phase2 → gate2 → complete
```

Best for: Sequential wizard flows with no branching.

### Implementation

```python
PHASES = ["connectivity_planning", "component_creation", "validation", "deployment"]

def can_start_phase(phase):
    idx = PHASES.index(phase)
    for i in range(idx):
        if not phases[PHASES[i]]["status"] == "completed":
            return False
    return True
```

## Pattern 2: Gate-Guarded Operations

```
                ┌─ gate check ─┐
                ↓              ↓
Tool Use → PreToolUse → exit(2) BLOCKS
                       exit(0) ALLOWS
```

Best for: Blocking dangerous operations until prerequisites met.

### Implementation

```python
def require_gate(gate_name):
    state = load_state()
    if not state:
        sys.exit(0)  # No workflow = allow
    if state["gates_passed"].get(gate_name):
        sys.exit(0)  # Gate passed = allow
    else:
        print(f"BLOCKED: Gate '{gate_name}' not passed")
        sys.exit(2)  # BLOCK
```

## Pattern 3: Evidence-Based Gates

```
action → result → evidence file → gate pass
                       ↓
              .claude/local/evidence.json
```

Best for: Verifiable operations that need proof of completion.

### Implementation

```python
def pass_gate_with_evidence(gate_name, evidence):
    state = load_state()
    state["gates_passed"][gate_name] = True
    state["evidence"][gate_name] = evidence
    save_state(state)
```

## Pattern 4: Rollback Points

```
phase1 → [checkpoint] → phase2 → failure? → rollback to checkpoint
```

Best for: Operations that can fail and need recovery.

### Implementation

```python
def create_checkpoint(phase):
    state = load_state()
    state["checkpoints"][phase] = {
        "git_commit": get_current_commit(),
        "state_snapshot": copy.deepcopy(state)
    }
    save_state(state)
```

## Anti-Patterns

### Anti-Pattern 1: Unconditional Blocking

```python
# BAD: Blocks even when no workflow exists
def require_gate(name):
    state = load_state()
    if not state:
        sys.exit(2)  # Blocks everything!
```

```python
# GOOD: Only blocks during active workflows
def require_gate(name):
    state = load_state()
    if not state:
        sys.exit(0)  # No workflow = allow normal operation
```

### Anti-Pattern 2: Missing State Persistence

```python
# BAD: State lost between sessions
workflow_state = {}  # In-memory only

# GOOD: Persistent state file
STATE_FILE = Path(".claude/local/forge-state.json")
```

### Anti-Pattern 3: Skippable Gates

```python
# BAD: Gate check only in documentation
"Run validation before proceeding"

# GOOD: Gate enforced by hook
{
  "PreToolUse": [{
    "matcher": "Task",
    "hooks": [{
      "command": "forge-state.py require-gate validation_passed"
    }]
  }]
}
```
