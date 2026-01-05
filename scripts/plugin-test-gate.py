#!/usr/bin/env python3
"""
Plugin Test Gate - Enforces testing before deployment

This script is called by hooks to ensure plugins pass all tests
before they can be published or deployed.

Usage:
  python3 plugin-test-gate.py [--plugin-dir <path>] [--strict]

Exit codes:
  0 - All tests passed
  2 - Tests failed (blocks deployment)
"""

import sys
import os
import json
import subprocess
from pathlib import Path


def find_plugin_root() -> Path:
    """Find the plugin root directory"""
    # Try environment variable first
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])

    # Try current directory
    cwd = Path.cwd()

    # Look for plugin markers
    markers = [".claude-plugin/plugin.json", "commands", "skills", "hooks"]

    for marker in markers:
        if (cwd / marker).exists():
            return cwd

    # Walk up to find plugin root
    for parent in cwd.parents:
        for marker in markers:
            if (parent / marker).exists():
                return parent

    return cwd


def run_tests(plugin_dir: Path, strict: bool = False) -> tuple[bool, str]:
    """Run plugin tests and return (passed, message)"""

    # Check for test runner
    test_runner = Path(__file__).parent.parent / "skills" / "plugin-test-framework" / "templates" / "test-runner.py"

    if not test_runner.exists():
        # Fall back to basic validation
        return basic_validation(plugin_dir)

    try:
        result = subprocess.run(
            ["python3", str(test_runner), str(plugin_dir)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Check for failures in output
        if "FAIL" in result.stdout or result.returncode != 0:
            return False, f"Tests failed:\n{result.stdout}"

        return True, "All tests passed"

    except subprocess.TimeoutExpired:
        return False, "Test timeout"
    except Exception as e:
        return False, f"Test error: {e}"


def basic_validation(plugin_dir: Path) -> tuple[bool, str]:
    """Basic structure validation without test framework"""

    issues = []

    # Check plugin.json
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            data = json.loads(plugin_json.read_text())
            if "name" not in data:
                issues.append("plugin.json missing 'name'")
            if "description" not in data:
                issues.append("plugin.json missing 'description'")
        except json.JSONDecodeError:
            issues.append("plugin.json is invalid JSON")
    else:
        issues.append("No .claude-plugin/plugin.json found")

    # Check commands
    commands_dir = plugin_dir / "commands"
    if commands_dir.exists():
        for cmd in commands_dir.glob("*.md"):
            content = cmd.read_text()
            if not content.startswith("---"):
                issues.append(f"Command {cmd.name} missing frontmatter")
            elif "description:" not in content[:500]:
                issues.append(f"Command {cmd.name} missing description")

    # Check skills
    skills_dir = plugin_dir / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                if not (skill_dir / "SKILL.md").exists():
                    issues.append(f"Skill {skill_dir.name} missing SKILL.md")

    # Check hooks
    hooks_dir = plugin_dir / ".claude" / "hooks"
    if hooks_dir.exists():
        for hook in hooks_dir.glob("*.sh"):
            if not os.access(hook, os.X_OK):
                issues.append(f"Hook {hook.name} not executable")

    if issues:
        return False, "Validation issues:\n" + "\n".join(f"  - {i}" for i in issues)

    return True, "Basic validation passed"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Plugin Test Gate")
    parser.add_argument("--plugin-dir", type=str, help="Plugin directory")
    parser.add_argument("--strict", action="store_true", help="Strict mode (block on any issue)")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    args = parser.parse_args()

    # Read stdin for hook context
    stdin_data = {}
    try:
        if not sys.stdin.isatty():
            stdin_data = json.loads(sys.stdin.read())
    except:
        pass

    # Determine plugin directory
    if args.plugin_dir:
        plugin_dir = Path(args.plugin_dir)
    else:
        plugin_dir = find_plugin_root()

    # Check if this is a publish/deploy operation
    is_publish = False
    if stdin_data:
        tool_input = stdin_data.get("tool_input", {})
        command = tool_input.get("command", "")
        prompt = stdin_data.get("prompt", "")

        # Detect publish/deploy operations
        publish_patterns = ["publish", "deploy", "release", "npm publish", "gh release"]
        for pattern in publish_patterns:
            if pattern in command.lower() or pattern in prompt.lower():
                is_publish = True
                break

    # Run tests
    passed, message = run_tests(plugin_dir, args.strict)

    if not args.quiet:
        if passed:
            print(f"✅ Plugin validation passed: {plugin_dir.name}")
        else:
            print(f"❌ Plugin validation failed: {plugin_dir.name}")
            print(message)

    # Block if publish operation and tests failed
    if is_publish and not passed:
        output = {
            "hookSpecificOutput": {
                "permissionDecision": "deny"
            },
            "systemMessage": f"🚫 DEPLOYMENT BLOCKED: Plugin tests failed\n{message}"
        }
        print(json.dumps(output))
        sys.exit(2)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
