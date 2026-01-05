#!/usr/bin/env python3
"""
Initialize a new skill directory with proper structure.

Usage:
    python init_skill.py <skill-name> [--path <output-directory>] [--type <type>] [--structure <structure>]

Type: Determines tools and directories (knowledge, hybrid, tool, expert)
Structure: Determines SKILL.md organization (workflow, task, reference, capabilities)

Examples:
    python init_skill.py my-skill
    python init_skill.py my-skill --path .claude/skills
    python init_skill.py pdf-processor --type tool --structure task
    python init_skill.py deploy-checker --type hybrid --structure workflow
    python init_skill.py code-style --type knowledge --structure reference
"""

import argparse
import os
import sys
from pathlib import Path

SKILL_TYPES = {
    "knowledge": {
        "description": "Knowledge-based skill for analysis, guidance, and best practices",
        "tools": '["Read", "Grep", "Glob"]',
        "dirs": ["references"],
        "scripts": False,
        "assets": False,
    },
    "hybrid": {
        "description": "Hybrid skill combining guidance with helper scripts",
        "tools": '["Read", "Write", "Grep", "Glob", "Bash"]',
        "dirs": ["references", "scripts"],
        "scripts": True,
        "assets": True,
    },
    "tool": {
        "description": "Tool skill for file manipulation and automation",
        "tools": '["Read", "Write", "Bash"]',
        "dirs": ["scripts", "references"],
        "scripts": True,
        "assets": True,
    },
    "expert": {
        "description": "Expert domain skill with comprehensive docs (OOXML, complex formats, etc.)",
        "tools": '["Read", "Write", "Bash"]',
        "dirs": ["scripts", "scripts/validation", "references", "assets/templates", "assets/examples"],
        "scripts": True,
        "assets": True,
        "expert_refs": ["internal-structure.md", "troubleshooting.md", "library-limitations.md", "edge-cases.md"],
    },
}

# Structure patterns (orthogonal to skill type)
STRUCTURE_PATTERNS = {
    "workflow": "Sequential multi-step tasks with decision points",
    "task": "Single-purpose input->process->output transformation",
    "reference": "Rules, standards, and best practices documentation",
    "capabilities": "Toolkit of related features/functions",
}


def create_structure_template(skill_name: str, structure: str, tools: str) -> str:
    """Generate SKILL.md content based on structure pattern."""
    title = skill_name.replace("-", " ").title()

    if structure == "workflow":
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what this skill does.
  Trigger phrases: "phrase1", "phrase2"
allowed-tools: {tools}
---

# {title}

TODO: 2-3 sentence overview.

## Step 1: [Initial Action]

TODO: First step instructions.

**Script:** `python scripts/step1.py`

→ If success: Continue to Step 2
→ If error: STOP and report

## Step 2: [Processing]

TODO: Second step instructions.

→ If condition A: Go to Step 3a
→ If condition B: Go to Step 3b

## Step 3a: [Branch A]

TODO: Branch A instructions.

## Step 3b: [Branch B]

TODO: Branch B instructions.

## Step 4: [Finalization]

TODO: Final step.

---

For details: [references/workflow-details.md](references/workflow-details.md)
'''

    elif structure == "task":
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what this skill does.
  Trigger phrases: "phrase1", "phrase2"
allowed-tools: {tools}
---

# {title}

TODO: 2-3 sentence overview.

## Input

- **Required:** `input_file` - Description
- **Optional:** `--option` - Description

## Process

```bash
python scripts/process.py <input> <output> [options]
```

## Output

- **Format:** TODO (JSON, file, etc.)
- **Location:** TODO

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `process.py` | Main processing | `python scripts/process.py input output` |
| `validate.py` | Validate output | `python scripts/validate.py output` |

---

For details: [references/processing-details.md](references/processing-details.md)
'''

    elif structure == "reference":
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what guidelines/standards this provides.
  Trigger phrases: "phrase1", "phrase2"
allowed-tools: {tools}
---

# {title}

TODO: 2-3 sentence overview of these guidelines.

## Core Rules

### Rule 1: [Name]

- **Do:** TODO
- **Don't:** TODO

### Rule 2: [Name]

- **Do:** TODO
- **Don't:** TODO

## Quick Reference

| Scenario | Recommendation |
|----------|---------------|
| A | Do X |
| B | Do Y |

## Examples

### Good Example

```
TODO: Show correct approach
```

### Bad Example

```
TODO: Show incorrect approach
```

---

For details: [references/detailed-guidelines.md](references/detailed-guidelines.md)
'''

    else:  # capabilities
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what capabilities this provides.
  Trigger phrases: "phrase1", "phrase2"
allowed-tools: {tools}
---

# {title}

TODO: 2-3 sentence overview.

## Available Capabilities

| Capability | Description | Script |
|-----------|-------------|--------|
| Feature A | TODO | `scripts/feature_a.py` |
| Feature B | TODO | `scripts/feature_b.py` |
| Feature C | TODO | `scripts/feature_c.py` |

## Feature A

### Usage

```bash
python scripts/feature_a.py [args]
```

### Options

- `--option1`: Description
- `--option2`: Description

## Feature B

### Usage

```bash
python scripts/feature_b.py [args]
```

## Combining Features

### Common Workflows

1. **A then B:** `feature_a.py input | feature_b.py`
2. **Full pipeline:** A → B → C

---

For details: [references/capability-details.md](references/capability-details.md)
'''


def create_skill_md(skill_name: str, skill_type: str, structure: str = None) -> str:
    """Generate SKILL.md content based on skill type and optional structure."""
    config = SKILL_TYPES[skill_type]

    # If structure is specified, use structure-based template
    if structure:
        return create_structure_template(skill_name, structure, config["tools"])

    # Otherwise, use type-based template (legacy behavior)
    if skill_type == "knowledge":
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what this skill does and when to use it.
  Include trigger phrases: "phrase1", "phrase2", "phrase3"
allowed-tools: {config["tools"]}
---

# {skill_name.replace("-", " ").title()}

TODO: 2-3 sentence overview of this skill.

## When to Use

- Scenario 1
- Scenario 2
- Scenario 3

## Core Guidelines

### Guideline 1

TODO: Explain the first guideline.

### Guideline 2

TODO: Explain the second guideline.

## Key Principles

- Principle 1
- Principle 2
- Principle 3

## Examples

### Example 1: Common Use Case

TODO: Add a practical example.

---

For detailed patterns: [references/patterns.md](references/patterns.md)
'''

    elif skill_type == "hybrid":
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what this skill does and when to use it.
  Supports: [capability1], [capability2].
  Include trigger phrases: "phrase1", "phrase2", "phrase3"
allowed-tools: {config["tools"]}
---

# {skill_name.replace("-", " ").title()}

TODO: 2-3 sentence overview of this skill.

## Quick Start

TODO: Fastest path to using this skill.

## Core Workflow

1. **Step 1**: Analyze the request
2. **Step 2**: Use appropriate script or generate code
3. **Step 3**: Validate results

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/example.py` | TODO: Purpose | `python scripts/example.py input output` |

## When to Use Scripts vs Generate Code

**Use scripts when**:
- Task is repetitive and well-defined
- Reliability is critical
- Same operation needed multiple times

**Generate code when**:
- Task requires customization
- One-time operation
- Context-specific logic needed

## Key Principles

- Principle 1
- Principle 2

---

For advanced patterns: [references/advanced.md](references/advanced.md)
'''

    elif skill_type == "tool":
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what this skill does and when to use it.
  Supports: [file operation 1], [file operation 2].
  Include trigger phrases: "phrase1", "phrase2", "phrase3"
allowed-tools: {config["tools"]}
---

# {skill_name.replace("-", " ").title()}

TODO: 2-3 sentence overview of this skill.

## Quick Start

```bash
# Example usage
python scripts/main_operation.py input_file output_file
```

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/operation1.py` | TODO: Purpose | `python scripts/operation1.py <input> <output>` |
| `scripts/operation2.py` | TODO: Purpose | `python scripts/operation2.py <input> [options]` |

## Script Details

### scripts/operation1.py

TODO: Detailed description of what this script does.

**Arguments**:
- `input`: Input file path
- `output`: Output file path

**Example**:
```bash
python scripts/operation1.py input.pdf output.pdf
```

### scripts/operation2.py

TODO: Detailed description.

## Troubleshooting

### Common Issue 1

**Symptom**: TODO
**Solution**: TODO

---

For troubleshooting: [references/troubleshooting.md](references/troubleshooting.md)
'''

    else:  # expert
        return f'''---
name: {skill_name}
description: |
  TODO: Describe what this skill does. This is an EXPERT skill requiring comprehensive documentation.
  Handles: [complex domain 1], [complex domain 2].
  Include trigger phrases: "phrase1", "phrase2", "phrase3"
allowed-tools: {config["tools"]}
---

# {skill_name.replace("-", " ").title()}

TODO: 2-3 sentence overview. Explain why this is an expert skill (complex format, undocumented behavior, etc.)

## Why This Skill Exists

Without this skill, Claude would need to:
- TODO: Describe trial-and-error that would be needed
- TODO: Describe undocumented behavior
- TODO: Describe library limitations

## Quick Start

```bash
# Most common operation
python scripts/main_operation.py input_file output_file

# Validate output
python scripts/validation/validate.py output_file
```

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/operation1.py` | TODO: Purpose | `python scripts/operation1.py <input> <output>` |
| `scripts/operation2.py` | TODO: Purpose | `python scripts/operation2.py <input> [options]` |
| `scripts/validation/validate.py` | Validate output | `python scripts/validation/validate.py <file>` |

## ⚠️ Critical: Known Limitations

### Limitation 1
- **Issue**: TODO: Describe the limitation
- **Workaround**: TODO: How our scripts handle it
- **Script**: `scripts/operation1.py --workaround`

### Limitation 2
- **Issue**: TODO
- **Workaround**: TODO

## Workflow

1. **Prepare**: TODO
2. **Execute**: Use appropriate script
3. **Validate**: `python scripts/validation/validate.py output_file`
4. **Troubleshoot**: See [references/troubleshooting.md](references/troubleshooting.md)

## When to Use Scripts vs Manual Code

**Always use scripts for**:
- TODO: Operations that are fragile
- TODO: Operations with known gotchas

**Can write manual code for**:
- TODO: Simple operations

---

**Essential References:**
- [Internal Structure](references/internal-structure.md) - Format internals
- [Troubleshooting](references/troubleshooting.md) - Known issues + fixes
- [Library Limitations](references/library-limitations.md) - What doesn't work
- [Edge Cases](references/edge-cases.md) - Special scenarios
'''


def create_example_script() -> str:
    """Generate example Python script."""
    return '''#!/usr/bin/env python3
"""
Example script - TODO: Replace with actual implementation.

Usage:
    python example.py <input> <output>
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="TODO: Description")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # TODO: Implement actual logic here
    print(f"Processing {input_path} -> {output_path}")

    # Example: Copy file (replace with actual logic)
    output_path.write_bytes(input_path.read_bytes())

    print(f"Done! Output written to {output_path}")


if __name__ == "__main__":
    main()
'''


def create_reference_md(skill_type: str) -> str:
    """Generate reference file content."""
    if skill_type == "knowledge":
        return '''# Detailed Patterns

This document contains detailed patterns and examples for the skill.

## Pattern 1: Common Scenario

### When to Use

TODO: Describe when this pattern applies.

### Implementation

TODO: Show how to implement this pattern.

### Example

TODO: Provide a concrete example.

## Pattern 2: Advanced Scenario

### When to Use

TODO: Describe when this pattern applies.

### Implementation

TODO: Show how to implement this pattern.

## Anti-patterns

### What NOT to Do

- Anti-pattern 1: TODO
- Anti-pattern 2: TODO
'''
    else:
        return '''# Advanced Usage

This document contains advanced usage patterns and troubleshooting.

## Advanced Options

### Option 1

TODO: Describe advanced option.

### Option 2

TODO: Describe advanced option.

## Troubleshooting

### Issue: Common Error

**Symptom**: TODO

**Cause**: TODO

**Solution**: TODO

### Issue: Another Error

**Symptom**: TODO

**Cause**: TODO

**Solution**: TODO

## Integration Examples

### With Other Tools

TODO: Show how to integrate with other tools.
'''


def create_expert_reference(ref_name: str) -> str:
    """Generate expert skill reference file content."""
    templates = {
        "internal-structure.md": '''# Internal Structure

This document explains the internal structure of the format this skill handles.

## File Format Overview

TODO: Describe the file format (e.g., "A .pptx is a ZIP containing XML files")

## Key Components

### Component 1

TODO: Describe the first key component.

```
# Structure example
component/
├── file1.xml
└── file2.xml
```

### Component 2

TODO: Describe the second key component.

## XML Namespaces (if applicable)

```python
NAMESPACES = {
    # TODO: Add relevant namespaces
}
```

## Common Patterns

### Pattern 1

TODO: Describe a common pattern in the internal structure.

### Pattern 2

TODO: Describe another pattern.

## Why This Matters

Understanding internals helps when:
- The library doesn't expose needed functionality
- Debugging corrupted files
- Implementing advanced features
''',
        "troubleshooting.md": '''# Troubleshooting Guide

This document contains known issues and their solutions.

## Common Issues

### Issue: [Error message or symptom]

**Symptom**: TODO: What the user sees

**Cause**: TODO: Why this happens

**Solution**:
```bash
# TODO: How to fix it
python scripts/fix_script.py --option
```

### Issue: [Another error]

**Symptom**: TODO

**Cause**: TODO

**Solution**: TODO

## Validation

Always validate output after operations:

```bash
python scripts/validation/validate.py output_file
```

## Recovery

### Recovering from Corruption

```bash
python scripts/validation/repair.py corrupted_file fixed_file
```

## Debug Mode

For detailed logging:

```bash
python scripts/operation.py input output --debug
```
''',
        "library-limitations.md": '''# Library Limitations

This document describes what the underlying library CAN'T do and our workarounds.

## Library Overview

**Library**: TODO: Name and version
**Documentation**: TODO: Link

## Limitations and Workarounds

### Limitation 1: [Feature not supported]

**What doesn't work**:
```python
# This fails or produces wrong results
library.feature()
```

**Our workaround**:
```python
# We do this instead (in scripts/workaround.py)
custom_implementation()
```

**Script**: `scripts/workaround.py`

### Limitation 2: [Another limitation]

**What doesn't work**: TODO

**Our workaround**: TODO

## Alternative Libraries Considered

| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| Library A | TODO | TODO | Used |
| Library B | TODO | TODO | Not used |

## When to Use Library vs Custom Code

**Use library for**:
- TODO: Simple operations

**Use custom code (our scripts) for**:
- TODO: Complex operations with known issues
''',
        "edge-cases.md": '''# Edge Cases

This document describes special scenarios and how to handle them.

## Edge Case 1: [Scenario]

**Scenario**: TODO: Describe the unusual situation

**Problem**: TODO: What goes wrong

**Solution**:
```bash
python scripts/operation.py input output --edge-case-flag
```

## Edge Case 2: [Another scenario]

**Scenario**: TODO

**Problem**: TODO

**Solution**: TODO

## Performance Considerations

### Large Files

For files > 100MB:
```bash
python scripts/operation.py large_file output --stream
```

### Many Items

For processing many items:
```bash
python scripts/batch.py input_dir/ output_dir/ --parallel 4
```

## Platform-Specific Issues

### Windows

TODO: Windows-specific issues and solutions

### macOS

TODO: macOS-specific issues and solutions

### Linux

TODO: Linux-specific issues and solutions
''',
    }
    return templates.get(ref_name, f"# {ref_name}\n\nTODO: Add content for {ref_name}\n")


def init_skill(skill_name: str, output_path: Path, skill_type: str, structure: str = None) -> None:
    """Initialize a skill directory with proper structure."""
    skill_dir = output_path / skill_name

    if skill_dir.exists():
        print(f"Error: Directory already exists: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    config = SKILL_TYPES[skill_type]

    # Create main directory
    skill_dir.mkdir(parents=True)
    print(f"Created: {skill_dir}/")

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(create_skill_md(skill_name, skill_type, structure))
    print(f"Created: {skill_md}")

    # Create subdirectories based on type
    for subdir in config["dirs"]:
        subdir_path = skill_dir / subdir
        subdir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {subdir_path}/")

        # Add example files
        if subdir == "scripts" and config["scripts"]:
            example_script = subdir_path / "example.py"
            example_script.write_text(create_example_script())
            example_script.chmod(0o755)
            print(f"Created: {example_script}")

        if subdir == "scripts/validation" and skill_type == "expert":
            validate_script = subdir_path / "validate.py"
            validate_script.write_text(create_example_script())
            validate_script.chmod(0o755)
            print(f"Created: {validate_script}")

        if subdir == "references":
            if skill_type == "expert" and "expert_refs" in config:
                # Create comprehensive reference files for expert skills
                for ref_name in config["expert_refs"]:
                    ref_file = subdir_path / ref_name
                    ref_file.write_text(create_expert_reference(ref_name))
                    print(f"Created: {ref_file}")
            else:
                ref_name = "patterns.md" if skill_type == "knowledge" else "advanced.md"
                ref_file = subdir_path / ref_name
                ref_file.write_text(create_reference_md(skill_type))
                print(f"Created: {ref_file}")

    # Create assets directory for hybrid/tool/expert skills (skip if already created by dirs)
    if config["assets"] and not (skill_dir / "assets").exists():
        assets_dir = skill_dir / "assets"
        assets_dir.mkdir()
        print(f"Created: {assets_dir}/")

        # Add .gitkeep
        gitkeep = assets_dir / ".gitkeep"
        gitkeep.write_text("# Add template files, images, or other assets here\n")
        print(f"Created: {gitkeep}")

    print(f"\n✅ Skill '{skill_name}' initialized successfully!")
    print(f"\nType: {skill_type} ({config['description']})")
    if structure:
        print(f"Structure: {structure} ({STRUCTURE_PATTERNS[structure]})")
    print(f"\nNext steps:")
    print(f"  1. Edit {skill_md} to define your skill")
    if config["scripts"]:
        print(f"  2. Implement scripts in {skill_dir}/scripts/")
    print(f"  3. Run: python validate_skill.py {skill_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Initialize a new skill directory with proper structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Skill Types (--type): Determines tools and directories
  knowledge  - For analysis, guidance, best practices (Read, Grep, Glob)
  hybrid     - Guidance + helper scripts (Read, Write, Grep, Glob, Bash)
  tool       - File manipulation, automation (Read, Write, Bash)
  expert     - Complex domain knowledge, comprehensive docs (OOXML, formats, etc.)

Structure Patterns (--structure): Determines SKILL.md organization
  workflow     - Sequential multi-step tasks with decision points
  task         - Single-purpose input->process->output transformation
  reference    - Rules, standards, and best practices documentation
  capabilities - Toolkit of related features/functions

Examples:
  %(prog)s my-skill
  %(prog)s my-skill --path .claude/skills
  %(prog)s pdf-processor --type tool --structure task
  %(prog)s deploy-checker --type hybrid --structure workflow
  %(prog)s code-style --type knowledge --structure reference
  %(prog)s webapp-testing --type tool --structure capabilities
        """
    )
    parser.add_argument("skill_name", help="Name of the skill (kebab-case)")
    parser.add_argument(
        "--path",
        default=".",
        help="Output directory (default: current directory)"
    )
    parser.add_argument(
        "--type",
        choices=["knowledge", "hybrid", "tool", "expert"],
        default="hybrid",
        help="Skill type (default: hybrid)"
    )
    parser.add_argument(
        "--structure",
        choices=["workflow", "task", "reference", "capabilities"],
        default=None,
        help="SKILL.md structure pattern (default: type-based template)"
    )

    args = parser.parse_args()

    # Validate skill name
    if not args.skill_name.replace("-", "").replace("_", "").isalnum():
        print(f"Error: Invalid skill name: {args.skill_name}", file=sys.stderr)
        print("Use kebab-case with alphanumeric characters only", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.path)
    if not output_path.exists():
        output_path.mkdir(parents=True)

    init_skill(args.skill_name, output_path, args.type, args.structure)


if __name__ == "__main__":
    main()
