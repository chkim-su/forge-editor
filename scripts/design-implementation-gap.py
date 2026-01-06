#!/usr/bin/env python3
"""
Design-Implementation Gap Detector (W047)

Detects patterns documented in design docs that aren't actually wired up.
The "신발 가게 주인이 맨발" (cobbler's children have no shoes) problem detector.

Usage:
    python3 scripts/design-implementation-gap.py [--deep] [--json]

Options:
    --deep      Use Serena MCP for symbol-level analysis (requires daemon)
    --json      Output in JSON format
    --fix       Suggest fixes (not auto-apply)

Exit codes:
    0 - No gaps found
    1 - Gaps detected
    2 - Warning only (minor gaps)

Gap Categories:
    CLI-to-Hook:    CLI commands exist but not used in hooks
    Doc-to-Code:    Patterns documented but no implementation
    Config-to-Run:  Settings defined but never read
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Gap:
    """Represents a design-implementation gap."""
    category: str  # CLI-to-Hook, Doc-to-Code, Config-to-Run
    severity: str  # high, medium, low
    designed_in: str  # Where the design/pattern is documented
    pattern: str  # The pattern that should be used
    expected_in: str  # Where it should be implemented
    actual_usage: str  # What we found (or "none")
    suggestion: str  # How to fix


@dataclass
class GapReport:
    """Collection of detected gaps."""
    gaps: List[Gap] = field(default_factory=list)

    def add(self, gap: Gap):
        self.gaps.append(gap)

    @property
    def high_severity_count(self) -> int:
        return sum(1 for g in self.gaps if g.severity == "high")

    @property
    def has_blocking_gaps(self) -> bool:
        return self.high_severity_count > 0

    def to_json(self) -> str:
        return json.dumps([g.__dict__ for g in self.gaps], indent=2)

    def print_report(self):
        if not self.gaps:
            print("No design-implementation gaps detected.")
            return

        print(f"\n{'='*60}")
        print(f"DESIGN-IMPLEMENTATION GAP REPORT (W047)")
        print(f"{'='*60}\n")

        for i, gap in enumerate(self.gaps, 1):
            severity_icon = {"high": "", "medium": "", "low": ""}[gap.severity]
            print(f"{i}. [{severity_icon} {gap.severity.upper()}] {gap.category}")
            print(f"   Designed in: {gap.designed_in}")
            print(f"   Pattern: {gap.pattern}")
            print(f"   Expected in: {gap.expected_in}")
            print(f"   Actual: {gap.actual_usage}")
            print(f"   Fix: {gap.suggestion}")
            print()

        print(f"{'='*60}")
        print(f"Summary: {len(self.gaps)} gaps ({self.high_severity_count} high severity)")
        print(f"{'='*60}\n")


def find_plugin_root() -> Path:
    """Find the plugin root directory."""
    # Try CLAUDE_PROJECT_DIR first
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])

    # Try CLAUDE_PLUGIN_ROOT
    if "CLAUDE_PLUGIN_ROOT" in os.environ:
        return Path(os.environ["CLAUDE_PLUGIN_ROOT"])

    # Walk up from script location
    script_dir = Path(__file__).parent
    for parent in [script_dir] + list(script_dir.parents):
        if (parent / ".claude-plugin").exists() or (parent / "hooks").exists():
            return parent

    return Path.cwd()


def grep_pattern(pattern: str, path: Path, recursive: bool = True) -> List[Tuple[str, str]]:
    """Search for pattern and return list of (file, line) matches."""
    try:
        cmd = ["grep", "-rn" if recursive else "-n", pattern, str(path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        matches = []
        for line in result.stdout.strip().split("\n"):
            if line and ":" in line:
                parts = line.split(":", 2)
                if len(parts) >= 2:
                    matches.append((parts[0], parts[-1].strip()))
        return matches
    except Exception:
        return []


def check_file_contains(filepath: Path, pattern: str) -> bool:
    """Check if file contains pattern."""
    if not filepath.exists():
        return False
    try:
        content = filepath.read_text()
        return bool(re.search(pattern, content))
    except Exception:
        return False


# =============================================================================
# Gap Detection Functions
# =============================================================================

def detect_cli_to_hook_gaps(plugin_root: Path, report: GapReport):
    """Detect CLI commands in forge-state.py that aren't used in hooks."""

    forge_state = plugin_root / "scripts" / "forge-state.py"
    hooks_json = plugin_root / "hooks" / "hooks.json"

    if not forge_state.exists():
        return

    # Extract CLI commands from forge-state.py
    content = forge_state.read_text()
    cli_commands = set()

    # Pattern: elif cmd == "command-name":
    for match in re.finditer(r'elif cmd == "([^"]+)":', content):
        cli_commands.add(match.group(1))

    # Also check for def cmd_xxx functions
    for match in re.finditer(r'def cmd_(\w+)\(', content):
        cmd_name = match.group(1).replace("_", "-")
        cli_commands.add(cmd_name)

    # Check which are used in hooks.json
    hooks_content = hooks_json.read_text() if hooks_json.exists() else ""

    # Important CLI commands that SHOULD be in hooks for enforcement
    enforcement_commands = {
        "require-gate": "Gate enforcement - blocks tools without passing gate",
        "check-gate": "Gate status check",
        "check-deps": "Dependency validation",
        "verify-protocol": "Protocol verification",
    }

    for cmd, description in enforcement_commands.items():
        if cmd in cli_commands and cmd not in hooks_content:
            report.add(Gap(
                category="CLI-to-Hook",
                severity="high",
                designed_in=f"scripts/forge-state.py (cmd_{cmd.replace('-', '_')})",
                pattern=f"forge-state.py {cmd}",
                expected_in="hooks/hooks.json",
                actual_usage="Not found in any hook",
                suggestion=f"Add PreToolUse hook: forge-state.py {cmd} <gate-name>"
            ))


def detect_doc_to_code_gaps(plugin_root: Path, report: GapReport):
    """Detect patterns documented in design docs that aren't implemented."""

    # Key patterns that should be wired up
    design_patterns = [
        {
            "doc_pattern": r"require-gate.*validation",
            "doc_files": ["skills/*/references/gate-design.md", "skills/*/references/gate-patterns.md"],
            "impl_pattern": r"require-gate.*(validate_all|validation_passed)",
            "impl_files": ["hooks/hooks.json"],
            "description": "Validation gate enforcement",
        },
        {
            "doc_pattern": r"exit\s*\(?2\)?.*block",
            "doc_files": ["skills/*/references/gate-patterns.md"],
            "impl_pattern": r"exit\s*2",
            "impl_files": ["scripts/*.py"],
            "description": "Exit code 2 for blocking",
        },
    ]

    for pattern_def in design_patterns:
        # Check if documented
        doc_found = False
        for glob_pattern in pattern_def["doc_files"]:
            for doc_file in plugin_root.glob(glob_pattern):
                if check_file_contains(doc_file, pattern_def["doc_pattern"]):
                    doc_found = True
                    break

        if not doc_found:
            continue  # Pattern not documented, no gap

        # Check if implemented
        impl_found = False
        for glob_pattern in pattern_def["impl_files"]:
            for impl_file in plugin_root.glob(glob_pattern):
                if check_file_contains(impl_file, pattern_def["impl_pattern"]):
                    impl_found = True
                    break

        if not impl_found:
            report.add(Gap(
                category="Doc-to-Code",
                severity="medium",
                designed_in=str(pattern_def["doc_files"]),
                pattern=pattern_def["description"],
                expected_in=str(pattern_def["impl_files"]),
                actual_usage="Pattern documented but not fully implemented",
                suggestion="Implement the documented pattern or mark as PLANNED"
            ))


def detect_skill_reference_gaps(plugin_root: Path, report: GapReport):
    """Detect skills referenced in SKILL_REFERENCES but missing actual skill."""

    validate_all = plugin_root / "scripts" / "validate_all.py"
    if not validate_all.exists():
        return

    content = validate_all.read_text()

    # Extract skill references from SKILL_REFERENCES dict
    referenced_skills = set()
    for line in content.split('\n'):
        # Skip comment lines
        if line.strip().startswith('#'):
            continue
        for match in re.finditer(r'"([^"]+)":\s*\(\s*"([^"]+)"', line):
            referenced_skills.add(match.group(2))  # skill name

    # Check if skills exist
    skills_dir = plugin_root / "skills"
    existing_skills = {d.name for d in skills_dir.iterdir() if d.is_dir()} if skills_dir.exists() else set()

    for skill in referenced_skills:
        if skill not in existing_skills:
            report.add(Gap(
                category="Config-to-Run",
                severity="low",
                designed_in="scripts/validate_all.py (SKILL_REFERENCES)",
                pattern=f"Skill reference: {skill}",
                expected_in=f"skills/{skill}/SKILL.md",
                actual_usage="Skill directory not found",
                suggestion=f"Create skills/{skill}/ or remove from SKILL_REFERENCES"
            ))


def detect_hook_script_gaps(plugin_root: Path, report: GapReport):
    """Detect hook scripts referenced but not existing."""

    hooks_json = plugin_root / "hooks" / "hooks.json"
    if not hooks_json.exists():
        return

    try:
        hooks_data = json.loads(hooks_json.read_text())
    except json.JSONDecodeError:
        return

    # Extract script paths from hooks
    script_refs = set()

    def extract_commands(obj):
        if isinstance(obj, dict):
            if "command" in obj:
                cmd = obj["command"]
                # Extract script path from command
                for pattern in [r'python3?\s+"([^"]+)"', r'python3?\s+(\S+\.py)', r'"([^"]+\.sh)"', r'(\S+\.sh)']:
                    match = re.search(pattern, cmd)
                    if match:
                        script_refs.add(match.group(1))
            for v in obj.values():
                extract_commands(v)
        elif isinstance(obj, list):
            for item in obj:
                extract_commands(item)

    extract_commands(hooks_data)

    # Check if scripts exist
    for script_ref in script_refs:
        # Clean up the script reference
        clean_ref = script_ref.strip('"\'')

        # Handle ${CLAUDE_PLUGIN_ROOT} substitution - replace with empty to get relative path
        relative_path = clean_ref.replace("${CLAUDE_PLUGIN_ROOT}/", "")
        relative_path = relative_path.replace("$CLAUDE_PLUGIN_ROOT/", "")
        relative_path = relative_path.replace("${CLAUDE_PLUGIN_ROOT}", "")
        relative_path = relative_path.replace("$CLAUDE_PLUGIN_ROOT", "")

        # Try to find the script
        full_path = plugin_root / relative_path

        if not full_path.exists():
            report.add(Gap(
                category="Config-to-Run",
                severity="high",
                designed_in="hooks/hooks.json",
                pattern=f"Hook script: {relative_path}",
                expected_in=str(full_path),
                actual_usage="Script file not found",
                suggestion=f"Create {relative_path} or fix path in hooks.json"
            ))


# =============================================================================
# Serena MCP Deep Analysis
# =============================================================================

def serena_deep_analysis(plugin_root: Path, report: GapReport):
    """Use Serena MCP for symbol-level gap detection."""

    serena_query = plugin_root / "scripts" / "serena-query"
    if not serena_query.exists():
        print("  [skip] serena-query not available for deep analysis")
        return

    # Check if Serena daemon is running
    try:
        result = subprocess.run(
            ["python3", str(serena_query), "get_current_config"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("  [skip] Serena daemon not running")
            return
    except Exception:
        print("  [skip] Could not connect to Serena daemon")
        return

    print("  [deep] Serena MCP analysis...")

    # Find CLI functions and check for references
    try:
        # Get symbols from forge-state.py
        result = subprocess.run(
            ["python3", str(serena_query), "get_symbols_overview",
             "scripts/forge-state.py", "--depth", "1"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            symbols = json.loads(result.stdout)

            # Check each cmd_ function for references
            for symbol in symbols.get("functions", []):
                if symbol.startswith("cmd_"):
                    ref_result = subprocess.run(
                        ["python3", str(serena_query), "find_referencing_symbols",
                         symbol, "--path", "scripts/forge-state.py"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if ref_result.returncode == 0:
                        refs = json.loads(ref_result.stdout)
                        # Filter to only external references
                        external_refs = [r for r in refs if "forge-state.py" not in r.get("file", "")]

                        if not external_refs:
                            cmd_name = symbol.replace("cmd_", "").replace("_", "-")
                            report.add(Gap(
                                category="CLI-to-Hook",
                                severity="medium",
                                designed_in=f"scripts/forge-state.py::{symbol}",
                                pattern=f"forge-state.py {cmd_name}",
                                expected_in="hooks/hooks.json or other scripts",
                                actual_usage="No external references found (Serena)",
                                suggestion=f"Consider using {cmd_name} in hooks or remove if unused"
                            ))
    except Exception as e:
        print(f"  [warn] Serena analysis error: {e}")


# =============================================================================
# Main
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Design-Implementation Gap Detector")
    parser.add_argument("--deep", action="store_true", help="Use Serena MCP for deep analysis")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    plugin_root = find_plugin_root()
    report = GapReport()

    if not args.quiet:
        print(f"Scanning for design-implementation gaps in: {plugin_root}")

    # Run detection
    if not args.quiet:
        print("  [check] CLI-to-Hook gaps...")
    detect_cli_to_hook_gaps(plugin_root, report)

    if not args.quiet:
        print("  [check] Doc-to-Code gaps...")
    detect_doc_to_code_gaps(plugin_root, report)

    if not args.quiet:
        print("  [check] Skill reference gaps...")
    detect_skill_reference_gaps(plugin_root, report)

    if not args.quiet:
        print("  [check] Hook script gaps...")
    detect_hook_script_gaps(plugin_root, report)

    # Optional deep analysis
    if args.deep:
        serena_deep_analysis(plugin_root, report)

    # Output
    if args.json:
        print(report.to_json())
    else:
        report.print_report()

    # Exit code
    if report.has_blocking_gaps:
        sys.exit(1)
    elif report.gaps:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
