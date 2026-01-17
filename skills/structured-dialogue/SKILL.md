---
name: structured-dialogue
description: "Standard question format for Forge workflow phases"
triggers:
  - "structured dialogue"
  - "question format"
  - "how to ask"
  - "dialogue contract"
---

# Structured Dialogue Contract

Standard format for asking questions during Forge workflow phases.

## Purpose

When agents need user input, they use this consistent format to:
- Provide clear context
- Present options neutrally
- Show trade-offs
- Specify default behavior

## Required Format

```markdown
### [ID]: [Short Title]

**Context:** [Why this matters - 1-2 sentences explaining the decision's impact]

**Options:**
- A: [Clear description of option]
- B: [Clear description of option]
- C: [Clear description of option] (optional)
- D: [Clear description of option] (optional)

**Trade-offs:**
| Option | Pros | Cons |
|--------|------|------|
| A | [Benefits] | [Drawbacks] |
| B | [Benefits] | [Drawbacks] |
| C | [Benefits] | [Drawbacks] |

**Default:** [Option letter] if no preference stated
```

## Format Rules

1. **Never recommend** - present trade-offs only
2. **Always explain context first** - user needs to understand why this matters
3. **Maximum 4 options** - more creates decision paralysis
4. **Include trade-off matrix** - visual comparison helps
5. **Specify default behavior** - reduces friction for common cases

## Examples

### Good Example

```markdown
### Q1: Component Structure

**Context:** Your plugin can organize commands as individual files or grouped by feature. This affects how Claude discovers and executes them.

**Options:**
- A: Flat structure - all commands in `commands/` directory
- B: Grouped structure - commands organized by feature subdirectories
- C: Hybrid - common commands flat, feature-specific in subdirectories

**Trade-offs:**
| Option | Pros | Cons |
|--------|------|------|
| A | Simple, easy to find | Can get cluttered with many commands |
| B | Organized, scalable | More navigation, harder discovery |
| C | Balanced | Requires consistent organization rules |

**Default:** A (flat structure) if no preference stated
```

### Bad Example (Don't Do This)

```markdown
### Question

I recommend Option A because it's the best choice. 

Options:
- A: The recommended approach (best!)
- B: An alternative (not as good)

Which do you prefer?
```

**Problems:**
- Recommends instead of presenting neutrally
- Biased language ("best", "not as good")
- No context or trade-offs
- No default specified

## When to Use Structured Dialogue

| Situation | Use Structured Dialogue |
|-----------|------------------------|
| Architecture decisions | Yes |
| Technology choices | Yes |
| File organization | Yes |
| Simple yes/no questions | No (just ask directly) |
| Factual clarifications | No (just ask directly) |
| User preferences | Yes |

## Integration with AskUserQuestion

When using the `AskUserQuestion` tool, map the structured dialogue to its format:

```json
{
  "questions": [{
    "question": "[Full question with context]",
    "header": "[Short title]",
    "options": [
      {"label": "Option A", "description": "[Description + trade-offs]"},
      {"label": "Option B", "description": "[Description + trade-offs]"},
      {"label": "Option C", "description": "[Description + trade-offs]"}
    ],
    "multiSelect": false
  }]
}
```

## Phase-Specific Usage

| Phase | Dialogue Purpose |
|-------|------------------|
| 0 - Input | Clarify requirements, scope |
| 1 - Analysis | Confirm analysis findings |
| 2 - Design | Select design option |
| 3 - Execute | Confirm before implementation |
| 4 - Validate | Address validation issues |

## Neutral Language Guide

**Instead of:** "I recommend..."
**Use:** "Consider the trade-offs above."

**Instead of:** "The best option is..."
**Use:** "Options differ in..."

**Instead of:** "You should..."
**Use:** "If you prefer X, then..."

**Instead of:** "Option A is better because..."
**Use:** "Option A provides X at the cost of Y."
