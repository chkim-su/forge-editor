# Comment Hygiene

Rules for TODO, FIXME, debug code, and comment quality.

## Comment Categories

| Pattern | Severity | Policy |
|---------|----------|--------|
| `TODO:` | ADVISORY | Track, resolve before major release |
| `FIXME:` | BLOCKING | Must resolve before any deployment |
| `XXX:` | ADVISORY | Technical debt marker |
| `HACK:` | ADVISORY | Known workaround |
| `DEBUG:` | BLOCKING | Remove before deployment |
| Commented-out code | ADVISORY | Remove or document why kept |

## Detection Patterns

```regex
# TODO patterns
TODO|TODO:|TODO\s*\(|@todo

# FIXME patterns
FIXME|FIXME:|BUG:|@fixme

# Debug patterns
console\.log\(|print\(.*debug|debugger;|pdb\.set_trace

# Commented code (heuristic)
#\s*(if|for|while|def|class|return|import)\s
```

## Pre-Deployment Checklist

Before `plugin_publish`:

- [ ] No `FIXME:` comments remain
- [ ] No `DEBUG:` markers
- [ ] No `console.log` debug statements
- [ ] No `print()` debug statements (non-status)
- [ ] No `debugger;` statements
- [ ] No `pdb.set_trace()` calls

## Acceptable Debug Code

When debug code must remain:

```python
# DEBUG-KEEP: Required for production monitoring
if os.environ.get("DEBUG"):
    print(f"Debug: {value}")
```

Mark with `DEBUG-KEEP:` and provide justification.

## Comment Quality Rules

### Good Comments

```python
# Validate schema before processing to catch malformed input early
def validate_schema(data):
    ...
```

### Bad Comments

```python
# Check if valid
def validate_schema(data):  # This checks schema
    ...  # Do validation
```

### Rules

1. Explain WHY, not WHAT
2. Keep comments current with code
3. Remove outdated comments
4. Use docstrings for public APIs

## Validation Integration

| Check | Code | Enforcement |
|-------|------|-------------|
| FIXME detection | (future) | BLOCKING for publish |
| DEBUG detection | (future) | BLOCKING for publish |
| TODO count | (info) | Report only |

## Cleanup Commands

```bash
# Find all TODO/FIXME
grep -rn "TODO\|FIXME" --include="*.py" --include="*.md"

# Find debug statements
grep -rn "console\.log\|print(" --include="*.py" --include="*.js"

# Find commented code
grep -rn "^#\s*\(if\|for\|def\|class\)" --include="*.py"
```

## Resolving Comments

| Pattern | Resolution |
|---------|------------|
| `TODO:` | Implement or create issue |
| `FIXME:` | Fix immediately |
| `XXX:` | Refactor or document technical debt |
| `HACK:` | Create proper solution or document |
| Commented code | Delete or restore with explanation |
