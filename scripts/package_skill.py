#!/usr/bin/env python3
"""
Package a skill directory into a distributable ZIP file.

Usage:
    python package_skill.py <skill-path> [--output <output-dir>]

Examples:
    python package_skill.py skills/pdf-processor
    python package_skill.py skills/pdf-processor --output dist/

Output:
    {skill-name}-v{version}.zip
"""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Optional

# Files/directories to exclude from package
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    ".git",
    ".gitignore",
    "test_*",
    "*_test.py",
    ".pytest_cache",
    "*.egg-info",
    ".mypy_cache",
    ".ruff_cache",
]


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}

    try:
        import yaml
        end_idx = content.index("---", 3)
        yaml_content = content[3:end_idx].strip()
        return yaml.safe_load(yaml_content) or {}
    except (ValueError, ImportError):
        # Fallback: simple regex extraction
        version_match = re.search(r"version:\s*['\"]?([^'\"\n]+)", content)
        name_match = re.search(r"name:\s*['\"]?([^'\"\n]+)", content)
        return {
            "version": version_match.group(1).strip() if version_match else "1.0.0",
            "name": name_match.group(1).strip() if name_match else None,
        }


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from package."""
    name = path.name

    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*") and pattern.endswith("*"):
            if pattern[1:-1] in name:
                return True
        elif pattern.startswith("*"):
            if name.endswith(pattern[1:]):
                return True
        elif pattern.endswith("*"):
            if name.startswith(pattern[:-1]):
                return True
        elif name == pattern:
            return True

    return False


def validate_skill(skill_path: Path) -> tuple[bool, list[str]]:
    """Validate skill structure before packaging."""
    errors = []

    # Check SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        errors.append("Missing SKILL.md")
        return False, errors

    # Check frontmatter has required fields
    content = skill_md.read_text()
    fm = parse_frontmatter(content)

    if not fm.get("name"):
        errors.append("SKILL.md missing 'name' in frontmatter")

    if not fm.get("description"):
        errors.append("SKILL.md missing 'description' in frontmatter")

    if "TODO" in content[:500]:  # Check first 500 chars (frontmatter area)
        errors.append("SKILL.md contains TODO in frontmatter")

    return len(errors) == 0, errors


def package_skill(skill_path: Path, output_dir: Optional[Path] = None) -> Path:
    """Package skill directory into ZIP file."""
    # Validate
    valid, errors = validate_skill(skill_path)
    if not valid:
        print("Validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # Get metadata
    skill_md = skill_path / "SKILL.md"
    fm = parse_frontmatter(skill_md.read_text())

    skill_name = fm.get("name") or skill_path.name
    version = fm.get("version", "1.0.0")

    # Sanitize name for filename
    safe_name = re.sub(r"[^\w\-]", "-", skill_name.lower())

    # Determine output path
    if output_dir is None:
        output_dir = Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_filename = f"{safe_name}-v{version}.zip"
    zip_path = output_dir / zip_filename

    # Create ZIP
    files_added = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_path.rglob("*"):
            if file_path.is_dir():
                continue

            # Check exclusions
            if should_exclude(file_path):
                continue

            # Check parent directories for exclusions
            skip = False
            for parent in file_path.relative_to(skill_path).parents:
                if should_exclude(Path(parent.name)):
                    skip = True
                    break
            if skip:
                continue

            # Add to ZIP
            arcname = file_path.relative_to(skill_path)
            zf.write(file_path, arcname)
            files_added += 1

    return zip_path, files_added


def main():
    parser = argparse.ArgumentParser(
        description="Package a skill directory into a distributable ZIP file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s skills/pdf-processor
    %(prog)s skills/pdf-processor --output dist/

Output format: {skill-name}-v{version}.zip

Excluded files/directories:
    __pycache__, *.pyc, .DS_Store, .git, test_*, *_test.py
        """
    )
    parser.add_argument("skill_path", help="Path to skill directory")
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: current directory)"
    )

    args = parser.parse_args()

    skill_path = Path(args.skill_path).resolve()
    if not skill_path.exists():
        print(f"Error: Skill directory not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    if not skill_path.is_dir():
        print(f"Error: Not a directory: {skill_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output).resolve() if args.output else None

    zip_path, files_added = package_skill(skill_path, output_dir)

    print(f"Packaged: {zip_path}")
    print(f"Files: {files_added}")
    print(f"Size: {zip_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
