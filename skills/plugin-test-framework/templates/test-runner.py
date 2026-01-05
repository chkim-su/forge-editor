#!/usr/bin/env python3
"""
Plugin Test Runner - Dynamic Hook/Plugin/Agent Testing

Features:
1. YAML-based test case definitions
2. Dynamic hook discovery and auto-testing
3. Plugin structure validation
4. Agent definition validation
"""

import json
import subprocess
import sys
import os
import re
import glob
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime

# Try to import yaml, fall back to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    message: str = ""
    output: str = ""
    expected: str = ""
    actual: str = ""


@dataclass
class TestReport:
    test_dir: str
    timestamp: str
    results: list = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total_count(self) -> int:
        return len(self.results)


class PluginTestRunner:
    def __init__(self, test_dir: str, yaml_path: Optional[str] = None):
        self.test_dir = Path(test_dir).resolve()
        self.yaml_path = yaml_path
        self.report = TestReport(
            test_dir=str(self.test_dir),
            timestamp=datetime.now().isoformat()
        )
        self.test_cases = []
        self.settings = {"timeout": 10, "log_dir": ".claude/hooks/logs"}

    def load_yaml_tests(self) -> bool:
        """Load test cases from YAML file"""
        if not self.yaml_path:
            # Try default location
            default_path = self.test_dir / "tests" / "hook-tests.yaml"
            if default_path.exists():
                self.yaml_path = str(default_path)
            else:
                return False

        if not HAS_YAML:
            print("Warning: PyYAML not installed, using basic parsing")
            return False

        try:
            with open(self.yaml_path) as f:
                data = yaml.safe_load(f)

            self.test_cases = data.get("test_cases", [])
            self.settings.update(data.get("settings", {}))
            self.plugin_validation = data.get("plugin_validation", [])
            self.agent_validation = data.get("agent_validation", [])
            return True
        except Exception as e:
            print(f"Warning: Failed to load YAML: {e}")
            return False

    def discover_hooks(self) -> list:
        """Dynamically discover all hook scripts"""
        hooks_dir = self.test_dir / ".claude" / "hooks"
        if not hooks_dir.exists():
            return []

        discovered = []
        for script in hooks_dir.glob("*.sh"):
            if script.name.startswith("."):
                continue

            # Detect event type from filename
            event_type = self._detect_event_type(script.name)
            discovered.append({
                "path": str(script),
                "name": script.name,
                "event": event_type
            })

        return discovered

    def _detect_event_type(self, filename: str) -> str:
        """Detect hook event type from filename"""
        filename_lower = filename.lower()

        if "pretool" in filename_lower or "pre-tool" in filename_lower:
            return "PreToolUse"
        elif "posttool" in filename_lower or "post-tool" in filename_lower:
            return "PostToolUse"
        elif "userprompt" in filename_lower or "prompt" in filename_lower or "context" in filename_lower:
            return "UserPromptSubmit"
        elif "stop" in filename_lower:
            return "Stop"
        elif "session" in filename_lower and "start" in filename_lower:
            return "SessionStart"
        elif "permission" in filename_lower:
            return "PermissionRequest"
        else:
            return "Unknown"

    def _generate_default_input(self, event_type: str) -> dict:
        """Generate default test input for event type"""
        base = {
            "session_id": f"auto-test-{datetime.now().strftime('%H%M%S')}",
            "hook_event_name": event_type,
            "cwd": str(self.test_dir)
        }

        if event_type == "PreToolUse":
            base.update({
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"},
                "tool_use_id": "toolu_auto_001"
            })
        elif event_type == "PostToolUse":
            base.update({
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"},
                "tool_response": {"output": "test"},
                "tool_use_id": "toolu_auto_002"
            })
        elif event_type == "UserPromptSubmit":
            base.update({
                "prompt": "Auto-generated test prompt"
            })
        elif event_type == "Stop":
            base.update({
                "stop_hook_active": False
            })

        return base

    def run_hook_test(self, hook_path: str, input_data: dict, expect: dict) -> TestResult:
        """Run a single hook test"""
        name = expect.get("name", Path(hook_path).name)
        category = expect.get("category", "general")

        try:
            # Run hook with input
            result = subprocess.run(
                [hook_path],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=self.settings.get("timeout", 10),
                cwd=str(self.test_dir)
            )

            output = result.stdout + result.stderr
            passed = True
            message = ""

            # Check exit code
            if "exit_code" in expect:
                if result.returncode != expect["exit_code"]:
                    passed = False
                    message = f"Exit code: expected {expect['exit_code']}, got {result.returncode}"

            # Check output contains
            if "output_contains" in expect and passed:
                if expect["output_contains"] not in output:
                    passed = False
                    message = f"Output missing: '{expect['output_contains']}'"

            # Check JSON path
            if "json_path" in expect and passed:
                try:
                    json_output = json.loads(result.stdout)
                    value = self._get_json_path(json_output, expect["json_path"])

                    if "json_value" in expect:
                        if value != expect["json_value"]:
                            passed = False
                            message = f"JSON value: expected {expect['json_value']}, got {value}"

                    if "json_contains" in expect:
                        if expect["json_contains"] not in str(value):
                            passed = False
                            message = f"JSON missing: '{expect['json_contains']}'"
                except json.JSONDecodeError:
                    if "json_path" in expect:
                        passed = False
                        message = "Invalid JSON output"

            return TestResult(
                name=name,
                category=category,
                passed=passed,
                message=message if not passed else "OK",
                output=output[:500]
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                name=name,
                category=category,
                passed=False,
                message="Timeout"
            )
        except Exception as e:
            return TestResult(
                name=name,
                category=category,
                passed=False,
                message=str(e)
            )

    def _get_json_path(self, obj: Any, path: str) -> Any:
        """Get value from JSON using dot notation path"""
        # Remove leading dot
        path = path.lstrip(".")

        for key in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
        return obj

    def run_yaml_tests(self):
        """Run tests defined in YAML"""
        print("--- YAML-Based Tests ---")

        for test in self.test_cases:
            # Find matching hooks
            hook_pattern = test.get("hook_pattern", "*.sh")
            hooks_dir = self.test_dir / ".claude" / "hooks"
            matching_hooks = list(hooks_dir.glob(hook_pattern))

            if not matching_hooks:
                self.report.results.append(TestResult(
                    name=test["name"],
                    category=test.get("category", "general"),
                    passed=False,
                    message=f"No hooks matching: {hook_pattern}"
                ))
                continue

            # Run test against first matching hook
            hook_path = str(matching_hooks[0])
            input_data = test.get("input", {})
            expect = {
                "name": test["name"],
                "category": test.get("category", "general"),
                **test.get("expect", {})
            }

            result = self.run_hook_test(hook_path, input_data, expect)
            self.report.results.append(result)

            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status}: {result.name}")
            if not result.passed:
                print(f"   {result.message}")

    def run_discovery_tests(self):
        """Run auto-discovery based tests"""
        print("\n--- Auto-Discovery Tests ---")

        discovered = self.discover_hooks()
        if not discovered:
            print("No hooks discovered")
            return

        for hook in discovered:
            # Generate default test
            input_data = self._generate_default_input(hook["event"])

            # Run basic execution test
            result = self.run_hook_test(
                hook["path"],
                input_data,
                {
                    "name": f"[Auto] {hook['name']} executes",
                    "category": "auto-discovery",
                    "exit_code": 0
                }
            )
            self.report.results.append(result)

            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status}: {result.name} ({hook['event']})")

    def validate_plugin_structure(self):
        """Validate plugin structure"""
        print("\n--- Plugin Validation ---")

        # Check plugin.json
        plugin_json = self.test_dir / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            try:
                with open(plugin_json) as f:
                    data = json.load(f)

                has_required = all(k in data for k in ["name", "description"])
                result = TestResult(
                    name="plugin.json valid",
                    category="plugin",
                    passed=has_required,
                    message="OK" if has_required else "Missing required fields"
                )
            except json.JSONDecodeError:
                result = TestResult(
                    name="plugin.json valid",
                    category="plugin",
                    passed=False,
                    message="Invalid JSON"
                )

            self.report.results.append(result)
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status}: {result.name}")

        # Check commands
        commands_dir = self.test_dir / "commands"
        if commands_dir.exists():
            valid = True
            for cmd in commands_dir.glob("*.md"):
                content = cmd.read_text()
                if not content.startswith("---") or "description:" not in content[:500]:
                    valid = False
                    break

            result = TestResult(
                name="Commands have frontmatter",
                category="plugin",
                passed=valid,
                message="OK" if valid else "Missing frontmatter"
            )
            self.report.results.append(result)
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status}: {result.name}")

        # Check skills
        skills_dir = self.test_dir / "skills"
        if skills_dir.exists():
            valid = True
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    if not (skill_dir / "SKILL.md").exists():
                        valid = False
                        break

            result = TestResult(
                name="Skills structured correctly",
                category="plugin",
                passed=valid,
                message="OK" if valid else "Missing SKILL.md"
            )
            self.report.results.append(result)
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status}: {result.name}")

    def validate_agents(self):
        """Validate agent definitions"""
        print("\n--- Agent Validation ---")

        agents_dir = self.test_dir / "agents"
        if not agents_dir.exists():
            return

        agents = list(agents_dir.glob("*.md"))
        if not agents:
            return

        # Check descriptions
        valid = all(
            "description:" in a.read_text()[:500]
            for a in agents
        )
        result = TestResult(
            name="Agents have descriptions",
            category="agent",
            passed=valid,
            message="OK" if valid else "Missing description"
        )
        self.report.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status}: {result.name}")

        # Check tools (accept either 'tools:' or 'allowed-tools:')
        valid = all(
            ("tools:" in a.read_text()[:500] or "allowed-tools:" in a.read_text()[:500])
            for a in agents
        )
        result = TestResult(
            name="Agents have tool lists",
            category="agent",
            passed=valid,
            message="OK" if valid else "Missing tools/allowed-tools"
        )
        self.report.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status}: {result.name}")

    def run_all(self):
        """Run all tests"""
        print("=" * 50)
        print("  Plugin Test Runner")
        print("=" * 50)
        print(f"Directory: {self.test_dir}")
        print()

        # Load YAML if available
        yaml_loaded = self.load_yaml_tests()

        # Run YAML-based tests
        if yaml_loaded and self.test_cases:
            self.run_yaml_tests()

        # Run auto-discovery tests
        self.run_discovery_tests()

        # Validate plugin structure
        self.validate_plugin_structure()

        # Validate agents
        self.validate_agents()

        # Summary
        print()
        print("=" * 50)
        print(f"  Summary: {self.report.passed_count} / {self.report.total_count} passed")
        print("=" * 50)

        return self.report

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Generate markdown report"""
        if not output_path:
            output_path = str(self.test_dir / "TEST-RESULTS.md")

        lines = [
            "# Plugin Test Results",
            f"**Date:** {self.report.timestamp}",
            f"**Directory:** {self.report.test_dir}",
            "",
        ]

        # Group by category
        categories = {}
        for r in self.report.results:
            if r.category not in categories:
                categories[r.category] = []
            categories[r.category].append(r)

        for category, results in categories.items():
            lines.append(f"## {category.title()}")
            for r in results:
                icon = "✅" if r.passed else "❌"
                lines.append(f"- {icon} {r.name}")
                if not r.passed and r.message:
                    lines.append(f"  - {r.message}")
            lines.append("")

        lines.extend([
            "## Summary",
            f"- **Passed:** {self.report.passed_count} / {self.report.total_count}",
            f"- **Failed:** {self.report.failed_count} / {self.report.total_count}",
            "",
            f"**Status:** {'ALL TESTS PASSED ✅' if self.report.failed_count == 0 else 'SOME TESTS FAILED ❌'}"
        ])

        content = "\n".join(lines)

        with open(output_path, "w") as f:
            f.write(content)

        print(f"\nResults saved to: {output_path}")
        return content


def main():
    if len(sys.argv) < 2:
        print("Usage: test-runner.py <test-directory> [yaml-file]")
        sys.exit(1)

    test_dir = sys.argv[1]
    yaml_path = sys.argv[2] if len(sys.argv) > 2 else None

    runner = PluginTestRunner(test_dir, yaml_path)
    report = runner.run_all()
    runner.generate_report()

    # Exit with error if any tests failed
    sys.exit(0 if report.failed_count == 0 else 1)


if __name__ == "__main__":
    main()
