#!/usr/bin/env python3
"""
Context-aware functional testing for skillmaker plugins.

Detects what changed and runs appropriate tests:
- New plugin: Test all skills/agents/commands
- Modified: Test only changed components
- Debugging: Test specific components

Usage:
    python3 scripts/functional-test.py              # Auto-detect from git
    python3 scripts/functional-test.py --all        # Test everything
    python3 scripts/functional-test.py --component skills/my-skill
    python3 scripts/functional-test.py --json       # JSON output

Exit codes:
    0 - All tests passed
    1 - Tests failed
    2 - Warnings only
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional


class TestResult:
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.warnings: List[str] = []
        self.skipped: List[str] = []

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "skipped": self.skipped,
            "summary": {
                "total": len(self.passed) + len(self.failed) + len(self.skipped),
                "passed": len(self.passed),
                "failed": len(self.failed),
                "warnings": len(self.warnings),
                "skipped": len(self.skipped)
            }
        }


def get_project_root() -> Path:
    """Find project root (directory containing .claude-plugin/)."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude-plugin").exists():
            return current
        current = current.parent
    return Path.cwd()


def detect_changes(project_root: Path) -> Dict[str, Set[str]]:
    """Detect changed files using git, categorized by component type."""
    changes = {
        "skills": set(),
        "agents": set(),
        "commands": set(),
        "scripts": set(),
        "hooks": set(),
        "config": set()
    }

    try:
        # Get untracked files (new)
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=project_root, capture_output=True, text=True
        )

        # Get modified files
        modified = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=project_root, capture_output=True, text=True
        )

        # Get staged files
        staged = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            cwd=project_root, capture_output=True, text=True
        )

        all_files = set()
        for result in [untracked, modified, staged]:
            if result.returncode == 0:
                all_files.update(result.stdout.strip().split('\n'))

        # Categorize files
        for f in all_files:
            if not f:
                continue
            if f.startswith("skills/"):
                # Extract skill name (skills/skill-name/*)
                parts = f.split("/")
                if len(parts) >= 2:
                    changes["skills"].add(parts[1])
            elif f.startswith("agents/"):
                changes["agents"].add(f)
            elif f.startswith("commands/"):
                changes["commands"].add(f)
            elif f.startswith("scripts/"):
                changes["scripts"].add(f)
            elif f.startswith("hooks/"):
                changes["hooks"].add(f)
            elif f.endswith(".json"):
                changes["config"].add(f)

    except FileNotFoundError:
        # Git not available
        pass

    return changes


def get_all_components(project_root: Path) -> Dict[str, Set[str]]:
    """Get all testable components in the project."""
    components = {
        "skills": set(),
        "agents": set(),
        "commands": set()
    }

    # Skills
    skills_dir = project_root / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                components["skills"].add(skill_dir.name)

    # Agents
    agents_dir = project_root / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            components["agents"].add(str(agent_file.relative_to(project_root)))

    # Commands
    commands_dir = project_root / "commands"
    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.md"):
            components["commands"].add(str(cmd_file.relative_to(project_root)))

    return components


def load_marketplace_config(project_root: Path) -> Optional[dict]:
    """Load marketplace.json configuration."""
    marketplace_path = project_root / ".claude-plugin" / "marketplace.json"
    if marketplace_path.exists():
        with open(marketplace_path) as f:
            return json.load(f)
    return None


def parse_agent_frontmatter(agent_path: Path) -> dict:
    """Parse agent frontmatter to extract dependencies."""
    content = agent_path.read_text()
    frontmatter = {}

    if content.startswith("---"):
        try:
            end_idx = content.index("---", 3)
            yaml_str = content[3:end_idx].strip()
            for line in yaml_str.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()
        except (ValueError, IndexError):
            pass

    return frontmatter


def test_skill_registration(project_root: Path, skill_name: str, config: dict) -> Tuple[bool, str]:
    """Test if a skill is properly registered in marketplace.json."""
    if not config or "plugins" not in config:
        return False, f"No marketplace config found"

    for plugin in config.get("plugins", []):
        skills = plugin.get("skills", [])
        skill_paths = [s.replace("./skills/", "").rstrip("/") for s in skills]
        if skill_name in skill_paths:
            return True, f"Skill '{skill_name}' is registered"

    return False, f"Skill '{skill_name}' NOT registered in marketplace.json"


def test_agent_dependencies(project_root: Path, agent_path: str, config: dict) -> Tuple[bool, str]:
    """Test if agent's skill dependencies are all registered."""
    full_path = project_root / agent_path
    if not full_path.exists():
        return False, f"Agent file not found: {agent_path}"

    frontmatter = parse_agent_frontmatter(full_path)
    skills_str = frontmatter.get("skills", "")

    if not skills_str:
        return True, f"Agent '{agent_path}' has no skill dependencies"

    # Parse skills (comma-separated)
    declared_skills = [s.strip() for s in skills_str.split(",")]

    # Get registered skills from config
    registered_skills = set()
    if config and "plugins" in config:
        for plugin in config.get("plugins", []):
            for skill_path in plugin.get("skills", []):
                # Extract skill name from path
                skill_name = skill_path.replace("./skills/", "").rstrip("/")
                registered_skills.add(skill_name)

    # Check each dependency
    missing = []
    for skill in declared_skills:
        if skill not in registered_skills:
            missing.append(skill)

    if missing:
        return False, f"Agent '{agent_path}' depends on unregistered skills: {missing}"

    return True, f"Agent '{agent_path}' dependencies OK ({len(declared_skills)} skills)"


def test_skill_structure(project_root: Path, skill_name: str) -> Tuple[bool, str]:
    """Test skill directory structure."""
    skill_dir = project_root / "skills" / skill_name
    skill_md = skill_dir / "SKILL.md"

    if not skill_dir.exists():
        return False, f"Skill directory not found: {skill_name}"

    if not skill_md.exists():
        return False, f"SKILL.md not found in {skill_name}"

    # Check frontmatter
    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, f"Skill '{skill_name}' missing frontmatter"

    return True, f"Skill '{skill_name}' structure OK"


def run_tests(project_root: Path, components: Dict[str, Set[str]],
              test_all: bool = False) -> TestResult:
    """Run tests on specified components."""
    result = TestResult()
    config = load_marketplace_config(project_root)

    # Determine what to test
    if test_all:
        to_test = get_all_components(project_root)
    else:
        to_test = components

    # Test skills
    for skill_name in to_test.get("skills", set()):
        # Structure test
        ok, msg = test_skill_structure(project_root, skill_name)
        if ok:
            result.passed.append(f"[STRUCTURE] {msg}")
        else:
            result.failed.append(f"[STRUCTURE] {msg}")
            continue

        # Registration test
        ok, msg = test_skill_registration(project_root, skill_name, config)
        if ok:
            result.passed.append(f"[REGISTRATION] {msg}")
        else:
            result.failed.append(f"[REGISTRATION] {msg}")

    # Test agents
    for agent_path in to_test.get("agents", set()):
        ok, msg = test_agent_dependencies(project_root, agent_path, config)
        if ok:
            result.passed.append(f"[DEPENDENCY] {msg}")
        else:
            result.failed.append(f"[DEPENDENCY] {msg}")

    # Note about runtime tests
    if to_test.get("skills") or to_test.get("agents"):
        result.warnings.append(
            "[INFO] Static tests completed. Runtime tests (Skill() load, Task execution) "
            "require Claude Code session."
        )

    return result


def print_report(result: TestResult, json_output: bool = False):
    """Print test report."""
    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print("=" * 60)
    print("FUNCTIONAL TEST REPORT")
    print("=" * 60)

    if result.failed:
        print("\nFAILED:")
        for msg in result.failed:
            print(f"  ❌ {msg}")

    if result.warnings:
        print("\nWARNINGS:")
        for msg in result.warnings:
            print(f"  ⚠️  {msg}")

    if result.passed:
        print("\nPASSED:")
        for msg in result.passed:
            print(f"  ✅ {msg}")

    if result.skipped:
        print("\nSKIPPED:")
        for msg in result.skipped:
            print(f"  ⏭️  {msg}")

    summary = result.to_dict()["summary"]
    print(f"\nSUMMARY:")
    print(f"  Total:    {summary['total']}")
    print(f"  Passed:   {summary['passed']}")
    print(f"  Failed:   {summary['failed']}")
    print(f"  Warnings: {summary['warnings']}")

    if result.failed:
        print("\nSTATUS: ❌ TESTS FAILED")
    elif result.warnings:
        print("\nSTATUS: ⚠️  PASSED WITH WARNINGS")
    else:
        print("\nSTATUS: ✅ ALL TESTS PASSED")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Context-aware functional testing")
    parser.add_argument("--all", action="store_true", help="Test all components")
    parser.add_argument("--component", help="Test specific component path")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    project_root = get_project_root()

    if args.component:
        # Test specific component
        components = {"skills": set(), "agents": set(), "commands": set()}
        if args.component.startswith("skills/"):
            skill_name = args.component.replace("skills/", "").rstrip("/")
            components["skills"].add(skill_name)
        elif args.component.startswith("agents/"):
            components["agents"].add(args.component)
        result = run_tests(project_root, components)
    elif args.all:
        # Test everything
        result = run_tests(project_root, {}, test_all=True)
    else:
        # Auto-detect from git
        changes = detect_changes(project_root)
        has_changes = any(changes.values())

        if not has_changes:
            if not args.json:
                print("No changes detected. Use --all to test all components.")
            result = TestResult()
            result.skipped.append("No changes detected")
        else:
            result = run_tests(project_root, changes)

    print_report(result, args.json)

    if result.failed:
        sys.exit(1)
    elif result.warnings:
        sys.exit(0)  # Warnings don't block
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
