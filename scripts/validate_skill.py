#!/usr/bin/env python3
"""
Validate a skill directory structure and content.

Usage:
    python validate_skill.py <skill-directory>

Examples:
    python validate_skill.py .claude/skills/my-skill
    python validate_skill.py ./pdf-processor
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Validation result types
ERROR = "error"
WARNING = "warning"
INFO = "info"


def validate_skill(skill_dir: Path) -> List[Tuple[str, str, str]]:
    """
    Validate a skill directory.

    Returns list of (level, category, message) tuples.
    """
    results = []

    # Check skill directory exists
    if not skill_dir.exists():
        results.append((ERROR, "structure", f"Skill directory not found: {skill_dir}"))
        return results

    if not skill_dir.is_dir():
        results.append((ERROR, "structure", f"Not a directory: {skill_dir}"))
        return results

    # Check SKILL.md exists
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        results.append((ERROR, "structure", "SKILL.md not found (required)"))
        return results

    results.append((INFO, "structure", "SKILL.md found"))

    # Validate SKILL.md content
    content = skill_md.read_text()
    results.extend(validate_skill_md(content, skill_dir))

    # Check directory structure
    results.extend(validate_directories(skill_dir))

    # Check for unwanted files
    results.extend(check_unwanted_files(skill_dir))

    # Check scripts if present
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        results.extend(validate_scripts(scripts_dir))

    return results


def validate_skill_md(content: str, skill_dir: Path) -> List[Tuple[str, str, str]]:
    """Validate SKILL.md content."""
    results = []

    # Check for YAML frontmatter
    if not content.startswith("---"):
        results.append((ERROR, "frontmatter", "SKILL.md must start with YAML frontmatter (---)"))
        return results

    # Extract frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        results.append((ERROR, "frontmatter", "Invalid YAML frontmatter format"))
        return results

    frontmatter = parts[1].strip()
    body = parts[2].strip()

    # Check required fields
    if "name:" not in frontmatter:
        results.append((ERROR, "frontmatter", "Missing required field: name"))
    else:
        results.append((INFO, "frontmatter", "name field present"))

    if "description:" not in frontmatter:
        results.append((ERROR, "frontmatter", "Missing required field: description"))
    else:
        results.append((INFO, "frontmatter", "description field present"))

    # Check description quality
    desc_match = re.search(r'description:\s*[|>]?\s*\n?\s*(.+?)(?=\n[a-z]|\nallowed|\n---|\Z)',
                          frontmatter, re.DOTALL | re.IGNORECASE)
    if desc_match:
        description = desc_match.group(1).strip()
        if len(description) < 50:
            results.append((WARNING, "frontmatter",
                          f"Description is short ({len(description)} chars). Include trigger phrases and use cases."))
        if "TODO" in description:
            results.append((WARNING, "frontmatter", "Description contains TODO - please complete"))

    # Check allowed-tools
    if "allowed-tools:" not in frontmatter:
        results.append((WARNING, "frontmatter", "No allowed-tools specified (recommended)"))
    else:
        results.append((INFO, "frontmatter", "allowed-tools specified"))

    # Check body length
    line_count = len(body.split("\n"))
    if line_count > 500:
        results.append((WARNING, "content",
                       f"SKILL.md body is {line_count} lines. Consider moving content to references/"))
    else:
        results.append((INFO, "content", f"SKILL.md body is {line_count} lines (good)"))

    # Check for TODOs in body
    todo_count = body.count("TODO")
    if todo_count > 0:
        results.append((WARNING, "content", f"Body contains {todo_count} TODO items - please complete"))

    # Check if references are linked properly
    ref_links = re.findall(r'\[.*?\]\((references/[^)]+)\)', body)
    for ref_link in ref_links:
        ref_path = skill_dir / ref_link
        if not ref_path.exists():
            results.append((ERROR, "references", f"Broken reference link: {ref_link}"))
        else:
            results.append((INFO, "references", f"Reference link valid: {ref_link}"))

    # Check script references
    script_refs = re.findall(r'scripts/[\w.-]+\.py', body)
    for script_ref in script_refs:
        script_path = skill_dir / script_ref
        if not script_path.exists():
            results.append((ERROR, "scripts", f"Referenced script not found: {script_ref}"))

    return results


def validate_directories(skill_dir: Path) -> List[Tuple[str, str, str]]:
    """Validate directory structure."""
    results = []

    valid_dirs = {"scripts", "references", "assets"}

    for item in skill_dir.iterdir():
        if item.is_dir() and item.name not in valid_dirs and not item.name.startswith("."):
            results.append((WARNING, "structure",
                          f"Unexpected directory: {item.name}/ (expected: scripts/, references/, assets/)"))

    # Check if scripts/ exists and has content
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        scripts = list(scripts_dir.glob("*.py")) + list(scripts_dir.glob("*.sh"))
        if scripts:
            results.append((INFO, "structure", f"scripts/ contains {len(scripts)} script(s)"))
        else:
            results.append((WARNING, "structure", "scripts/ exists but contains no .py or .sh files"))

    # Check references/
    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        refs = list(refs_dir.glob("*.md"))
        if refs:
            results.append((INFO, "structure", f"references/ contains {len(refs)} file(s)"))
        else:
            results.append((WARNING, "structure", "references/ exists but contains no .md files"))

    # Check assets/
    assets_dir = skill_dir / "assets"
    if assets_dir.exists():
        assets = [f for f in assets_dir.iterdir() if not f.name.startswith(".")]
        if assets:
            results.append((INFO, "structure", f"assets/ contains {len(assets)} item(s)"))

    return results


def check_unwanted_files(skill_dir: Path) -> List[Tuple[str, str, str]]:
    """Check for files that shouldn't be in a skill."""
    results = []

    unwanted = [
        "README.md",
        "INSTALLATION_GUIDE.md",
        "QUICK_REFERENCE.md",
        "CHANGELOG.md",
        "LICENSE.md",
        "CONTRIBUTING.md",
    ]

    for filename in unwanted:
        if (skill_dir / filename).exists():
            results.append((WARNING, "content",
                          f"Unwanted file: {filename} (skills shouldn't have user documentation)"))

    return results


def validate_scripts(scripts_dir: Path) -> List[Tuple[str, str, str]]:
    """Validate script files."""
    results = []

    for script in scripts_dir.glob("*.py"):
        content = script.read_text()

        # Check for shebang
        if not content.startswith("#!/"):
            results.append((WARNING, "scripts", f"{script.name}: Missing shebang line"))

        # Check for docstring
        if '"""' not in content[:500] and "'''" not in content[:500]:
            results.append((WARNING, "scripts", f"{script.name}: Missing docstring"))

        # Check for TODO
        if "TODO" in content:
            results.append((WARNING, "scripts", f"{script.name}: Contains TODO items"))

        # Check if executable
        if not script.stat().st_mode & 0o111:
            results.append((INFO, "scripts", f"{script.name}: Not executable (run: chmod +x {script})"))

    for script in scripts_dir.glob("*.sh"):
        content = script.read_text()

        # Check for shebang
        if not content.startswith("#!/"):
            results.append((WARNING, "scripts", f"{script.name}: Missing shebang line"))

    return results


def print_results(results: List[Tuple[str, str, str]]) -> int:
    """Print validation results and return exit code."""
    errors = [r for r in results if r[0] == ERROR]
    warnings = [r for r in results if r[0] == WARNING]
    infos = [r for r in results if r[0] == INFO]

    # Group by category
    categories = {}
    for level, category, message in results:
        if category not in categories:
            categories[category] = []
        categories[category].append((level, message))

    print("\n" + "=" * 60)
    print("SKILL VALIDATION REPORT")
    print("=" * 60)

    for category, items in sorted(categories.items()):
        print(f"\n## {category.upper()}")
        for level, message in items:
            if level == ERROR:
                print(f"  ❌ {message}")
            elif level == WARNING:
                print(f"  ⚠️  {message}")
            else:
                print(f"  ✅ {message}")

    print("\n" + "-" * 60)
    print(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} passed")
    print("-" * 60)

    if errors:
        print("\n❌ VALIDATION FAILED")
        print("Fix the errors above before using this skill.")
        return 1
    elif warnings:
        print("\n⚠️  VALIDATION PASSED WITH WARNINGS")
        print("Consider addressing the warnings above.")
        return 0
    else:
        print("\n✅ VALIDATION PASSED")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate a skill directory structure and content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s .claude/skills/my-skill
  %(prog)s ./pdf-processor

Checks performed:
  - SKILL.md exists with valid YAML frontmatter
  - Required fields (name, description) present
  - Description quality and completeness
  - Reference links valid
  - Script files have proper format
  - No unwanted documentation files
        """
    )
    parser.add_argument("skill_dir", help="Path to skill directory")

    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    results = validate_skill(skill_dir)
    exit_code = print_results(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
