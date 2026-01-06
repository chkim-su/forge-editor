---
name: comprehensive-validation
description: Language, style, and comment quality guidelines for plugin content
category: quality
tools: []
---

# Comprehensive Validation

Guidelines for content quality: language usage, emoji placement, and comment hygiene.

## Core Principle

**English for LLM consumption, localized text only for user-facing output.**

## When to Use

- Before `plugin_publish` workflow
- When W037 (Korean) or W038 (emoji) warnings appear
- Reviewing documentation quality
- Cleaning up debug artifacts

## Quick Reference

| Content Type | Rule | Example |
|--------------|------|---------|
| Skill/Agent descriptions | English only | `description: "Analyze code quality"` |
| Code comments | English only | `# Check file existence` |
| CLI output (print/console.log) | OK to localize | `print("Success")` or `print("OK")` |
| Error messages in exceptions | English preferred | `raise ValueError("Invalid input")` |
| Frontmatter fields | English only | Never use emoji/Korean in YAML |
| Markdown headers | English preferred | `## Process` not `## 프로세스` |

## Validation Codes

| Code | Check | Enforcement |
|------|-------|-------------|
| W037 | Korean in non-localized content | Warning (BLOCKING for publish) |
| W038 | Emoji in inappropriate locations | Warning (BLOCKING for publish) |

## Enforcement Levels

| Workflow | W037/W038 |
|----------|-----------|
| `skill_creation` | WARNING |
| `agent_creation` | WARNING |
| `command_creation` | WARNING |
| `plugin_publish` | **BLOCKING** |
| `quick_fix` | WARNING |
| `analyze_only` | WARNING |

## Cleanup Commands

```bash
# Run validation to detect issues
python3 scripts/validate_all.py . --content-quality

# Detailed semantic analysis (uses content-quality-analyzer agent)
# Requires Task tool invocation with form-selection-auditor
```

## References

- `references/language-guidelines.md` - When Korean vs English
- `references/style-guidelines.md` - Emoji and formatting rules
- `references/comment-hygiene.md` - TODO/FIXME/debug code rules
