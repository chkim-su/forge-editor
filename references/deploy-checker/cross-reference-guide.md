# Cross-Reference Validation Guide

## Your Task

Verify all internal links and file references are valid.

## What to Check

### 1. Markdown Links in SKILL.md
```markdown
See [references/patterns.md](references/patterns.md) for details.
```
→ Verify `references/patterns.md` exists

### 2. Script References
```markdown
Run `scripts/validate.py` to check output.
```
→ Verify `scripts/validate.py` exists

### 3. Agent Skill References
```yaml
# In agents/*.md frontmatter
skills: my-skill
```
→ Verify `skills/my-skill/SKILL.md` exists

### 4. Asset References
```markdown
Use template from `assets/templates/base.pptx`
```
→ Verify file exists

## Validation Process

1. Read each `.md` file in commands/, agents/, skills/
2. Extract all file references (markdown links, code blocks mentioning files)
3. Verify each referenced file exists
4. Report broken references

## Common Patterns to Check

```regex
\[.*?\]\((.*?)\)           # Markdown links
`(scripts/.*?\.py)`        # Script references
`(references/.*?\.md)`     # Reference file mentions
`(assets/.*?)`             # Asset references
skills:\s*(\S+)            # Agent skill references
```

## Output Format

Return JSON:
```json
{
  "task": "cross-ref",
  "status": "pass" or "fail",
  "issues": [
    {"file": "skills/foo/SKILL.md", "broken_ref": "references/missing.md"},
    {"file": "agents/bar.md", "broken_ref": "skills/nonexistent"}
  ]
}
```

If all references valid, return status "pass" with empty issues.
