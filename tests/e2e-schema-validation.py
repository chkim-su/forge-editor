#!/usr/bin/env python3
"""
Forge Schema Validation E2E Tests

Tests that Forge's runtime validation:
1. Detects all expected schema errors
2. Auto-fixes safe issues correctly
3. Provides correct guidance for manual fixes

Run with: python3 e2e-schema-validation.py [--verbose]
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# Configuration
FORGE_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", "/workspace/forge"))
FIXTURES_DIR = FORGE_ROOT / "tests" / "fixtures"
VALIDATOR_SCRIPT = FORGE_ROOT / "scripts" / "schema-validator.py"


class TestResult:
    """Track test results."""
    def __init__(self, verbose: bool = False):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.verbose = verbose

    def success(self, name: str, detail: str = ""):
        self.passed += 1
        if self.verbose and detail:
            print(f"  ✓ {name}: {detail}")
        else:
            print(f"  ✓ {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ✗ {name}")
        print(f"    Reason: {reason}")

    def summary(self) -> int:
        print(f"\n{'='*60}")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print('='*60)
        return 0 if self.failed == 0 else 1


def run_validator(plugin_dir: Path, fix: bool = False, json_output: bool = True) -> dict:
    """Run schema validator on a plugin directory."""
    args = ["python3", str(VALIDATOR_SCRIPT), str(plugin_dir)]
    if fix:
        args.append("--fix")
    if json_output:
        args.append("--json")
    
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_dir)}
    )
    
    if json_output:
        try:
            return {
                "data": json.loads(result.stdout),
                "returncode": result.returncode,
                "stderr": result.stderr
            }
        except json.JSONDecodeError:
            return {
                "data": None,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "parse_error": True
            }
    else:
        return {
            "stdout": result.stdout,
            "returncode": result.returncode,
            "stderr": result.stderr
        }


def copy_fixture(fixture_name: str, dest_name: str) -> Path:
    """Copy a fixture to a temp location for modification tests."""
    src = FIXTURES_DIR / fixture_name
    dest = FIXTURES_DIR / dest_name
    
    if dest.exists():
        shutil.rmtree(dest)
    
    shutil.copytree(src, dest)
    return dest


def cleanup_fixture(dest_name: str):
    """Remove a copied fixture."""
    dest = FIXTURES_DIR / dest_name
    if dest.exists():
        shutil.rmtree(dest)


# =============================================================================
# TEST: Valid Plugin Passes
# =============================================================================

def test_valid_plugin_passes(results: TestResult):
    """Valid plugin should pass validation with no errors."""
    plugin_dir = FIXTURES_DIR / "valid-plugin"
    
    if not plugin_dir.exists():
        results.fail("valid_plugin_passes", f"Fixture not found: {plugin_dir}")
        return
    
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("valid_plugin_passes", f"JSON parse error: {result.get('stdout')}")
        return
    
    data = result.get("data", {})
    
    if result["returncode"] == 0 and data.get("is_valid"):
        error_count = data.get("summary", {}).get("error_count", 0)
        results.success("valid_plugin_passes", f"No errors (warnings: {data.get('summary', {}).get('warning_count', 0)})")
    else:
        errors = data.get("errors", [])
        error_msgs = [e.get("message") for e in errors]
        results.fail("valid_plugin_passes", f"Should be valid but got errors: {error_msgs}")


# =============================================================================
# TEST: Broken Plugin Detected
# =============================================================================

def test_broken_plugin_detected(results: TestResult):
    """Broken plugin should be detected with specific errors."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    
    if not plugin_dir.exists():
        results.fail("broken_plugin_detected", f"Fixture not found: {plugin_dir}")
        return
    
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("broken_plugin_detected", f"JSON parse error: {result.get('stdout')}")
        return
    
    data = result.get("data", {})
    
    # Should fail validation
    if result["returncode"] != 1 or data.get("is_valid"):
        results.fail("broken_plugin_detected", "Should fail validation")
        return
    
    results.success("broken_plugin_detected", f"Found {len(data.get('errors', []))} errors")


def test_broken_plugin_missing_description(results: TestResult):
    """Detect missing description in plugin.json."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("missing_plugin_description", "JSON parse error")
        return
    
    data = result.get("data", {})
    errors = data.get("errors", [])
    
    has_desc_error = any(
        "description" in e.get("message", "").lower() and 
        "plugin.json" in e.get("component", "")
        for e in errors
    )
    
    if has_desc_error:
        results.success("missing_plugin_description")
    else:
        results.fail("missing_plugin_description", 
                    f"Should detect missing description. Errors: {[e.get('message') for e in errors]}")


def test_broken_plugin_invalid_version(results: TestResult):
    """Detect invalid semver format (1.0 instead of 1.0.0)."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("invalid_version_format", "JSON parse error")
        return
    
    data = result.get("data", {})
    warnings = data.get("warnings", [])
    
    has_version_warning = any(
        "version" in w.get("message", "").lower() and "semver" in w.get("message", "").lower()
        for w in warnings
    )
    
    if has_version_warning:
        results.success("invalid_version_format")
    else:
        results.fail("invalid_version_format", 
                    f"Should warn about version format. Warnings: {[w.get('message') for w in warnings]}")


def test_broken_plugin_invalid_tools(results: TestResult):
    """Detect invalid tools in agent frontmatter."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("invalid_agent_tools", "JSON parse error")
        return
    
    data = result.get("data", {})
    warnings = data.get("warnings", [])
    
    has_tools_warning = any(
        "invalid tools" in w.get("message", "").lower() and 
        ("FakeRead" in w.get("message", "") or "NotATool" in w.get("message", ""))
        for w in warnings
    )
    
    if has_tools_warning:
        results.success("invalid_agent_tools")
    else:
        results.fail("invalid_agent_tools", 
                    f"Should warn about FakeRead/NotATool. Warnings: {[w.get('message') for w in warnings]}")


def test_broken_plugin_invalid_model(results: TestResult):
    """Detect invalid model (gpt-4) in agent frontmatter."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("invalid_agent_model", "JSON parse error")
        return
    
    data = result.get("data", {})
    warnings = data.get("warnings", [])
    
    has_model_warning = any(
        "invalid model" in w.get("message", "").lower() and "gpt-4" in w.get("message", "")
        for w in warnings
    )
    
    if has_model_warning:
        results.success("invalid_agent_model")
    else:
        results.fail("invalid_agent_model", 
                    f"Should warn about gpt-4 model. Warnings: {[w.get('message') for w in warnings]}")


def test_broken_plugin_empty_triggers(results: TestResult):
    """Detect empty triggers array in skill."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("empty_skill_triggers", "JSON parse error")
        return
    
    data = result.get("data", {})
    warnings = data.get("warnings", [])
    
    has_triggers_warning = any(
        "triggers" in w.get("message", "").lower() and "empty" in w.get("message", "").lower()
        for w in warnings
    )
    
    if has_triggers_warning:
        results.success("empty_skill_triggers")
    else:
        results.fail("empty_skill_triggers", 
                    f"Should warn about empty triggers. Warnings: {[w.get('message') for w in warnings]}")


def test_broken_plugin_missing_skill_description(results: TestResult):
    """Detect missing description in skill."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("missing_skill_description", "JSON parse error")
        return
    
    data = result.get("data", {})
    errors = data.get("errors", [])
    
    has_desc_error = any(
        "description" in e.get("message", "").lower() and "skill" in e.get("component", "")
        for e in errors
    )
    
    if has_desc_error:
        results.success("missing_skill_description")
    else:
        results.fail("missing_skill_description", 
                    f"Should detect missing skill description. Errors: {[e.get('message') for e in errors]}")


def test_broken_plugin_missing_command_description(results: TestResult):
    """Detect missing description in command."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("missing_command_description", "JSON parse error")
        return
    
    data = result.get("data", {})
    errors = data.get("errors", [])
    
    has_desc_error = any(
        "description" in e.get("message", "").lower() and "command" in e.get("component", "")
        for e in errors
    )
    
    if has_desc_error:
        results.success("missing_command_description")
    else:
        results.fail("missing_command_description", 
                    f"Should detect missing command description. Errors: {[e.get('message') for e in errors]}")


def test_broken_plugin_invalid_hook_event(results: TestResult):
    """Detect invalid hook event."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("invalid_hook_event", "JSON parse error")
        return
    
    data = result.get("data", {})
    warnings = data.get("warnings", [])
    
    has_event_warning = any(
        "invalid" in w.get("message", "").lower() and 
        "event" in w.get("message", "").lower() and
        "InvalidEvent" in w.get("message", "")
        for w in warnings
    )
    
    if has_event_warning:
        results.success("invalid_hook_event")
    else:
        results.fail("invalid_hook_event", 
                    f"Should warn about InvalidEvent. Warnings: {[w.get('message') for w in warnings]}")


# =============================================================================
# TEST: Auto-Fix Capabilities
# =============================================================================

def test_autofix_plugin_name(results: TestResult):
    """Auto-fix missing plugin name from directory."""
    temp_dir = copy_fixture("fixable-plugin", "temp-fixable-plugin")
    
    try:
        # Verify name is missing
        plugin_json = temp_dir / "plugin.json"
        with open(plugin_json) as f:
            data = json.load(f)
        
        if "name" in data:
            results.fail("autofix_plugin_name", "Fixture already has name")
            return
        
        # Run validator with --fix
        result = run_validator(temp_dir, fix=True)
        
        if result.get("parse_error"):
            results.fail("autofix_plugin_name", "JSON parse error")
            return
        
        # Check if name was added
        with open(plugin_json) as f:
            data = json.load(f)
        
        if data.get("name") == "temp-fixable-plugin":
            results.success("autofix_plugin_name", f"Name set to '{data.get('name')}'")
        else:
            results.fail("autofix_plugin_name", f"Name not inferred correctly: {data.get('name')}")
    finally:
        cleanup_fixture("temp-fixable-plugin")


def test_autofix_plugin_version(results: TestResult):
    """Auto-fix missing plugin version to 1.0.0."""
    temp_dir = copy_fixture("fixable-plugin", "temp-fixable-version")
    
    try:
        # Verify version is missing
        plugin_json = temp_dir / "plugin.json"
        with open(plugin_json) as f:
            data = json.load(f)
        
        if "version" in data:
            results.fail("autofix_plugin_version", "Fixture already has version")
            return
        
        # Run validator with --fix
        result = run_validator(temp_dir, fix=True)
        
        # Check if version was added
        with open(plugin_json) as f:
            data = json.load(f)
        
        if data.get("version") == "1.0.0":
            results.success("autofix_plugin_version")
        else:
            results.fail("autofix_plugin_version", f"Version not set correctly: {data.get('version')}")
    finally:
        cleanup_fixture("temp-fixable-version")


def test_autofix_agent_name(results: TestResult):
    """Auto-fix missing agent name from filename."""
    temp_dir = copy_fixture("fixable-plugin", "temp-fixable-agent")
    
    try:
        agent_file = temp_dir / "agents" / "unnamed-agent.md"
        
        # Run validator with --fix
        result = run_validator(temp_dir, fix=True)
        
        # Check agent frontmatter
        import yaml
        content = agent_file.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1])
            if fm.get("name") == "unnamed-agent":
                results.success("autofix_agent_name", f"Name set to '{fm.get('name')}'")
            else:
                results.fail("autofix_agent_name", f"Name not inferred: {fm.get('name')}")
        else:
            results.fail("autofix_agent_name", "Could not parse frontmatter")
    finally:
        cleanup_fixture("temp-fixable-agent")


def test_autofix_skill_name(results: TestResult):
    """Auto-fix missing skill name from directory."""
    temp_dir = copy_fixture("fixable-plugin", "temp-fixable-skill")
    
    try:
        skill_file = temp_dir / "skills" / "fixable-skill" / "SKILL.md"
        
        # Run validator with --fix
        result = run_validator(temp_dir, fix=True)
        
        # Check skill frontmatter
        import yaml
        content = skill_file.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1])
            if fm.get("name") == "fixable-skill":
                results.success("autofix_skill_name", f"Name set to '{fm.get('name')}'")
            else:
                results.fail("autofix_skill_name", f"Name not inferred: {fm.get('name')}")
        else:
            results.fail("autofix_skill_name", "Could not parse frontmatter")
    finally:
        cleanup_fixture("temp-fixable-skill")


def test_autofix_skill_triggers(results: TestResult):
    """Auto-fix missing triggers array."""
    temp_dir = copy_fixture("fixable-plugin", "temp-fixable-triggers")
    
    try:
        skill_file = temp_dir / "skills" / "fixable-skill" / "SKILL.md"
        
        # Verify triggers is missing
        import yaml
        content = skill_file.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1])
            if "triggers" in fm:
                results.fail("autofix_skill_triggers", "Fixture already has triggers")
                return
        
        # Run validator with --fix
        result = run_validator(temp_dir, fix=True)
        
        # Check if triggers was added
        content = skill_file.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1])
            if "triggers" in fm and isinstance(fm["triggers"], list):
                results.success("autofix_skill_triggers")
            else:
                results.fail("autofix_skill_triggers", f"Triggers not added: {fm}")
        else:
            results.fail("autofix_skill_triggers", "Could not parse frontmatter")
    finally:
        cleanup_fixture("temp-fixable-triggers")


def test_autofix_reports_fixes(results: TestResult):
    """Validator reports what was auto-fixed."""
    temp_dir = copy_fixture("fixable-plugin", "temp-fixable-report")
    
    try:
        result = run_validator(temp_dir, fix=True)
        
        if result.get("parse_error"):
            results.fail("autofix_reports_fixes", "JSON parse error")
            return
        
        data = result.get("data", {})
        fixes = data.get("fixes_applied", [])
        
        if len(fixes) > 0:
            fix_descriptions = [f.get("description") for f in fixes]
            results.success("autofix_reports_fixes", f"Reported {len(fixes)} fixes")
        else:
            results.fail("autofix_reports_fixes", "No fixes reported")
    finally:
        cleanup_fixture("temp-fixable-report")


# =============================================================================
# TEST: Guidance Quality
# =============================================================================

def test_guidance_provides_fix_suggestion(results: TestResult):
    """Errors include fix guidance."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("guidance_has_fix_suggestion", "JSON parse error")
        return
    
    data = result.get("data", {})
    errors = data.get("errors", [])
    
    # Check that at least some errors have fix_guidance
    with_guidance = [e for e in errors if e.get("fix_guidance")]
    
    if len(with_guidance) > 0:
        results.success("guidance_has_fix_suggestion", f"{len(with_guidance)}/{len(errors)} have guidance")
    else:
        results.fail("guidance_has_fix_suggestion", "No errors have fix_guidance")


def test_guidance_identifies_fixable(results: TestResult):
    """Fixable issues are marked as can_fix=True."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("guidance_marks_fixable", "JSON parse error")
        return
    
    data = result.get("data", {})
    all_issues = data.get("errors", []) + data.get("warnings", [])
    
    # Check that some issues are marked fixable
    fixable = [i for i in all_issues if i.get("can_fix")]
    
    if len(fixable) > 0:
        results.success("guidance_marks_fixable", f"{len(fixable)} marked as fixable")
    else:
        results.fail("guidance_marks_fixable", "No issues marked as fixable")


# =============================================================================
# TEST: Summary Statistics
# =============================================================================

def test_summary_counts(results: TestResult):
    """Validator provides accurate summary counts."""
    plugin_dir = FIXTURES_DIR / "broken-plugin"
    result = run_validator(plugin_dir)
    
    if result.get("parse_error"):
        results.fail("summary_counts", "JSON parse error")
        return
    
    data = result.get("data", {})
    summary = data.get("summary", {})
    
    expected_keys = ["error_count", "warning_count", "fix_count", "fixable_count"]
    missing_keys = [k for k in expected_keys if k not in summary]
    
    if missing_keys:
        results.fail("summary_counts", f"Missing summary keys: {missing_keys}")
        return
    
    # Verify counts match actual lists
    actual_errors = len(data.get("errors", []))
    actual_warnings = len(data.get("warnings", []))
    
    if summary["error_count"] == actual_errors and summary["warning_count"] == actual_warnings:
        results.success("summary_counts", f"Errors: {actual_errors}, Warnings: {actual_warnings}")
    else:
        results.fail("summary_counts", 
                    f"Mismatch: summary says {summary['error_count']}e/{summary['warning_count']}w, "
                    f"actual is {actual_errors}e/{actual_warnings}w")


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Run all schema validation E2E tests."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    print("=" * 60)
    print("Forge Schema Validation E2E Tests")
    print("=" * 60)
    print(f"Forge root: {FORGE_ROOT}")
    print(f"Fixtures: {FIXTURES_DIR}")
    print(f"Validator: {VALIDATOR_SCRIPT}")
    print("=" * 60 + "\n")
    
    # Check prerequisites
    if not VALIDATOR_SCRIPT.exists():
        print(f"ERROR: Validator script not found: {VALIDATOR_SCRIPT}")
        return 1
    
    if not FIXTURES_DIR.exists():
        print(f"ERROR: Fixtures directory not found: {FIXTURES_DIR}")
        return 1
    
    results = TestResult(verbose=verbose)
    
    # Valid plugin tests
    print("Valid Plugin Tests:")
    test_valid_plugin_passes(results)
    
    # Broken plugin detection tests
    print("\nBroken Plugin Detection Tests:")
    test_broken_plugin_detected(results)
    test_broken_plugin_missing_description(results)
    test_broken_plugin_invalid_version(results)
    test_broken_plugin_invalid_tools(results)
    test_broken_plugin_invalid_model(results)
    test_broken_plugin_empty_triggers(results)
    test_broken_plugin_missing_skill_description(results)
    test_broken_plugin_missing_command_description(results)
    test_broken_plugin_invalid_hook_event(results)
    
    # Auto-fix tests
    print("\nAuto-Fix Tests:")
    test_autofix_plugin_name(results)
    test_autofix_plugin_version(results)
    test_autofix_agent_name(results)
    test_autofix_skill_name(results)
    test_autofix_skill_triggers(results)
    test_autofix_reports_fixes(results)
    
    # Guidance quality tests
    print("\nGuidance Quality Tests:")
    test_guidance_provides_fix_suggestion(results)
    test_guidance_identifies_fixable(results)
    
    # Summary tests
    print("\nSummary Tests:")
    test_summary_counts(results)
    
    return results.summary()


if __name__ == "__main__":
    sys.exit(run_all_tests())
