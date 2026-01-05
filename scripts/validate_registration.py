#!/usr/bin/env python3
"""
Validate plugin registration integrity.

Checks that marketplace.json entries match actual files and vice versa.
This is the most common cause of deployment failures.

Usage:
    python scripts/validate_registration.py [plugin-path]

Examples:
    python scripts/validate_registration.py
    python scripts/validate_registration.py /path/to/plugin

Exit codes:
    0 - All validations passed
    1 - Errors found (deployment will fail)
    2 - Warnings only (deployment may work but has issues)
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set


def find_marketplace_json(start_path: Path) -> Path | None:
    """Find marketplace.json in .claude-plugin/ directory."""
    claude_plugin = start_path / ".claude-plugin"
    if claude_plugin.exists():
        marketplace = claude_plugin / "marketplace.json"
        if marketplace.exists():
            return marketplace

    # Also check for standalone plugin.json
    plugin_json = start_path / "plugin.json"
    if plugin_json.exists():
        return plugin_json

    return None


def normalize_path(path: str, file_type: str) -> str:
    """Normalize a path by removing ./ prefix and handling extensions."""
    path = path.strip().strip('"').strip("'").strip(",")
    if path.startswith("./"):
        path = path[2:]
    return path


def path_to_file(path: str, extension: str = ".md") -> str:
    """Convert a registration path to actual file path."""
    if path.endswith(extension):
        return path
    return path + extension


def validate_commands(plugin_root: Path, registered: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Validate commands registration.
    Returns: (errors, warnings, passed)
    """
    errors = []
    warnings = []
    passed = []

    commands_dir = plugin_root / "commands"
    if not commands_dir.exists():
        if registered:
            errors.append(f"commands/ directory not found but {len(registered)} commands registered")
        return errors, warnings, passed

    # Get actual files
    actual_files = set()
    for f in commands_dir.glob("*.md"):
        actual_files.add(f.name)

    # Normalize registered paths
    registered_normalized = {}
    has_extension = set()
    no_extension = set()

    for reg_path in registered:
        norm = normalize_path(reg_path, "commands")
        # Extract just the filename part
        parts = norm.split("/")
        if len(parts) >= 2 and parts[0] == "commands":
            filename = parts[1]
            if filename.endswith(".md"):
                has_extension.add(filename)
                registered_normalized[filename] = reg_path
            else:
                no_extension.add(filename)
                registered_normalized[filename + ".md"] = reg_path

    # Check format consistency
    if has_extension and no_extension:
        warnings.append(f"Inconsistent format: some commands have .md ({list(has_extension)[:2]}), some don't ({list(no_extension)[:2]})")

    # Check registered -> file exists
    for filename, orig_path in registered_normalized.items():
        if filename in actual_files:
            passed.append(f"{orig_path} -> commands/{filename} EXISTS")
        else:
            errors.append(f"{orig_path} -> commands/{filename} NOT FOUND")

    # Check file exists -> registered
    for actual in actual_files:
        if actual not in registered_normalized:
            base_name = actual[:-3]  # remove .md
            # Check if registered without extension
            if base_name + ".md" not in registered_normalized and actual not in registered_normalized:
                errors.append(f"commands/{actual} exists but NOT REGISTERED in marketplace.json")

    return errors, warnings, passed


def validate_agents(plugin_root: Path, registered: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Validate agents registration."""
    errors = []
    warnings = []
    passed = []

    agents_dir = plugin_root / "agents"
    if not agents_dir.exists():
        if registered:
            errors.append(f"agents/ directory not found but {len(registered)} agents registered")
        return errors, warnings, passed

    actual_files = set(f.name for f in agents_dir.glob("*.md"))

    registered_normalized = {}
    for reg_path in registered:
        norm = normalize_path(reg_path, "agents")
        parts = norm.split("/")
        if len(parts) >= 2 and parts[0] == "agents":
            filename = parts[1]
            if not filename.endswith(".md"):
                filename += ".md"
            registered_normalized[filename] = reg_path

    for filename, orig_path in registered_normalized.items():
        if filename in actual_files:
            passed.append(f"{orig_path} -> agents/{filename} EXISTS")
        else:
            errors.append(f"{orig_path} -> agents/{filename} NOT FOUND")

    for actual in actual_files:
        if actual not in registered_normalized:
            errors.append(f"agents/{actual} exists but NOT REGISTERED")

    return errors, warnings, passed


def validate_skills(plugin_root: Path, registered: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Validate skills registration."""
    errors = []
    warnings = []
    passed = []

    skills_dir = plugin_root / "skills"
    if not skills_dir.exists():
        if registered:
            errors.append(f"skills/ directory not found but {len(registered)} skills registered")
        return errors, warnings, passed

    actual_dirs = set(d.name for d in skills_dir.iterdir() if d.is_dir())

    registered_normalized = {}
    for reg_path in registered:
        norm = normalize_path(reg_path, "skills")
        parts = norm.split("/")
        if len(parts) >= 2 and parts[0] == "skills":
            dirname = parts[1]
            registered_normalized[dirname] = reg_path

    for dirname, orig_path in registered_normalized.items():
        skill_dir = skills_dir / dirname
        skill_md = skill_dir / "SKILL.md"

        if not skill_dir.exists():
            errors.append(f"{orig_path} -> skills/{dirname}/ NOT FOUND")
        elif not skill_md.exists():
            errors.append(f"{orig_path} -> skills/{dirname}/SKILL.md NOT FOUND (directory exists but no SKILL.md)")
        else:
            passed.append(f"{orig_path} -> skills/{dirname}/SKILL.md EXISTS")

    for actual in actual_dirs:
        if actual not in registered_normalized:
            skill_md = skills_dir / actual / "SKILL.md"
            if skill_md.exists():
                errors.append(f"skills/{actual}/ exists with SKILL.md but NOT REGISTERED")

    return errors, warnings, passed


def validate_source_path(plugin_data: dict) -> Tuple[List[str], List[str]]:
    """Validate source path format."""
    errors = []
    warnings = []

    source = plugin_data.get("source", "")

    if isinstance(source, str):
        if source and not source.startswith("./") and source != ".":
            if source.startswith("/"):
                errors.append(f'source "{source}" is absolute path - should be relative starting with "./"')
            else:
                errors.append(f'source "{source}" must start with "./" (e.g., "./{source}")')
    elif isinstance(source, dict):
        # GitHub format
        if "source" not in source or "repo" not in source:
            errors.append(f'GitHub source format requires {{"source": "github", "repo": "user/repo"}}')

    return errors, warnings


def validate_settings_json(home_dir: Path = None) -> Tuple[List[str], List[str]]:
    """Check for common settings.json misconfigurations."""
    errors = []
    warnings = []

    if home_dir is None:
        home_dir = Path.home()

    settings_paths = [
        home_dir / ".claude" / "settings.json",
        home_dir / ".config" / "claude-code" / "settings.json",
    ]

    for settings_path in settings_paths:
        if not settings_path.exists():
            continue

        try:
            with open(settings_path) as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        # Check plugins array
        plugins = settings.get("plugins", [])
        for i, plugin in enumerate(plugins):
            if isinstance(plugin, dict):
                source = plugin.get("source", "")
                if isinstance(source, str):
                    if source and not source.startswith("./") and not source.startswith("/"):
                        errors.append(
                            f'settings.json plugins[{i}].source "{source}" must start with "./" '
                            f'(e.g., "./{source}")'
                        )

        # Check extraKnownMarketplaces
        marketplaces = settings.get("extraKnownMarketplaces", {})
        for name, config in marketplaces.items():
            source = config.get("source", "")
            if isinstance(source, str):
                if source and not source.startswith("./"):
                    errors.append(
                        f'settings.json extraKnownMarketplaces.{name}.source "{source}" '
                        f'must start with "./" or use GitHub format'
                    )
            elif isinstance(source, dict):
                # GitHub format - validate structure
                if "source" not in source or "repo" not in source:
                    errors.append(
                        f'settings.json extraKnownMarketplaces.{name}.source missing "source" or "repo" field'
                    )

    return errors, warnings


def main():
    # Determine plugin path
    if len(sys.argv) > 1:
        plugin_root = Path(sys.argv[1]).resolve()
    else:
        plugin_root = Path.cwd()

    print("=" * 60)
    print("PLUGIN REGISTRATION VALIDATOR")
    print("=" * 60)
    print(f"Plugin path: {plugin_root}")
    print()

    # Also check settings.json for common errors
    settings_errors, settings_warnings = validate_settings_json()
    if settings_errors:
        print("SETTINGS.JSON ISSUES DETECTED:")
        for e in settings_errors:
            print(f"  ❌ {e}")
        print()

    # Find marketplace.json
    marketplace_path = find_marketplace_json(plugin_root)
    if not marketplace_path:
        print("ERROR: No .claude-plugin/marketplace.json or plugin.json found")
        sys.exit(1)

    print(f"Config file: {marketplace_path}")
    print()

    # Parse JSON
    try:
        with open(marketplace_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {marketplace_path}: {e}")
        sys.exit(1)

    # Handle marketplace format (plugins array) vs plugin format
    if "plugins" in data:
        plugins = data["plugins"]
    else:
        plugins = [data]

    total_errors = list(settings_errors)  # Include settings.json errors
    total_warnings = list(settings_warnings)
    total_passed = []

    for plugin in plugins:
        plugin_name = plugin.get("name", "unnamed")
        print(f"--- Validating plugin: {plugin_name} ---")
        print()

        # Determine plugin source path
        source = plugin.get("source", "./")
        if source == "." or source == "./":
            effective_root = plugin_root
        else:
            source_path = source.lstrip("./")
            effective_root = plugin_root / source_path

        # Validate source path format
        src_errors, src_warnings = validate_source_path(plugin)
        total_errors.extend(src_errors)
        total_warnings.extend(src_warnings)

        # Get registered items
        registered_commands = plugin.get("commands", [])
        registered_agents = plugin.get("agents", [])
        registered_skills = plugin.get("skills", [])

        # Validate commands
        if registered_commands or (effective_root / "commands").exists():
            print("COMMANDS:")
            errors, warnings, passed = validate_commands(effective_root, registered_commands)
            for e in errors:
                print(f"  ❌ {e}")
            for w in warnings:
                print(f"  ⚠️  {w}")
            for p in passed:
                print(f"  ✅ {p}")
            if not errors and not warnings and not passed:
                print("  (none)")
            print()
            total_errors.extend(errors)
            total_warnings.extend(warnings)
            total_passed.extend(passed)

        # Validate agents
        if registered_agents or (effective_root / "agents").exists():
            print("AGENTS:")
            errors, warnings, passed = validate_agents(effective_root, registered_agents)
            for e in errors:
                print(f"  ❌ {e}")
            for w in warnings:
                print(f"  ⚠️  {w}")
            for p in passed:
                print(f"  ✅ {p}")
            if not errors and not warnings and not passed:
                print("  (none)")
            print()
            total_errors.extend(errors)
            total_warnings.extend(warnings)
            total_passed.extend(passed)

        # Validate skills
        if registered_skills or (effective_root / "skills").exists():
            print("SKILLS:")
            errors, warnings, passed = validate_skills(effective_root, registered_skills)
            for e in errors:
                print(f"  ❌ {e}")
            for w in warnings:
                print(f"  ⚠️  {w}")
            for p in passed:
                print(f"  ✅ {p}")
            if not errors and not warnings and not passed:
                print("  (none)")
            print()
            total_errors.extend(errors)
            total_warnings.extend(warnings)
            total_passed.extend(passed)

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Errors:   {len(total_errors)} ❌")
    print(f"  Warnings: {len(total_warnings)} ⚠️")
    print(f"  Passed:   {len(total_passed)} ✅")
    print()

    if total_errors:
        print("STATUS: ❌ DEPLOYMENT WILL FAIL")
        print()
        print("Fix these errors:")
        for i, e in enumerate(total_errors, 1):
            print(f"  {i}. {e}")
        sys.exit(1)
    elif total_warnings:
        print("STATUS: ⚠️  DEPLOYMENT MAY HAVE ISSUES")
        print()
        print("Consider fixing these warnings:")
        for i, w in enumerate(total_warnings, 1):
            print(f"  {i}. {w}")
        sys.exit(2)
    else:
        print("STATUS: ✅ READY FOR DEPLOYMENT")
        sys.exit(0)


if __name__ == "__main__":
    main()
