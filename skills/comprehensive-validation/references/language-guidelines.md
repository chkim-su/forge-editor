# Language Guidelines

Rules for Korean vs English usage in plugin content.

## Core Rule

**English for LLM-consumed content, localized text only for user-facing output.**

## Where English is Required

| Location | Reason | Example |
|----------|--------|---------|
| `skills/*/SKILL.md` | LLM prompt comprehension | Description, process, examples |
| `agents/*.md` | Task tool prompt parsing | Description, success criteria |
| `commands/*.md` | Slash command expansion | Prompt content |
| Frontmatter fields | YAML parsing reliability | `name`, `description`, `tools` |
| Code comments | Maintenance by any developer | `# Validate input parameters` |
| Variable/function names | Code readability | `def validate_schema():` |
| Error messages (thrown) | Debugging/logging | `raise ValueError("Invalid config")` |

## Where Korean is Acceptable

| Location | Condition | Example |
|----------|-----------|---------|
| CLI output (`print()`) | User-facing status | `print("Validation completed")` |
| User prompts | Interactive UI | `input("Enter name: ")` |
| Localization files | `i18n/`, `locales/`, `ko/` | `messages.ko.json` |
| Marked content | Comment marker present | `# i18n: User message` |
| Documentation in `/docs/ko/` | Explicit localization | Korean user guide |

## Detection Pattern

Korean text is detected using Unicode ranges:
- Hangul Syllables: U+AC00-U+D7AF
- Hangul Jamo: U+1100-U+11FF
- Hangul Compatibility: U+3130-U+318F

## Exemption Markers

Add these markers to exempt intentional Korean:

```python
# i18n: User-facing message
print("Korean text here is OK")

# user-facing
message = "Korean text here is OK"
```

## Validation Behavior

| Workflow | Detection | Action |
|----------|-----------|--------|
| Creation workflows | W037 warning | Inform, allow proceed |
| `plugin_publish` | W037 error | Block until fixed |
| Analysis | W037 info | Report only |

## Fixing W037

1. Translate Korean to English
2. If intentional: Add `# i18n` marker
3. If localization: Move to `i18n/` directory
