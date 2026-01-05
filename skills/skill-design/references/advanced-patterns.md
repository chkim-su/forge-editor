# Advanced Skill Design Patterns

This document provides advanced patterns for complex skill scenarios.

## Skill Type Decision Tree

```
Does the skill involve file manipulation?
├── Yes
│   └── Same operation repeatedly?
│       ├── Yes → Tool Skill (scripts/)
│       └── No → Hybrid Skill (scripts/ + references/)
└── No
    └── Is there a preferred approach?
        ├── Yes, with variations → Hybrid Skill
        └── Multiple valid approaches → Knowledge Skill
```

## Script Design Patterns

### Pattern 1: Standalone Script with argparse

Every script should be independently executable:

```python
#!/usr/bin/env python3
"""
Brief description of what the script does.

Usage:
    python script.py <required_arg> [--optional <value>]

Examples:
    python script.py input.pdf output.txt
    python script.py input.pdf output.txt --verbose
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Validate inputs
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Main logic
    try:
        process(input_path, Path(args.output), verbose=args.verbose)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def process(input_path: Path, output_path: Path, verbose: bool = False) -> None:
    """Core processing logic."""
    if verbose:
        print(f"Processing {input_path}...")
    # Implementation here
    print(f"Done! Output: {output_path}")


if __name__ == "__main__":
    main()
```

### Pattern 2: Script Suite with Shared Utilities

For skills with multiple related scripts:

```
skill-name/
├── scripts/
│   ├── __init__.py       # Empty or shared imports
│   ├── utils.py          # Shared utilities
│   ├── operation1.py     # Main script 1
│   └── operation2.py     # Main script 2
```

**utils.py**:
```python
"""Shared utilities for skill scripts."""
from pathlib import Path

def validate_file(path: Path, extension: str = None) -> Path:
    """Validate file exists and optionally check extension."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if extension and path.suffix.lower() != extension.lower():
        raise ValueError(f"Expected {extension} file, got: {path.suffix}")
    return path
```

**operation1.py**:
```python
#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils import validate_file
# ... rest of script
```

## Progressive Disclosure Patterns

### Pattern 1: Framework-Specific References

```
cloud-deploy/
├── SKILL.md              # Core workflow + framework selection
└── references/
    ├── aws.md            # AWS-specific patterns
    ├── gcp.md            # GCP-specific patterns
    └── azure.md          # Azure-specific patterns
```

**SKILL.md**:
```markdown
## Select Your Cloud Provider

Based on your infrastructure, choose the appropriate guide:

- **AWS**: See [references/aws.md](references/aws.md) for EC2, Lambda, ECS
- **GCP**: See [references/gcp.md](references/gcp.md) for Compute, Cloud Run, GKE
- **Azure**: See [references/azure.md](references/azure.md) for VMs, Functions, AKS

The core deployment principles below apply to all providers.
```

### Pattern 2: Complexity Levels

```markdown
## Quick Start

[Minimal instructions for common case]

## Standard Usage

[More detailed instructions with options]

## Advanced Configuration

See [references/advanced.md](references/advanced.md) for:
- Custom configurations
- Edge cases
- Performance tuning
```

### Pattern 3: Large Reference Files

For files >100 lines, include a table of contents:

```markdown
# API Reference

## Table of Contents

- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Users](#users)
  - [Products](#products)
- [Error Codes](#error-codes)
- [Rate Limiting](#rate-limiting)

---

## Authentication
...
```

## Asset Usage Patterns

### Pattern 1: Project Templates

```
skill-name/
└── assets/
    └── template/
        ├── package.json
        ├── tsconfig.json
        ├── src/
        │   └── index.ts
        └── README.md
```

**Usage in SKILL.md**:
```markdown
## Initialize New Project

Copy the template to your project:

```bash
cp -r ${SKILL_ROOT}/assets/template ./my-project
cd my-project
npm install
```
```

### Pattern 2: Document Templates

```
skill-name/
└── assets/
    ├── report-template.docx
    ├── presentation-template.pptx
    └── brand/
        ├── logo.png
        └── colors.json
```

**Usage in SKILL.md**:
```markdown
## Generate Report

Use the template as a starting point:

```python
from docx import Document
doc = Document('${SKILL_ROOT}/assets/report-template.docx')
# Modify and save
```
```

## Multi-Phase Workflow Skills

For complex multi-step processes:

```markdown
## Deployment Workflow

### Phase 1: Validation

```bash
# Run validation script
python scripts/validate.py --config deployment.yaml
```

If validation fails, see [references/troubleshooting.md](references/troubleshooting.md).

### Phase 2: Build

```bash
# Build artifacts
python scripts/build.py --env production
```

### Phase 3: Deploy

```bash
# Deploy to target environment
python scripts/deploy.py --env production --dry-run
# If dry-run looks good:
python scripts/deploy.py --env production
```

### Phase 4: Verify

```bash
# Run health checks
python scripts/verify.py --env production
```
```

## Conditional Logic in Skills

Skills can provide different guidance based on context:

```markdown
## Framework Detection

First, detect your framework:

```bash
# Check for package.json (Node.js)
# Check for requirements.txt (Python)
# Check for go.mod (Go)
```

### If Node.js

[Node.js specific instructions]

### If Python

[Python specific instructions]

### If Go

[Go specific instructions]
```

## Error Recovery Patterns

```markdown
## Troubleshooting

### Error: "Connection refused"

**Cause**: Service not running or wrong port.

**Fix**:
```bash
# Check if service is running
python scripts/health_check.py

# Restart if needed
python scripts/restart_service.py
```

### Error: "Permission denied"

**Cause**: Insufficient file permissions.

**Fix**:
```bash
# Check permissions
ls -la target_file

# Fix permissions
chmod +x target_file
```
```

## Testing Skills

Include self-testing guidance:

```markdown
## Verify This Skill Works

### Test Scripts

```bash
# Test each script
python scripts/operation1.py --help  # Should show usage
python scripts/operation1.py test_input.pdf test_output.pdf  # Should succeed
```

### Test Workflow

1. Create test input files
2. Run through complete workflow
3. Verify outputs match expected results

### Common Test Cases

| Input | Expected Output | Script |
|-------|-----------------|--------|
| sample.pdf | sample.txt | extract_text.py |
| portrait.pdf | landscape.pdf | rotate_page.py |
```

## Skill Composition

While skills don't call other skills directly, they can suggest orchestrators:

```markdown
## For Complex Workflows

This skill handles **PDF processing** only.

For workflows involving multiple domains, consider:
- Use an orchestrator agent that combines:
  - pdf-processor (this skill)
  - data-analyzer
  - report-generator

Example orchestrator: `fullstack-orchestrator` agent
```

## Security-Conscious Skills

```markdown
## Security Checklist

Before using file processing scripts:

- [ ] Input files from trusted sources
- [ ] Output directory has appropriate permissions
- [ ] No sensitive data in file paths logged
- [ ] Temporary files cleaned up

## Sensitive Data Handling

**Never** include in logs:
- File contents
- Personal data
- Credentials

**Always** sanitize:
- User-provided file names
- Path arguments
```

## Performance Considerations

```markdown
## For Large Files

### Memory Management

For files >100MB, use streaming:

```bash
python scripts/process.py large_file.pdf --stream
```

### Batch Processing

For multiple files:

```bash
python scripts/batch_process.py input_dir/ output_dir/ --parallel 4
```

### Progress Reporting

For long operations, use verbose mode:

```bash
python scripts/process.py input.pdf output.pdf --verbose
```
```
