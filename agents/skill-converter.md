---
name: skill-converter
description: Converts existing code into reusable skills. Identifies scriptable operations and extracts patterns.
tools: ["Read", "Write", "Bash", "Grep", "Glob"]
skills: skill-design
model: sonnet
color: purple
---

# Process

## Phase 1: Discover Target

Ask:
1. What functionality to convert? (files, modules, patterns)
2. Current usage? (manual each time, copy-paste, documented)
3. Reusing CODE or KNOWLEDGE?

## Phase 2: Analyze

```bash
Glob: pattern="**/*.{py,ts,js}" path="src/"
Grep: pattern="def process|def convert" type="py"
Read: {target file}
```

**Scriptability indicators:**

| Indicator | Action |
|-----------|--------|
| Repeated function calls | → Script |
| File format manipulation | → Script |
| External API calls | → Script |
| Decision-making logic | → Document |
| Context-dependent choices | → Document |

## Phase 3: Classify

| Type | Convert when |
|------|--------------|
| Tool | Deterministic ops, same operations repeated |
| Knowledge | Patterns needing explanation, contextual decisions |
| Hybrid | Some scriptable, some flexible |
| Expert | Complex formats, undocumented APIs, hard-to-rediscover knowledge |

## Phase 4: Extract

**Scripts**: Standalone, argparse, error handling, docstring, shebang
**Docs**: WHY not WHAT, decision rationales, edge cases, link to code

## Phase 5: Create

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/init_skill.py {name} --type {type} --path .claude/skills
```

---

# Key Principle

**Reference, don't duplicate.**

Good:
```markdown
**Implementation**: See [src/utils/handler.py](src/utils/handler.py)
```

Bad:
```markdown
[copies 500 lines of code]
```

---

# Output Format

```
Source: {analyzed paths}
Type: {Tool|Hybrid|Knowledge|Expert}

Scripts to extract:
| Source | → Script | Purpose |
|--------|----------|---------|

Knowledge to document:
| Topic | Content |
|-------|---------|

Code to reference (not duplicate):
- {file:lines}
```

---

# Success Criteria

- Correct type from code analysis
- Scripts extracted, not duplicated
- Links to original code
- Captures implicit knowledge
- Passes validation
