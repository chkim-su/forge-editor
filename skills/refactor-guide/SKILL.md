---
name: refactor-guide
description: "Guide for refactoring existing projects with rollback safety"
triggers:
  - "refactor"
  - "improve existing"
  - "restructure"
  - "clean up code"
  - "code improvement"
  - "technical debt"
---

# Refactoring Guide

Safe, incremental approach to improving existing codebases.

## Refactoring Phases

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: ANALYZE                                           │
│  └─ Understand current state, identify issues               │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: DESIGN                                            │
│  └─ Propose improvements with trade-offs                    │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: PREVIEW (New!)                                    │
│  └─ Dry-run showing what will change                        │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: EXECUTE                                           │
│  └─ Apply changes incrementally with checkpoints            │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: VERIFY                                            │
│  └─ Confirm behavior preserved, tests pass                  │
└─────────────────────────────────────────────────────────────┘
```

## Refactoring Categories

| Category | Focus | Risk | Approach |
|----------|-------|------|----------|
| **Rename/Move** | Organization | Low | Symbolic rename, update references |
| **Extract** | Split components | Medium | Create new unit, replace inline |
| **Inline** | Remove abstraction | Medium | Replace calls with body, delete unit |
| **Restructure** | Architecture | High | Incremental migration |
| **Optimize** | Performance | Medium | Profile first, measure after |

## Safety Rules

### 1. Analyze Before Changing
Never refactor blind. Understand:
- Current behavior
- Dependencies
- Test coverage
- Integration points

### 2. Preserve Behavior
Refactoring ≠ feature change. The code should do the same thing, just better.

### 3. Incremental Steps
Each change should be:
- Small and focused
- Independently verifiable
- Rollbackable

### 4. Test Boundaries
Know what needs testing:
- Unit tests for changed logic
- Integration tests for interfaces
- E2E tests for workflows

### 5. Rollback Plan
Before each step, know how to undo:
- Git checkpoint (`git stash` or commit)
- Document original state
- Keep backups of deleted code temporarily

## Rollback Mechanisms

### Git-Based Rollback
```bash
# Before refactoring
git checkout -b refactor/feature-name
git add -A && git commit -m "Checkpoint before refactoring"

# After each successful step
git add -A && git commit -m "Step N: description"

# If something breaks
git revert HEAD  # Undo last commit
# OR
git reset --hard HEAD~1  # Completely undo last commit
```

### Incremental Checkpoints
```python
# Rollback tracking structure
{
    "refactor_session": "uuid",
    "checkpoints": [
        {
            "step": 1,
            "description": "Extract helper function",
            "files_modified": ["src/main.py"],
            "git_sha": "abc123",
            "can_rollback": true
        }
    ]
}
```

## Phase Details

### Phase 1: Analyze

**Inputs:**
- What code needs improvement?
- What's the pain point?

**Process:**
1. Map current architecture
2. Identify code smells
3. Assess test coverage
4. Find dependencies

**Outputs:**
```markdown
## Current State Analysis

**Code Structure:**
- [Component]: [Role, size, complexity]

**Issues Identified:**
- [Issue]: [Location, severity, impact]

**Dependencies:**
- [Component] -> [Dependency]: [Coupling type]

**Test Coverage:**
- [Area]: [Coverage %, gaps]

**Risk Assessment:**
- [Change area]: [Risk level, mitigation]
```

### Phase 2: Design

**Inputs:**
- Analysis results
- Improvement goals

**Process:**
1. Generate improvement options
2. Evaluate trade-offs
3. Plan incremental steps
4. Identify test requirements

**Outputs:**
```markdown
## Refactoring Design

### Option A: [Name]
**Approach:** [Description]
**Steps:**
1. [Step with estimated impact]
2. [Step with estimated impact]
**Trade-offs:**
| Aspect | Before | After |
|--------|--------|-------|
| Complexity | ... | ... |
| Coupling | ... | ... |

### Option B: [Name]
[Same structure]

## Step Sequence
[Ordered list of all changes with dependencies]
```

### Phase 3: Preview

**Purpose:** Dry-run showing exact changes before execution

**Outputs:**
```markdown
## Preview: Changes That Will Be Made

### Step 1: [Description]
**Files Modified:**
- `path/to/file.py`: [What changes]

**Diff Preview:**
\`\`\`diff
- old code
+ new code
\`\`\`

**Rollback:** `git revert <sha>` or `git checkout -- path/to/file.py`

### Step 2: [Description]
[Same structure]

## Confirmation Required
Type "proceed" to execute these changes, or "modify" to adjust the plan.
```

### Phase 4: Execute

**Safety Requirements:**
- Create git checkpoint before starting
- Commit after each step
- Run tests after each step
- Stop on failure

**Execution Pattern:**
```bash
# Before execution
git checkout -b refactor/$(date +%Y%m%d)-$(openssl rand -hex 4)
git add -A && git commit -m "Checkpoint: before refactoring"

# After each step
git add -A && git commit -m "Refactor step N: description"
# Run tests
pytest tests/ || git revert HEAD --no-edit

# On completion
git checkout main
git merge refactor/...
```

### Phase 5: Verify

**Checks:**
1. All tests pass
2. No new warnings/errors
3. Behavior unchanged (manual spot-check)
4. Performance acceptable
5. Code review (if applicable)

## Common Refactoring Patterns

### Extract Function/Method
**When:** Code block does one thing, used in multiple places
```python
# Before
def process():
    # ... validation logic ...
    # ... business logic ...

# After
def validate(data):
    # ... validation logic ...

def process():
    validate(data)
    # ... business logic ...
```

### Extract Class
**When:** Class does too many things
```python
# Before: God class
class UserManager:
    def create_user(self): ...
    def send_email(self): ...
    def generate_report(self): ...

# After: Focused classes
class UserRepository:
    def create_user(self): ...

class EmailService:
    def send_email(self): ...

class ReportGenerator:
    def generate_report(self): ...
```

### Inline
**When:** Abstraction adds no value
```python
# Before: Unnecessary wrapper
def get_user_name(user):
    return user.name

name = get_user_name(user)

# After: Direct access
name = user.name
```

### Rename
**When:** Name doesn't reflect purpose
```python
# Before
def proc(d):
    return d * 2

# After
def double_value(number):
    return number * 2
```

## Error Recovery

### Mid-Refactor Failure
If something breaks during refactoring:

1. **Don't panic** - you have checkpoints
2. **Identify the breaking change** - which step failed?
3. **Rollback to last good state:**
   ```bash
   git log --oneline  # Find last good commit
   git reset --hard <sha>
   ```
4. **Analyze what went wrong**
5. **Adjust plan and retry**

### Test Failure After Refactor
1. Check if test is valid (might need updating)
2. If behavior changed, rollback
3. If test is outdated, update test first, then retry

## Quick Commands

```bash
# Start refactoring session
git checkout -b refactor/$(date +%Y%m%d)

# Checkpoint
git add -A && git commit -m "Checkpoint"

# Rollback last step
git revert HEAD --no-edit

# Hard rollback to start
git reset --hard $(git log --format=%H --reverse | head -1)

# Complete and merge
git checkout main && git merge refactor/...
```
