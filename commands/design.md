---
name: design
description: "Design options synthesis without full Forge workflow"
---

# /design - Design Options

Run the Design phase directly when you already understand the problem and need design options.

## Purpose

Generate design options for:
- Architecture decisions
- Component structure
- Implementation approaches
- Technology choices

## Usage

Provide context and constraints:

```
/design [description of what needs designing]
```

## Examples

```
/design a caching layer for API responses
/design plugin structure for code review automation
/design error handling strategy
/design database schema for user preferences
```

## Prerequisites

Before using `/design`, you should have:
- Clear understanding of the problem
- Knowledge of existing codebase patterns
- Identified constraints and requirements

If you don't have these, use `/diagnose` first.

## How It Works

This command runs the Design agent directly:

```
Task(subagent_type="forge:design-agent", prompt="[your description]")
```

Unlike the full Forge workflow, this:
- Does NOT activate forge state
- Does NOT require prior analysis phase
- Does NOT enforce phase gates
- Is for quick design exploration

## Output

The Design agent will provide neutral options:

```markdown
## Design Options

### Option A: [Name]
**Approach:** [Description]
**Components:** [What gets created]
**Trade-offs:** [Pros and cons]

### Option B: [Name]
[Same structure]

### Option C: [Name]
[Same structure]

## Trade-off Comparison
[Matrix comparing aspects]

## User Selection Required
[Ask user to choose, specify default]
```

## Key Principles

1. **Neutral presentation** - No recommendations, only trade-offs
2. **Meaningful options** - Options should differ substantively
3. **Honest trade-offs** - Don't hide complexity or risks
4. **User decides** - Present facts, let user choose

## Next Steps

After design selection:
- Implement directly (if simple)
- Use full workflow for complex implementations: `/forge`
- Create a plan before implementing
