---
name: diagnose
description: "Quick codebase analysis without full Forge workflow"
---

# /diagnose - Codebase Analysis

Run the Analysis phase directly to understand a codebase without activating the full Forge workflow.

## Purpose

Quick analysis for:
- Understanding existing code structure
- Identifying patterns and conventions
- Finding integration points
- Assessing project type

## Usage

Describe what you want to analyze:

```
/diagnose [description of what to analyze]
```

## Examples

```
/diagnose the authentication system
/diagnose how errors are handled
/diagnose existing plugin structure
/diagnose test patterns
```

## How It Works

This command runs the Analysis agent directly:

```
Task(subagent_type="forge:analysis-agent", prompt="[your description]")
```

Unlike the full Forge workflow (`/forge`), this:
- Does NOT activate forge state
- Does NOT enforce phase gates
- Does NOT track checkpoints
- Is purely informational

## When to Use

| Situation | Use `/diagnose` | Use `/forge` |
|-----------|-----------------|--------------|
| Just exploring | ✓ | |
| Planning new work | ✓ | |
| Building a plugin | | ✓ |
| Refactoring | | ✓ (or `/refactor`) |
| Quick questions | ✓ | |

## Output

The Analysis agent will provide:

```markdown
## Codebase Analysis

### Project Type
[Identified project type and technology stack]

### Structure Overview
[Directory and file organization]

### Relevant Existing Code
[Components relevant to your query]

### Patterns Identified
[Coding conventions and architecture patterns]

### Integration Points
[Where new code would connect]

### Observations
[Key insights for your question]
```

## Next Steps

After diagnosis, you might:
- Start full workflow: `/forge`
- Jump to design: `/design`
- Start refactoring: `/refactor`
