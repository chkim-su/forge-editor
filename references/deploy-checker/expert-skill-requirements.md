# Expert Skill Requirements Guide

## Your Task

Identify skills that qualify as "expert skills" and validate their completeness.

## Expert Skill Detection

A skill is an **expert skill** if ANY of these are true:
- Has `scripts/validation/` directory
- Has 4+ files in `references/`
- Handles complex file formats (PDF, PPTX, XLSX, DOCX)
- Description mentions "complex", "advanced", or format-specific operations

## Expert Skill Requirements

Expert skills MUST have:

### 1. Comprehensive References (required)
```
skills/my-skill/
├── references/
│   ├── format-structure.md      # Internal format documentation
│   ├── troubleshooting.md       # Known issues and workarounds
│   ├── library-limitations.md   # What the library can't do
│   └── edge-cases.md            # Gotchas and special cases
```

### 2. Validation Scripts (required)
```
skills/my-skill/
├── scripts/
│   └── validation/
│       └── validate_output.py   # Verify output correctness
```

### 3. Assets (recommended)
```
skills/my-skill/
├── assets/
│   ├── templates/               # Starting templates
│   └── examples/                # Example outputs
```

## Validation Process

For each skill:
1. Check if it qualifies as expert skill
2. If yes, verify all required components exist
3. Check reference files have actual content (not just TODOs)

## Output Format

Return JSON:
```json
{
  "task": "expert-skill",
  "status": "pass" or "fail",
  "issues": [
    {"skill": "pptx-builder", "missing": "references/troubleshooting.md"},
    {"skill": "pdf-processor", "missing": "scripts/validation/"}
  ]
}
```

If no expert skills or all complete, return status "pass" with empty issues.
