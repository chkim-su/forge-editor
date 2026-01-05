#!/usr/bin/env python3
"""
Claude Code Plugin E2E Test Runner

Executes real Claude CLI commands to test plugins end-to-end.
Uses actual LLM calls - costs apply!

Usage:
    python3 e2e-test-runner.py <test-yaml> [--dry-run] [--model haiku]
"""

import json
import subprocess
import sys
import os
import re
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("Warning: PyYAML not installed. Install with: pip install pyyaml")


@dataclass
class E2ETestResult:
    name: str
    passed: bool
    prompt: str
    expected: dict
    actual_output: str
    error: str = ""
    duration_ms: int = 0
    cost_usd: float = 0.0


@dataclass
class E2ETestReport:
    plugin_dir: str
    timestamp: str
    model: str
    total_cost_usd: float = 0.0
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


class E2ETestRunner:
    """
    E2E Test Runner for Claude Code Plugins

    Executes tests by:
    1. Spawning claude CLI with -p (print mode)
    2. Capturing JSON output
    3. Validating against expected patterns
    """

    def __init__(
        self,
        plugin_dir: str,
        model: str = "haiku",
        max_budget: float = 0.50,
        skip_permissions: bool = True
    ):
        self.plugin_dir = Path(plugin_dir).resolve()
        self.model = model
        self.max_budget = max_budget
        self.skip_permissions = skip_permissions
        self.report = E2ETestReport(
            plugin_dir=str(self.plugin_dir),
            timestamp=datetime.now().isoformat(),
            model=model
        )

    def run_claude(
        self,
        prompt: str,
        allowed_tools: Optional[list] = None,
        timeout: int = 60
    ) -> tuple[str, dict, float]:
        """
        Execute claude CLI and return (output, json_result, duration_ms)
        """
        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--model", self.model,
            "--max-budget-usd", str(self.max_budget),
        ]

        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        if allowed_tools:
            cmd.extend(["--allowed-tools", ",".join(allowed_tools)])

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.plugin_dir)
            )
            duration_ms = int((time.time() - start) * 1000)

            output = result.stdout

            # Parse JSON output
            try:
                json_result = json.loads(output)
            except json.JSONDecodeError:
                json_result = {"raw_output": output, "parse_error": True}

            return output, json_result, duration_ms

        except subprocess.TimeoutExpired:
            return "", {"error": "timeout"}, timeout * 1000
        except Exception as e:
            return "", {"error": str(e)}, 0

    def check_assertion(self, actual: Any, assertion: dict) -> tuple[bool, str]:
        """
        Check if actual output matches assertion.

        Supported assertions:
        - contains: string contains substring
        - not_contains: string does not contain substring
        - matches: regex match
        - equals: exact match
        - json_path: check value at JSON path
        - tool_used: specific tool was called
        - hook_triggered: specific hook was triggered
        """
        if "contains" in assertion:
            pattern = assertion["contains"]
            if isinstance(actual, str):
                if pattern.lower() in actual.lower():
                    return True, f"Contains '{pattern}'"
                return False, f"Does not contain '{pattern}'"
            return False, "Output is not a string"

        if "not_contains" in assertion:
            pattern = assertion["not_contains"]
            if isinstance(actual, str):
                if pattern.lower() not in actual.lower():
                    return True, f"Does not contain '{pattern}'"
                return False, f"Should not contain '{pattern}'"
            return True, "Output is not a string"

        if "matches" in assertion:
            pattern = assertion["matches"]
            if isinstance(actual, str):
                if re.search(pattern, actual, re.IGNORECASE | re.DOTALL):
                    return True, f"Matches '{pattern}'"
                return False, f"Does not match '{pattern}'"
            return False, "Output is not a string"

        if "equals" in assertion:
            expected = assertion["equals"]
            if actual == expected:
                return True, f"Equals '{expected}'"
            return False, f"Expected '{expected}', got '{actual}'"

        if "tool_used" in assertion:
            tool_name = assertion["tool_used"]
            if isinstance(actual, dict):
                # Check in JSON output for tool usage
                output_str = json.dumps(actual)
                if f'"tool_name":"{tool_name}"' in output_str or f'"name":"{tool_name}"' in output_str:
                    return True, f"Tool '{tool_name}' was used"
            if isinstance(actual, str) and tool_name in actual:
                return True, f"Tool '{tool_name}' was used"
            return False, f"Tool '{tool_name}' was not used"

        if "exit_success" in assertion:
            if assertion["exit_success"]:
                if isinstance(actual, dict) and actual.get("error"):
                    return False, f"Expected success but got error: {actual.get('error')}"
                return True, "Completed successfully"
            else:
                if isinstance(actual, dict) and actual.get("error"):
                    return True, "Failed as expected"
                return False, "Expected failure but succeeded"

        return False, f"Unknown assertion type: {assertion}"

    def run_test(self, test_case: dict, dry_run: bool = False) -> E2ETestResult:
        """Run a single E2E test case"""
        name = test_case.get("name", "Unnamed test")
        prompt = test_case.get("prompt", "")
        assertions = test_case.get("expect", [])
        allowed_tools = test_case.get("allowed_tools")
        timeout = test_case.get("timeout", 60)

        if not prompt:
            return E2ETestResult(
                name=name,
                passed=False,
                prompt="",
                expected={"error": "No prompt specified"},
                actual_output="",
                error="No prompt specified"
            )

        if dry_run:
            print(f"  [DRY-RUN] Would execute: claude -p \"{prompt[:50]}...\"")
            return E2ETestResult(
                name=name,
                passed=True,
                prompt=prompt,
                expected=assertions,
                actual_output="[DRY-RUN]"
            )

        # Execute claude CLI
        output, json_result, duration_ms = self.run_claude(
            prompt=prompt,
            allowed_tools=allowed_tools,
            timeout=timeout
        )

        # Check all assertions
        all_passed = True
        error_messages = []

        for assertion in assertions if isinstance(assertions, list) else [assertions]:
            # Check against both raw output and JSON result
            passed_raw, msg_raw = self.check_assertion(output, assertion)
            passed_json, msg_json = self.check_assertion(json_result, assertion)

            if not (passed_raw or passed_json):
                all_passed = False
                error_messages.append(f"{msg_raw} / {msg_json}")

        return E2ETestResult(
            name=name,
            passed=all_passed,
            prompt=prompt,
            expected=assertions,
            actual_output=output[:500] if len(output) > 500 else output,
            error="; ".join(error_messages) if error_messages else "",
            duration_ms=duration_ms
        )

    def run_all_tests(self, test_file: str, dry_run: bool = False) -> E2ETestReport:
        """Run all tests from YAML file"""
        if not HAS_YAML:
            print("Error: PyYAML required for E2E tests")
            return self.report

        test_path = Path(test_file)
        if not test_path.exists():
            print(f"Error: Test file not found: {test_file}")
            return self.report

        with open(test_path) as f:
            test_data = yaml.safe_load(f)

        test_cases = test_data.get("e2e_tests", [])

        print("=" * 50)
        print("  Claude Code E2E Test Runner")
        print("=" * 50)
        print(f"Plugin: {self.plugin_dir}")
        print(f"Model: {self.model}")
        print(f"Max Budget: ${self.max_budget}")
        print(f"Tests: {len(test_cases)}")
        if dry_run:
            print("MODE: DRY-RUN (no actual API calls)")
        print()

        for test_case in test_cases:
            name = test_case.get("name", "Unnamed")
            print(f"Running: {name}...", end=" ", flush=True)

            result = self.run_test(test_case, dry_run=dry_run)
            self.report.results.append(result)

            if result.passed:
                print(f"✅ PASS ({result.duration_ms}ms)")
            else:
                print(f"❌ FAIL")
                print(f"   Error: {result.error}")

        print()
        print("=" * 50)
        print(f"  Summary: {self.report.passed_count} / {self.report.total_count} passed")
        print("=" * 50)

        return self.report


def generate_sample_e2e_tests(output_path: str):
    """Generate sample E2E test YAML file"""
    sample = {
        "version": "1.0",
        "description": "E2E Tests for Claude Code Plugin",
        "settings": {
            "model": "haiku",
            "max_budget_usd": 0.50,
            "timeout": 60
        },
        "e2e_tests": [
            {
                "name": "Skill invocation test",
                "prompt": "/forge-editor:wizard --help",
                "expect": [
                    {"contains": "wizard"},
                    {"not_contains": "error"}
                ],
                "timeout": 30
            },
            {
                "name": "Hook trigger verification",
                "prompt": "Run: echo 'test'",
                "allowed_tools": ["Bash"],
                "expect": [
                    {"tool_used": "Bash"},
                    {"exit_success": True}
                ]
            },
            {
                "name": "Security hook blocks dangerous command",
                "prompt": "Run exactly this command: rm -rf /",
                "allowed_tools": ["Bash"],
                "expect": [
                    {"not_contains": "removed"},
                    {"contains": "dangerous"}
                ]
            },
            {
                "name": "Agent spawning works",
                "prompt": "Use the Task tool to spawn a quick explore agent to find README files",
                "allowed_tools": ["Task", "Glob"],
                "expect": [
                    {"tool_used": "Task"},
                    {"exit_success": True}
                ],
                "timeout": 120
            }
        ]
    }

    with open(output_path, "w") as f:
        yaml.dump(sample, f, default_flow_style=False, allow_unicode=True)

    print(f"Sample E2E tests written to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code E2E Test Runner")
    parser.add_argument("test_file", nargs="?", help="YAML test file")
    parser.add_argument("--plugin-dir", "-d", default=".", help="Plugin directory")
    parser.add_argument("--model", "-m", default="haiku", help="Model to use (haiku/sonnet/opus)")
    parser.add_argument("--max-budget", "-b", type=float, default=0.50, help="Max budget in USD")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually run tests")
    parser.add_argument("--generate-sample", "-g", help="Generate sample test YAML to specified path")
    parser.add_argument("--no-skip-permissions", action="store_true", help="Don't skip permission checks")
    args = parser.parse_args()

    if args.generate_sample:
        if not HAS_YAML:
            print("Error: PyYAML required. Install with: pip install pyyaml")
            sys.exit(1)
        generate_sample_e2e_tests(args.generate_sample)
        sys.exit(0)

    if not args.test_file:
        print("Usage: python3 e2e-test-runner.py <test.yaml> [--dry-run]")
        print("       python3 e2e-test-runner.py --generate-sample tests/e2e-tests.yaml")
        sys.exit(1)

    runner = E2ETestRunner(
        plugin_dir=args.plugin_dir,
        model=args.model,
        max_budget=args.max_budget,
        skip_permissions=not args.no_skip_permissions
    )

    report = runner.run_all_tests(args.test_file, dry_run=args.dry_run)

    # Exit with error code if any tests failed
    sys.exit(0 if report.failed_count == 0 else 1)


if __name__ == "__main__":
    main()
