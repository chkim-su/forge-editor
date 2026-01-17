#!/usr/bin/env python3
"""
Forge Plugin Validation Script

Validates plugin structure, schemas, and references.
Can be run standalone or as part of E2E tests.
"""

import json
import os
import sys
import yaml
from pathlib import Path
from typing import Optional


FORGE_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))

# Valid tool names for agents
VALID_TOOLS = {
    "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Task",
    "AskUserQuestion", "WebFetch", "WebSearch", "TodoWrite",
    "NotebookEdit", "KillShell", "TaskOutput", "EnterPlanMode",
    "ExitPlanMode", "Skill", "ListMcpResourcesTool", "ReadMcpResourceTool"
}

# Valid hook events
VALID_EVENTS = {
    "PreToolUse", "PostToolUse", "Stop", "SubagentStop",
    "SessionStart", "SessionEnd", "UserPromptSubmit",
    "PreCompact", "Notification", "PermissionRequest"
}


class ValidationResult:
    """Collect validation errors and warnings."""
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def error(self, msg: str):
        self.errors.append(msg)
        print(f"  ✗ ERROR: {msg}")
    
    def warn(self, msg: str):
        self.warnings.append(msg)
        print(f"  ⚠ WARN: {msg}")
    
    def ok(self, msg: str):
        print(f"  ✓ {msg}")
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def parse_frontmatter(file_path: Path) -> Optional[dict]:
    """Parse YAML frontmatter from markdown file."""
    try:
        content = file_path.read_text()
        if not content.startswith("---"):
            return None
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        
        return yaml.safe_load(parts[1])
    except Exception as e:
        return None


def validate_plugin_json(results: ValidationResult) -> Optional[dict]:
    """Validate plugin.json manifest."""
    plugin_json = FORGE_ROOT / "plugin.json"
    
    if not plugin_json.exists():
        results.error("Missing plugin.json")
        return None
    
    try:
        with open(plugin_json) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        results.error(f"Invalid JSON in plugin.json: {e}")
        return None
    
    # Required fields
    for field in ["name", "version", "description"]:
        if field not in manifest:
            results.error(f"Missing required field in plugin.json: {field}")
        else:
            results.ok(f"plugin.json has '{field}'")
    
    return manifest


def validate_component_paths(manifest: dict, results: ValidationResult):
    """Validate that all component paths exist."""
    for comp_type in ["skills", "agents", "commands"]:
        components = manifest.get(comp_type, [])
        for comp in components:
            path = FORGE_ROOT / comp.get("path", "")
            if not path.exists():
                results.error(f"{comp_type} path not found: {comp['path']}")
            else:
                results.ok(f"{comp_type} path exists: {comp['path']}")


def validate_hooks_json(manifest: dict, results: ValidationResult):
    """Validate hooks.json if specified."""
    hooks_path_str = manifest.get("hooks")
    if not hooks_path_str:
        results.ok("No hooks specified (optional)")
        return
    
    hooks_path = FORGE_ROOT / hooks_path_str
    if not hooks_path.exists():
        results.error(f"Hooks file not found: {hooks_path_str}")
        return
    
    try:
        with open(hooks_path) as f:
            hooks_config = json.load(f)
    except json.JSONDecodeError as e:
        results.error(f"Invalid JSON in hooks.json: {e}")
        return
    
    results.ok(f"hooks.json is valid JSON")
    
    # Validate hook events
    for hook in hooks_config.get("hooks", []):
        event = hook.get("event")
        if event and event not in VALID_EVENTS:
            results.warn(f"Unknown hook event: {event}")
        else:
            results.ok(f"Hook event '{event}' is valid")


def validate_agent_frontmatter(manifest: dict, results: ValidationResult):
    """Validate agent frontmatter."""
    for agent in manifest.get("agents", []):
        path = FORGE_ROOT / agent.get("path", "")
        if not path.exists():
            continue  # Already reported in path validation
        
        fm = parse_frontmatter(path)
        if not fm:
            results.error(f"Agent missing frontmatter: {path.name}")
            continue
        
        # Check required fields
        if "name" not in fm:
            results.error(f"Agent '{path.name}' missing 'name' in frontmatter")
        
        if "description" not in fm:
            results.error(f"Agent '{path.name}' missing 'description' in frontmatter")
        
        # Validate tools if specified
        if "tools" in fm:
            for tool in fm["tools"]:
                if tool not in VALID_TOOLS:
                    results.warn(f"Agent '{path.name}' has unknown tool: {tool}")
        
        results.ok(f"Agent '{path.name}' frontmatter valid")


def validate_skill_frontmatter(manifest: dict, results: ValidationResult):
    """Validate skill frontmatter."""
    for skill in manifest.get("skills", []):
        path = FORGE_ROOT / skill.get("path", "")
        if not path.exists():
            continue
        
        fm = parse_frontmatter(path)
        if not fm:
            results.error(f"Skill missing frontmatter: {path.name}")
            continue
        
        # Check required fields
        if "name" not in fm:
            results.error(f"Skill '{path.name}' missing 'name' in frontmatter")
        
        if "description" not in fm:
            results.error(f"Skill '{path.name}' missing 'description' in frontmatter")
        
        if "triggers" not in fm or len(fm.get("triggers", [])) < 1:
            results.warn(f"Skill '{path.name}' should have triggers for matching")
        
        results.ok(f"Skill '{path.name}' frontmatter valid")


def validate_command_frontmatter(manifest: dict, results: ValidationResult):
    """Validate command frontmatter."""
    for cmd in manifest.get("commands", []):
        path = FORGE_ROOT / cmd.get("path", "")
        if not path.exists():
            continue
        
        fm = parse_frontmatter(path)
        if not fm:
            results.error(f"Command missing frontmatter: {path.name}")
            continue
        
        if "name" not in fm:
            results.error(f"Command '{path.name}' missing 'name' in frontmatter")
        
        if "description" not in fm:
            results.error(f"Command '{path.name}' missing 'description' in frontmatter")
        
        results.ok(f"Command '{path.name}' frontmatter valid")


def validate_python_syntax(results: ValidationResult):
    """Check Python files for syntax errors."""
    python_files = list(FORGE_ROOT.rglob("*.py"))
    
    for py_file in python_files:
        if "__pycache__" in str(py_file):
            continue
        
        try:
            with open(py_file) as f:
                compile(f.read(), py_file, "exec")
            results.ok(f"Python syntax OK: {py_file.relative_to(FORGE_ROOT)}")
        except SyntaxError as e:
            results.error(f"Python syntax error in {py_file.name}: {e}")


def main():
    """Run all validations."""
    print("="*50)
    print("Forge Plugin Validation")
    print("="*50)
    print(f"Plugin root: {FORGE_ROOT}\n")
    
    results = ValidationResult()
    
    print("Plugin Manifest:")
    manifest = validate_plugin_json(results)
    
    if manifest:
        print("\nComponent Paths:")
        validate_component_paths(manifest, results)
        
        print("\nHooks Configuration:")
        validate_hooks_json(manifest, results)
        
        print("\nAgent Frontmatter:")
        validate_agent_frontmatter(manifest, results)
        
        print("\nSkill Frontmatter:")
        validate_skill_frontmatter(manifest, results)
        
        print("\nCommand Frontmatter:")
        validate_command_frontmatter(manifest, results)
    
    print("\nPython Syntax:")
    validate_python_syntax(results)
    
    print("\n" + "="*50)
    if results.is_valid:
        print("✓ Plugin is valid!")
        print(f"  Warnings: {len(results.warnings)}")
        return 0
    else:
        print("✗ Plugin validation failed!")
        print(f"  Errors: {len(results.errors)}")
        print(f"  Warnings: {len(results.warnings)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
