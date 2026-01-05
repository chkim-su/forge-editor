# Content Quality Validation Guide

## Your Task

Validate all description fields in the plugin for quality and completeness.

## Files to Check

1. **Commands** (`commands/*.md`): Check `description` in frontmatter
2. **Agents** (`agents/*.md`): Check `description` in frontmatter
3. **Skills** (`skills/*/SKILL.md`): Check `description` in frontmatter

## Validation Criteria

### Description Quality

**FAIL conditions:**
- Empty or missing description
- Contains "TODO" or placeholder text
- Less than 20 characters
- Generic text like "A command for..." without specifics

**PASS conditions:**
- Clearly explains what the component does
- Includes trigger phrases for skills (e.g., "Use when user asks to...")
- Specific and actionable

### Examples

**FAIL:**
```yaml
description: TODO
description: A skill
description: Does stuff
```

**PASS:**
```yaml
description: Create PowerPoint presentations with slides, tables, and charts. Use when user asks to "make slides" or "create presentation".
```

## Output Format

Return JSON:
```json
{
  "task": "content",
  "status": "pass" or "fail",
  "issues": [
    {"file": "commands/foo.md", "field": "description", "problem": "Contains TODO"},
    {"file": "skills/bar/SKILL.md", "field": "description", "problem": "Too short (15 chars)"}
  ]
}
```

If no issues, return empty issues array with status "pass".
