# Style Guidelines

Rules for emoji usage and formatting in plugin content.

## Emoji Policy

**No emoji in code logic. Emoji OK in user-facing output.**

## Where Emoji is Prohibited

| Location | Reason | Fix |
|----------|--------|-----|
| Python/JS/TS logic | Professionalism, portability | Remove or use text |
| Variable/function names | Parsing issues | Use descriptive text |
| Frontmatter fields | YAML parsing | Remove completely |
| Error exceptions | Logging/debugging | Use text descriptions |
| JSON keys | Schema validation | Use alphanumeric |

## Where Emoji is Acceptable

| Location | Purpose | Example |
|----------|---------|---------|
| CLI status output | Visual feedback | `print("OK")` |
| Markdown headers | Visual hierarchy | `## Process` |
| User documentation | Engagement | Lists with emoji bullets |
| Status indicators | Quick recognition | Build status badges |

## Detection Pattern

Emoji ranges detected:
- Emoticons: U+1F600-U+1F64F
- Symbols: U+1F300-U+1F5FF
- Transport: U+1F680-U+1F6FF
- Flags: U+1F1E0-U+1F1FF
- Dingbats: U+2700-U+27BF
- Misc Symbols: U+2600-U+26FF

## Exemption Markers

```python
# status-indicator
print("OK Build passed")

# ui-element
status = "Running..."

# user-facing
message = "Success!"
```

## Validation Behavior

| Workflow | Detection | Action |
|----------|-----------|--------|
| Creation workflows | W038 warning | Inform, allow proceed |
| `plugin_publish` | W038 error | Block until fixed |
| Analysis | W038 info | Report only |

## Fixing W038

1. Remove emoji from code logic
2. If status indicator: Add `# status-indicator` marker
3. If user-facing: Add `# user-facing` marker
4. Replace with text equivalent when possible

## Text Alternatives

| Emoji | Text Alternative |
|-------|------------------|
| checkmark | `[OK]`, `[PASS]`, `SUCCESS` |
| cross mark | `[FAIL]`, `[ERROR]`, `FAILED` |
| warning | `[WARN]`, `WARNING:` |
| info | `[INFO]`, `NOTE:` |
| arrow | `->`, `-->`, `=>` |
