#!/usr/bin/env python3
"""
Skillmaker Self-Test Suite

Comprehensive testing of skillmaker in a virtual session context.
Tests semantic analysis, MUST keyword filtering, hook coverage, and all components.

Usage:
    python3 scripts/self-test.py              # Run all tests
    python3 scripts/self-test.py --semantic   # Semantic analysis tests only
    python3 scripts/self-test.py --json       # JSON output
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field


@dataclass
class TestResult:
    passed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_pass(self, name: str, msg: str = ""):
        self.passed.append(f"{name}: {msg}" if msg else name)

    def add_fail(self, name: str, msg: str = ""):
        self.failed.append(f"{name}: {msg}" if msg else name)

    def add_warn(self, name: str, msg: str = ""):
        self.warnings.append(f"{name}: {msg}" if msg else name)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "summary": {
                "total": len(self.passed) + len(self.failed),
                "passed": len(self.passed),
                "failed": len(self.failed),
                "warnings": len(self.warnings)
            }
        }


def get_project_root() -> Path:
    """Find skillmaker project root."""
    script_dir = Path(__file__).parent
    return script_dir.parent


class MUSTKeywordAnalyzer:
    """
    Tests the MUST keyword filtering logic (Phase 1.5).
    Ensures meta-documentation is not counted as enforcement requirements.
    """

    # Patterns that indicate meta-documentation (should be EXCLUDED)
    META_PATTERNS = [
        r'```[\s\S]*?```',  # Code blocks
        r'\|.*MUST.*\|',     # Table cells
        r'If keyword in \[.*MUST.*\]',  # Conditional about MUST
        r'"MUST.*?"',        # Quoted examples
        r"'MUST.*?'",        # Single-quoted examples
        r'`MUST.*?`',        # Backtick examples
        r'MUST keywords? (should|are|is|that)',  # Explaining MUST
        r'(explain|detect|find|search|scan).*MUST',  # Meta operations
        r'\*\*MUST',         # Bold MUST (markdown emphasis)
        r'MUST.*→',          # Arrow notation (pattern tables)
        r'Pattern.*MUST',    # Pattern definition
        r'MUST.*SKIP',       # Skip instruction
        r'SKIP.*MUST',       # Skip instruction
        r'example.*MUST',    # Example context
        r'MUST.*example',    # Example context
    ]

    # Patterns that indicate actual enforcement (should be COUNTED)
    ENFORCEMENT_PATTERNS = [
        r'^(?!\|).*\bMUST\b(?! keyword)',  # MUST not in table, not "MUST keyword"
        r'you MUST',
        r'agents? MUST',
        r'MUST (use|validate|complete|run|pass)',
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = TestResult()

    def is_in_code_block(self, content: str, match_start: int) -> bool:
        """Check if position is inside a code block."""
        # Count ``` before this position
        before = content[:match_start]
        fence_count = before.count('```')
        return fence_count % 2 == 1  # Odd means inside code block

    def is_in_table(self, content: str, match_start: int) -> bool:
        """Check if position is inside a table row."""
        # Find the line containing this match
        line_start = content.rfind('\n', 0, match_start) + 1
        line_end = content.find('\n', match_start)
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]
        return line.strip().startswith('|') and line.strip().endswith('|')

    def is_in_references_folder(self, file_path: Path) -> bool:
        """Check if file is in references/ folder."""
        return 'references' in file_path.parts

    def is_meta_documentation(self, content: str, match: re.Match, file_path: Path = None) -> bool:
        """Determine if a MUST match is meta-documentation."""
        match_start = match.start()
        match_text = match.group()

        # Check if file is in references folder
        if file_path and self.is_in_references_folder(file_path):
            return True

        # Check if in code block
        if self.is_in_code_block(content, match_start):
            return True

        # Check if in table
        if self.is_in_table(content, match_start):
            return True

        # Get surrounding context (80 chars before and after for better detection)
        context_start = max(0, match_start - 80)
        context_end = min(len(content), match_start + len(match_text) + 80)
        context = content[context_start:context_end]

        # Additional context checks
        line_start = content.rfind('\n', 0, match_start) + 1
        line_end = content.find('\n', match_start)
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]

        # Check if line is a header about patterns/filtering
        if re.search(r'^#+.*(?:Pattern|Filter|Phase|Heuristic)', line, re.IGNORECASE):
            return True

        # Check if "Not just" pattern (explaining what we don't do)
        if 'Not just' in context or 'not just' in context:
            return True

        # Check for meta patterns
        for pattern in self.META_PATTERNS:
            if re.search(pattern, context, re.IGNORECASE):
                return True

        return False

    def analyze_file(self, file_path: Path) -> Tuple[int, int, List[str]]:
        """
        Analyze a file for MUST keywords.
        Returns: (total_must, actual_enforcement, list of enforcement requirements)
        """
        content = file_path.read_text()

        # Find all MUST occurrences
        must_matches = list(re.finditer(r'\bMUST\b', content))
        total = len(must_matches)

        enforcement = []
        for match in must_matches:
            if not self.is_meta_documentation(content, match, file_path):
                # Get the line for context
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_end = content.find('\n', match.start())
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end].strip()
                enforcement.append(line)

        return total, len(enforcement), enforcement

    def run_tests(self) -> TestResult:
        """Run MUST keyword filtering tests."""

        # Test 1: skill-design/SKILL.md should have mostly meta-documentation
        skill_design = self.project_root / "skills/skill-design/SKILL.md"
        if skill_design.exists():
            total, actual, lines = self.analyze_file(skill_design)
            # skill-design teaches about MUST, so most should be meta
            if actual <= 2 and total >= 5:
                self.results.add_pass(
                    "skill-design MUST filtering",
                    f"Correctly filtered: {total} total, {actual} actual enforcement"
                )
            else:
                self.results.add_fail(
                    "skill-design MUST filtering",
                    f"Expected mostly meta-docs, got {actual}/{total} as enforcement"
                )

        # Test 2: hook-reasoning-engine should have few actual enforcement
        hook_engine = self.project_root / "agents/hook-reasoning-engine.md"
        if hook_engine.exists():
            total, actual, lines = self.analyze_file(hook_engine)
            if actual <= 3:  # Most MUST in this file explain the concept
                self.results.add_pass(
                    "hook-reasoning-engine MUST filtering",
                    f"Correctly filtered: {total} total, {actual} actual"
                )
            else:
                self.results.add_fail(
                    "hook-reasoning-engine MUST filtering",
                    f"Too many false positives: {actual}/{total}"
                )

        # Test 3: orchestration-patterns should have real enforcement
        orch_patterns = self.project_root / "skills/orchestration-patterns/SKILL.md"
        if orch_patterns.exists():
            total, actual, lines = self.analyze_file(orch_patterns)
            if actual >= 1:  # Should have at least one real enforcement
                self.results.add_pass(
                    "orchestration-patterns enforcement",
                    f"Found {actual} actual enforcement requirements"
                )
            else:
                self.results.add_warn(
                    "orchestration-patterns enforcement",
                    f"No actual enforcement found (may be OK)"
                )

        # Test 4: references/ folder should be all meta-documentation
        references_must = 0
        references_enforcement = 0
        for ref_file in self.project_root.rglob("references/*.md"):
            total, actual, _ = self.analyze_file(ref_file)
            references_must += total
            references_enforcement += actual

        if references_must > 0:
            if references_enforcement == 0:
                self.results.add_pass(
                    "references/ folder filtering",
                    f"All {references_must} MUST keywords correctly filtered as meta-docs"
                )
            elif references_enforcement / references_must < 0.1:
                self.results.add_pass(
                    "references/ folder filtering",
                    f"{references_enforcement}/{references_must} enforcement (< 10%, acceptable)"
                )
            else:
                self.results.add_fail(
                    "references/ folder filtering",
                    f"Too many false positives: {references_enforcement}/{references_must}"
                )

        return self.results


class HookCoverageAnalyzer:
    """Tests hook coverage calculation."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = TestResult()

    def get_hooks(self) -> Dict[str, List[str]]:
        """Get all configured hooks."""
        hooks_file = self.project_root / "hooks/hooks.json"
        if not hooks_file.exists():
            return {}

        with open(hooks_file) as f:
            data = json.load(f)

        hooks = data.get("hooks", {})
        result = {}
        for event, matchers in hooks.items():
            result[event] = []
            for matcher in matchers:
                if "matcher" in matcher:
                    result[event].append(matcher["matcher"])
                else:
                    result[event].append("*")

        return result

    def run_tests(self) -> TestResult:
        """Run hook coverage tests."""
        hooks = self.get_hooks()

        # Test 1: Core events should have hooks
        core_events = ["PreToolUse", "PostToolUse", "UserPromptSubmit"]
        for event in core_events:
            if event in hooks and hooks[event]:
                self.results.add_pass(
                    f"{event} hook coverage",
                    f"Covers: {', '.join(hooks[event])}"
                )
            else:
                self.results.add_fail(f"{event} hook coverage", "No hooks configured")

        # Test 2: Critical tools should have PreToolUse hooks
        critical_tools = ["Write", "Edit", "Bash"]
        pre_hooks = hooks.get("PreToolUse", [])
        for tool in critical_tools:
            if tool in pre_hooks or "*" in pre_hooks:
                self.results.add_pass(f"PreToolUse:{tool}", "Covered")
            else:
                self.results.add_fail(f"PreToolUse:{tool}", "Not covered")

        # Test 3: Task tool should have PostToolUse hook
        post_hooks = hooks.get("PostToolUse", [])
        if "Task" in post_hooks or "*" in post_hooks:
            self.results.add_pass("PostToolUse:Task", "Covered")
        else:
            self.results.add_warn("PostToolUse:Task", "Not covered (optional)")

        return self.results


class ComponentIntegrityTester:
    """Tests all skillmaker components for integrity."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = TestResult()

    def load_marketplace_config(self) -> Optional[dict]:
        """Load marketplace.json."""
        marketplace_path = self.project_root / ".claude-plugin/marketplace.json"
        if marketplace_path.exists():
            with open(marketplace_path) as f:
                return json.load(f)
        return None

    def test_skills(self, config: dict) -> None:
        """Test all registered skills exist and have valid structure."""
        if not config or "plugins" not in config:
            self.results.add_fail("Skills", "No marketplace config")
            return

        for plugin in config.get("plugins", []):
            for skill_path in plugin.get("skills", []):
                skill_name = skill_path.replace("./skills/", "").rstrip("/")
                skill_dir = self.project_root / "skills" / skill_name
                skill_md = skill_dir / "SKILL.md"

                if not skill_dir.exists():
                    self.results.add_fail(f"Skill:{skill_name}", "Directory not found")
                elif not skill_md.exists():
                    self.results.add_fail(f"Skill:{skill_name}", "SKILL.md not found")
                else:
                    # Check frontmatter
                    content = skill_md.read_text()
                    if content.startswith("---"):
                        self.results.add_pass(f"Skill:{skill_name}", "OK")
                    else:
                        self.results.add_fail(f"Skill:{skill_name}", "Missing frontmatter")

    def test_agents(self, config: dict) -> None:
        """Test all registered agents exist and have valid structure."""
        if not config or "plugins" not in config:
            return

        for plugin in config.get("plugins", []):
            for agent_path in plugin.get("agents", []):
                agent_file = self.project_root / agent_path.lstrip("./")

                if not agent_file.exists():
                    self.results.add_fail(f"Agent:{agent_path}", "File not found")
                else:
                    content = agent_file.read_text()
                    if content.startswith("---"):
                        # Check for required fields
                        if "description:" in content[:500]:
                            self.results.add_pass(f"Agent:{agent_file.stem}", "OK")
                        else:
                            self.results.add_fail(f"Agent:{agent_file.stem}", "Missing description")
                    else:
                        self.results.add_fail(f"Agent:{agent_file.stem}", "Missing frontmatter")

    def test_commands(self, config: dict) -> None:
        """Test all registered commands exist."""
        if not config or "plugins" not in config:
            return

        for plugin in config.get("plugins", []):
            for cmd_path in plugin.get("commands", []):
                cmd_file = self.project_root / cmd_path.lstrip("./")

                if not cmd_file.exists():
                    self.results.add_fail(f"Command:{cmd_path}", "File not found")
                else:
                    self.results.add_pass(f"Command:{cmd_file.stem}", "OK")

    def run_tests(self) -> TestResult:
        """Run all component integrity tests."""
        config = self.load_marketplace_config()

        if not config:
            self.results.add_fail("marketplace.json", "Not found")
            return self.results

        self.results.add_pass("marketplace.json", "Valid")

        self.test_skills(config)
        self.test_agents(config)
        self.test_commands(config)

        return self.results


class SemanticAnalyzerTester:
    """Tests the semantic analysis agents."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = TestResult()

    def test_diagnostic_orchestrator(self) -> None:
        """Test diagnostic-orchestrator has required sections."""
        agent_file = self.project_root / "agents/diagnostic-orchestrator.md"
        if not agent_file.exists():
            self.results.add_fail("diagnostic-orchestrator", "File not found")
            return

        content = agent_file.read_text()

        # Check for Phase 1.5 false positive filtering mention
        if "False Positive" in content or "Phase 1.5" in content:
            self.results.add_pass(
                "diagnostic-orchestrator:false-positive-handling",
                "Contains false positive filtering guidance"
            )
        else:
            self.results.add_fail(
                "diagnostic-orchestrator:false-positive-handling",
                "Missing false positive filtering guidance"
            )

        # Check for dispatch rules
        if "Dispatch" in content:
            self.results.add_pass("diagnostic-orchestrator:dispatch-rules", "Has dispatch rules")
        else:
            self.results.add_warn("diagnostic-orchestrator:dispatch-rules", "Missing dispatch rules")

    def test_hook_reasoning_engine(self) -> None:
        """Test hook-reasoning-engine has Phase 1.5 filtering."""
        agent_file = self.project_root / "agents/hook-reasoning-engine.md"
        if not agent_file.exists():
            self.results.add_fail("hook-reasoning-engine", "File not found")
            return

        content = agent_file.read_text()

        # Check for Phase 1.5
        if "Phase 1.5" in content:
            self.results.add_pass(
                "hook-reasoning-engine:phase-1.5",
                "Has Phase 1.5 filtering"
            )
        else:
            self.results.add_fail(
                "hook-reasoning-engine:phase-1.5",
                "Missing Phase 1.5 filtering (CRITICAL)"
            )

        # Check for meta-documentation exclusion
        if "Meta-documentation" in content or "meta-doc" in content.lower():
            self.results.add_pass(
                "hook-reasoning-engine:meta-doc-filter",
                "Has meta-documentation filter"
            )
        else:
            self.results.add_fail(
                "hook-reasoning-engine:meta-doc-filter",
                "Missing meta-documentation filter"
            )

    def run_tests(self) -> TestResult:
        """Run semantic analyzer tests."""
        self.test_diagnostic_orchestrator()
        self.test_hook_reasoning_engine()
        return self.results


def run_all_tests(project_root: Path, semantic_only: bool = False) -> Dict[str, TestResult]:
    """Run all test suites."""
    results = {}

    if semantic_only:
        # Semantic analysis tests only
        results["MUST Keyword Filtering"] = MUSTKeywordAnalyzer(project_root).run_tests()
        results["Semantic Analyzer"] = SemanticAnalyzerTester(project_root).run_tests()
    else:
        # All tests
        results["Component Integrity"] = ComponentIntegrityTester(project_root).run_tests()
        results["Hook Coverage"] = HookCoverageAnalyzer(project_root).run_tests()
        results["MUST Keyword Filtering"] = MUSTKeywordAnalyzer(project_root).run_tests()
        results["Semantic Analyzer"] = SemanticAnalyzerTester(project_root).run_tests()

    return results


def print_results(results: Dict[str, TestResult], json_output: bool = False):
    """Print test results."""
    if json_output:
        output = {}
        for suite, result in results.items():
            output[suite] = result.to_dict()
        print(json.dumps(output, indent=2))
        return

    total_passed = 0
    total_failed = 0
    total_warnings = 0

    print("=" * 70)
    print("SKILLMAKER SELF-TEST RESULTS")
    print("=" * 70)

    for suite, result in results.items():
        print(f"\n## {suite}")
        print("-" * 50)

        for msg in result.failed:
            print(f"  ❌ FAIL: {msg}")
        for msg in result.warnings:
            print(f"  ⚠️  WARN: {msg}")
        for msg in result.passed:
            print(f"  ✅ PASS: {msg}")

        total_passed += len(result.passed)
        total_failed += len(result.failed)
        total_warnings += len(result.warnings)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total Tests: {total_passed + total_failed}")
    print(f"  Passed:      {total_passed}")
    print(f"  Failed:      {total_failed}")
    print(f"  Warnings:    {total_warnings}")
    print()

    if total_failed > 0:
        print("STATUS: ❌ SELF-TEST FAILED")
        return 1
    elif total_warnings > 0:
        print("STATUS: ⚠️  PASSED WITH WARNINGS")
        return 0
    else:
        print("STATUS: ✅ ALL SELF-TESTS PASSED")
        return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skillmaker Self-Test Suite")
    parser.add_argument("--semantic", action="store_true", help="Semantic tests only")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    project_root = get_project_root()

    print(f"Project: {project_root}")
    print()

    results = run_all_tests(project_root, semantic_only=args.semantic)
    exit_code = print_results(results, json_output=args.json)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
