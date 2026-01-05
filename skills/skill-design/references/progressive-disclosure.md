# Progressive Disclosure Pattern

Minimize context consumption by loading information only when needed.

## Three-Layer Information Architecture

```
Layer 1: Metadata (frontmatter)     → Always loaded
Layer 2: SKILL.md body              → Loaded on skill activation
Layer 3: references/, scripts/      → Loaded on explicit request
```

### Layer 1: Metadata (Always Loaded)
```yaml
---
name: my-skill
description: |
  One-line summary. Trigger phrases: "phrase1", "phrase2"
allowed-tools: ["Read", "Write", "Bash"]
---
```
**Size:** ~100-200 chars
**Purpose:** Discovery, matching, tool permissions

### Layer 2: SKILL.md Body (On Activation)
```markdown
# My Skill

2-3 sentence overview.

## Quick Start
Minimal instructions to get started.

## Core Flow
1. Step 1
2. Step 2
3. Step 3

---
For details: [references/detailed-guide.md](references/detailed-guide.md)
```
**Size:** 50 lines or less
**Purpose:** High-level flow, entry points, navigation

### Layer 3: References (On Demand)
```
references/
├── detailed-guide.md      # Full documentation
├── troubleshooting.md     # Problem solutions
├── examples/              # Code examples
└── api-reference.md       # Detailed API docs

scripts/
├── main.py                # Executed, not read into context
└── helpers.py             # Executed, not read into context
```
**Size:** Unlimited
**Purpose:** Deep knowledge, examples, edge cases


## Context Optimization Rules

### Rule 1: SKILL.md ≤ 50 Lines
Move everything else to references/

**Before (150 lines):**
```markdown
# PDF Processor

## Overview
Long explanation of what this does...
Multiple paragraphs of context...

## Detailed API Reference
Function 1: ...
Function 2: ...
[100+ lines of documentation]
```

**After (40 lines):**
```markdown
# PDF Processor

Extract text and images from PDFs.

## Quick Start
python scripts/extract.py input.pdf output/

## Available Operations
| Operation | Script | Usage |
|-----------|--------|-------|
| Extract text | extract.py | extract.py <input> <output> |
| Merge PDFs | merge.py | merge.py <files...> <output> |

---
Details: [references/api-reference.md](references/api-reference.md)
```


### Rule 2: Scripts Execute, Don't Load
Scripts are executed via Bash, not read into context.

**Wrong:**
```markdown
Read scripts/process.py to understand how it works, then execute it.
```

**Correct:**
```markdown
Execute: python scripts/process.py input output
```


### Rule 3: Reference Links Are Navigation
End sections with explicit links to deeper content.

```markdown
## Error Handling

Common errors are handled automatically.

---
For troubleshooting: [references/troubleshooting.md](references/troubleshooting.md)
```


### Rule 4: Examples in Separate Files
Long examples belong in references/ or assets/.

**In SKILL.md:**
```markdown
## Example

```python
# Simple example (3-5 lines max)
result = process(input)
print(result)
```

For complex examples: [references/examples/](references/examples/)
```


## Directory Role Separation

| Directory | Context Load | Purpose |
|-----------|-------------|---------|
| SKILL.md | Always (on use) | Flow, navigation |
| references/ | On explicit Read | Deep knowledge |
| scripts/ | Never (executed) | Automation |
| assets/ | Never (used by scripts) | Templates, data |


## Anti-Patterns

### Anti-Pattern 1: Monolithic SKILL.md
❌ Everything in one 500-line file

✅ 50-line SKILL.md + references/

### Anti-Pattern 2: Inline Documentation
❌ Detailed explanations in SKILL.md flow

✅ Link to references/, keep flow concise

### Anti-Pattern 3: Reading Scripts
❌ "Read scripts/main.py to understand..."

✅ "Execute: python scripts/main.py"

### Anti-Pattern 4: Repeated Content
❌ Same information in SKILL.md and references/

✅ Single source of truth in references/, SKILL.md links to it


## Measurement

Check your skill's context efficiency:

```bash
# Count SKILL.md lines
wc -l skills/my-skill/SKILL.md
# Target: ≤ 50

# Count total reference size
wc -l skills/my-skill/references/*.md
# No limit, but organize well
```
