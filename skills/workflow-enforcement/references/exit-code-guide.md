# Exit Code Guide

## Hook Exit Code Semantics

| Exit Code | Meaning | PreToolUse Behavior |
|-----------|---------|---------------------|
| `0` | SUCCESS/ALLOW | Operation proceeds |
| `1` | WARN/ERROR | May or may not block (varies) |
| `2` | BLOCK | **Always blocks operation** |

**Key insight**: Only `exit(2)` guarantees blocking in PreToolUse hooks.

## Classification Philosophy

### Blocking Issues (exit 2)

Issues that indicate the plugin is **incomplete or non-functional**:

| Category | Codes | Reason |
|----------|-------|--------|
| **Schema errors** | E001-E021 | Plugin won't load |
| **Missing structure** | W029 | Required frontmatter missing |
| **Broken tools** | W030 | Declared tools won't work |
| **Dead agents** | W033, W034 | Agents won't function |
| **Orphan components** | W046 | Components unreachable |

### Quality Issues (exit 0)

Issues that are **advisory only** - plugin works but could be better:

| Category | Codes | Reason |
|----------|-------|--------|
| **Documentation** | W028 | Missing hookify (style) |
| **Cleanup** | W036 | Unnecessary files |
| **Style** | W037, W038 | Language/emoji preferences |
| **Recommendations** | W040, W045 | Best practices |
| **Known issues** | W035 | Marked for later |

## Implementation

```python
class ValidationResult:
    BLOCKING_WARNING_CODES = {
        'W029',  # Missing frontmatter
        'W030',  # Missing tools declaration
        'W033',  # Missing Skill() usage
        'W034',  # Workflow pattern violation
        'W046',  # Unreferenced components
    }

    QUALITY_WARNING_CODES = {
        'W028',  # Enforcement keywords
        'W035',  # NOT YET HOOKIFIED
        'W036',  # Unnecessary files
        'W037',  # Non-English content
        'W038',  # Emoji usage
        'W040',  # Form selection audit
        'W045',  # Test infrastructure
    }

    def has_blocking_issues(self) -> bool:
        if self.errors:
            return True
        return bool(self.found_codes & self.BLOCKING_WARNING_CODES)
```

## Exit Code Decision Tree

```
Has errors?
    ↓ Yes → exit(2) BLOCK
    ↓ No
Has blocking warnings?
    ↓ Yes → exit(2) BLOCK
    ↓ No
Has quality warnings?
    ↓ Yes → exit(0) WARN (don't block)
    ↓ No
→ exit(0) PASS
```

## Gate Script Usage

```python
# require-gate: Blocks if gate not passed
def cmd_require_gate(name):
    state = load_state()
    if not state:
        sys.exit(0)  # No workflow = allow
    if state["gates_passed"].get(name):
        sys.exit(0)  # Gate passed = allow
    else:
        sys.exit(2)  # BLOCK

# check-gate: Just reports status
def cmd_check_gate(name):
    passed = state["gates_passed"].get(name)
    sys.exit(0 if passed else 1)  # 0=passed, 1=not passed
```

## Common Mistakes

### Mistake 1: Using exit(1) to block

```python
# WRONG - exit(1) may not block
if errors:
    sys.exit(1)

# CORRECT - exit(2) always blocks
if errors:
    sys.exit(2)
```

### Mistake 2: Blocking on all warnings

```python
# WRONG - blocks advisory warnings
if warnings:
    sys.exit(2)

# CORRECT - only block on blocking codes
if has_blocking_issues():
    sys.exit(2)
```

### Mistake 3: Blocking when no workflow

```python
# WRONG - blocks normal operations
if not state:
    sys.exit(2)

# CORRECT - allow when no workflow active
if not state:
    sys.exit(0)  # No workflow = allow
```
