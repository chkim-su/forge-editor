#!/usr/bin/env python3
"""
Forge Schema Validator

Comprehensive schema validation with auto-fix capabilities for Forge plugins.
Validates plugin.json, agent/skill/command frontmatter, hooks.json, and marketplace.json.

Usage:
    python3 schema-validator.py [plugin_dir] [--fix] [--json]

Arguments:
    plugin_dir   Path to plugin directory (default: current directory)
    --fix        Attempt to auto-fix safe issues
    --json       Output results as JSON
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml


# =============================================================================
# CONSTANTS
# =============================================================================

VALID_MODELS = {"sonnet", "opus", "haiku"}

VALID_TOOLS = {
    "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Task",
    "AskUserQuestion", "WebFetch", "WebSearch", "TodoWrite",
    "NotebookEdit", "KillShell", "TaskOutput", "EnterPlanMode",
    "ExitPlanMode", "Skill", "ListMcpResourcesTool", "ReadMcpResourceTool"
}

VALID_EVENTS = {
    "PreToolUse", "PostToolUse", "Stop", "SubagentStop",
    "SessionStart", "SessionEnd", "UserPromptSubmit",
    "PreCompact", "Notification", "PermissionRequest"
}

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$")


# =============================================================================
# DATA CLASSES
# =============================================================================

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    """Represents a validation issue."""
    severity: Severity
    component: str
    file_path: str
    message: str
    can_fix: bool = False
    fix_description: str = ""
    fix_guidance: str = ""
    was_fixed: bool = False


@dataclass
class ValidationResult:
    """Holds all validation results."""
    issues: list = field(default_factory=list)
    fixes_applied: list = field(default_factory=list)
    
    def add_issue(self, severity: Severity, component: str, file_path: str, 
                  message: str, can_fix: bool = False, fix_description: str = "",
                  fix_guidance: str = ""):
        self.issues.append(Issue(
            severity=severity,
            component=component,
            file_path=file_path,
            message=message,
            can_fix=can_fix,
            fix_description=fix_description,
            fix_guidance=fix_guidance
        ))
    
    def error(self, component: str, file_path: str, message: str, 
              can_fix: bool = False, fix_description: str = "", fix_guidance: str = ""):
        self.add_issue(Severity.ERROR, component, file_path, message, 
                      can_fix, fix_description, fix_guidance)
    
    def warning(self, component: str, file_path: str, message: str,
                can_fix: bool = False, fix_description: str = "", fix_guidance: str = ""):
        self.add_issue(Severity.WARNING, component, file_path, message,
                      can_fix, fix_description, fix_guidance)
    
    def info(self, component: str, file_path: str, message: str):
        self.add_issue(Severity.INFO, component, file_path, message)
    
    def record_fix(self, component: str, file_path: str, description: str):
        self.fixes_applied.append({
            "component": component,
            "file_path": file_path,
            "description": description
        })
    
    @property
    def errors(self):
        return [i for i in self.issues if i.severity == Severity.ERROR and not i.was_fixed]
    
    @property
    def warnings(self):
        return [i for i in self.issues if i.severity == Severity.WARNING and not i.was_fixed]
    
    @property
    def infos(self):
        return [i for i in self.issues if i.severity == Severity.INFO]
    
    @property
    def fixable(self):
        return [i for i in self.issues if i.can_fix and not i.was_fixed]
    
    @property
    def is_valid(self):
        return len(self.errors) == 0


# =============================================================================
# FRONTMATTER PARSING
# =============================================================================

def parse_frontmatter(file_path: Path) -> tuple[Optional[dict], Optional[str]]:
    """
    Parse YAML frontmatter from a markdown file.
    Returns (frontmatter_dict, error_message).
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return None, f"Cannot read file: {e}"
    
    if not content.startswith("---"):
        return None, "No frontmatter found (file doesn't start with ---)"
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, "Invalid frontmatter format (missing closing ---)"
    
    try:
        frontmatter = yaml.safe_load(parts[1])
        if frontmatter is None:
            return {}, None  # Empty frontmatter is valid YAML
        return frontmatter, None
    except yaml.YAMLError as e:
        # Extract line/column info from YAML error
        error_msg = str(e)
        return None, f"Invalid YAML: {error_msg}"


def write_frontmatter(file_path: Path, frontmatter: dict, body: str = "") -> bool:
    """Write frontmatter to a markdown file."""
    try:
        content = "---\n" + yaml.dump(frontmatter, default_flow_style=False) + "---\n" + body
        file_path.write_text(content, encoding='utf-8')
        return True
    except Exception:
        return False


def get_markdown_body(file_path: Path) -> str:
    """Get the markdown body (everything after frontmatter)."""
    try:
        content = file_path.read_text(encoding='utf-8')
        if not content.startswith("---"):
            return content
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
        return ""
    except Exception:
        return ""


# =============================================================================
# AUTO-FIX FUNCTIONS
# =============================================================================

def fix_plugin_name(plugin_dir: Path, result: ValidationResult) -> bool:
    """Fix missing/empty plugin name by inferring from directory."""
    plugin_json = plugin_dir / "plugin.json"
    try:
        with open(plugin_json, 'r') as f:
            data = json.load(f)
        
        inferred_name = plugin_dir.name
        data["name"] = inferred_name
        
        with open(plugin_json, 'w') as f:
            json.dump(data, f, indent=2)
        
        result.record_fix("plugin.json", str(plugin_json), 
                         f"Added name '{inferred_name}' (inferred from directory)")
        return True
    except Exception:
        return False


def fix_plugin_version(plugin_dir: Path, result: ValidationResult) -> bool:
    """Fix missing version by defaulting to 1.0.0."""
    plugin_json = plugin_dir / "plugin.json"
    try:
        with open(plugin_json, 'r') as f:
            data = json.load(f)
        
        data["version"] = "1.0.0"
        
        with open(plugin_json, 'w') as f:
            json.dump(data, f, indent=2)
        
        result.record_fix("plugin.json", str(plugin_json), 
                         "Added version '1.0.0' (default)")
        return True
    except Exception:
        return False


def fix_semver_format(plugin_dir: Path, current_version: str, result: ValidationResult) -> bool:
    """Normalize version to semver X.Y.Z format."""
    plugin_json = plugin_dir / "plugin.json"
    try:
        with open(plugin_json, 'r') as f:
            data = json.load(f)
        
        # Try to normalize: "1.0" -> "1.0.0", "1" -> "1.0.0"
        parts = current_version.split(".")
        while len(parts) < 3:
            parts.append("0")
        normalized = ".".join(parts[:3])
        
        data["version"] = normalized
        
        with open(plugin_json, 'w') as f:
            json.dump(data, f, indent=2)
        
        result.record_fix("plugin.json", str(plugin_json), 
                         f"Normalized version '{current_version}' → '{normalized}'")
        return True
    except Exception:
        return False


def fix_agent_name(agent_path: Path, result: ValidationResult) -> bool:
    """Fix missing agent name by inferring from filename."""
    fm, _ = parse_frontmatter(agent_path)
    if fm is None:
        fm = {}
    
    inferred_name = agent_path.stem  # filename without extension
    fm["name"] = inferred_name
    
    body = get_markdown_body(agent_path)
    if write_frontmatter(agent_path, fm, body):
        result.record_fix("agent", str(agent_path), 
                         f"Added name '{inferred_name}' (inferred from filename)")
        return True
    return False


def fix_agent_model(agent_path: Path, current_model: str, result: ValidationResult) -> bool:
    """Fix invalid model by defaulting to sonnet."""
    fm, _ = parse_frontmatter(agent_path)
    if fm is None:
        return False
    
    fm["model"] = "sonnet"
    
    body = get_markdown_body(agent_path)
    if write_frontmatter(agent_path, fm, body):
        result.record_fix("agent", str(agent_path), 
                         f"Changed model '{current_model}' → 'sonnet' (default)")
        return True
    return False


def fix_agent_tools(agent_path: Path, invalid_tools: list, result: ValidationResult) -> bool:
    """Remove invalid tools from agent."""
    fm, _ = parse_frontmatter(agent_path)
    if fm is None or "tools" not in fm:
        return False
    
    original_tools = fm["tools"]
    valid_only = [t for t in original_tools if t in VALID_TOOLS]
    fm["tools"] = valid_only
    
    body = get_markdown_body(agent_path)
    if write_frontmatter(agent_path, fm, body):
        result.record_fix("agent", str(agent_path), 
                         f"Removed invalid tools: {invalid_tools}")
        return True
    return False


def fix_agent_name_mismatch(agent_path: Path, current_name: str, result: ValidationResult) -> bool:
    """Fix agent name to match filename."""
    fm, _ = parse_frontmatter(agent_path)
    if fm is None:
        return False
    
    expected_name = agent_path.stem
    fm["name"] = expected_name
    
    body = get_markdown_body(agent_path)
    if write_frontmatter(agent_path, fm, body):
        result.record_fix("agent", str(agent_path), 
                         f"Renamed '{current_name}' → '{expected_name}' (match filename)")
        return True
    return False


def fix_missing_agent_frontmatter(agent_path: Path, result: ValidationResult) -> bool:
    """Generate minimal frontmatter for agent."""
    try:
        content = agent_path.read_text(encoding='utf-8')
    except:
        return False
    
    name = agent_path.stem
    fm = {
        "name": name,
        "description": f"TODO: Add description for {name}",
        "model": "sonnet",
        "tools": ["Read", "Glob", "Grep"]
    }
    
    body = content if not content.startswith("---") else get_markdown_body(agent_path)
    
    if write_frontmatter(agent_path, fm, body):
        result.record_fix("agent", str(agent_path), 
                         "Generated minimal frontmatter (needs description)")
        return True
    return False


def fix_skill_name(skill_path: Path, result: ValidationResult) -> bool:
    """Fix missing skill name by inferring from directory."""
    fm, _ = parse_frontmatter(skill_path)
    if fm is None:
        fm = {}
    
    # Skill name from parent directory
    inferred_name = skill_path.parent.name
    fm["name"] = inferred_name
    
    body = get_markdown_body(skill_path)
    if write_frontmatter(skill_path, fm, body):
        result.record_fix("skill", str(skill_path), 
                         f"Added name '{inferred_name}' (inferred from directory)")
        return True
    return False


def fix_skill_triggers(skill_path: Path, result: ValidationResult) -> bool:
    """Add empty triggers array with warning."""
    fm, _ = parse_frontmatter(skill_path)
    if fm is None:
        return False
    
    fm["triggers"] = []
    
    body = get_markdown_body(skill_path)
    if write_frontmatter(skill_path, fm, body):
        result.record_fix("skill", str(skill_path), 
                         "Added empty triggers array (should add trigger phrases)")
        return True
    return False


def fix_missing_skill_frontmatter(skill_path: Path, result: ValidationResult) -> bool:
    """Generate minimal frontmatter for skill."""
    try:
        content = skill_path.read_text(encoding='utf-8')
    except:
        return False
    
    name = skill_path.parent.name
    fm = {
        "name": name,
        "description": f"TODO: Add description for {name}",
        "triggers": []
    }
    
    body = content if not content.startswith("---") else get_markdown_body(skill_path)
    
    if write_frontmatter(skill_path, fm, body):
        result.record_fix("skill", str(skill_path), 
                         "Generated minimal frontmatter (needs description and triggers)")
        return True
    return False


def fix_command_name(cmd_path: Path, result: ValidationResult) -> bool:
    """Fix missing command name by inferring from filename."""
    fm, _ = parse_frontmatter(cmd_path)
    if fm is None:
        fm = {}
    
    inferred_name = cmd_path.stem
    fm["name"] = inferred_name
    
    body = get_markdown_body(cmd_path)
    if write_frontmatter(cmd_path, fm, body):
        result.record_fix("command", str(cmd_path), 
                         f"Added name '{inferred_name}' (inferred from filename)")
        return True
    return False


def fix_missing_command_frontmatter(cmd_path: Path, result: ValidationResult) -> bool:
    """Generate minimal frontmatter for command."""
    try:
        content = cmd_path.read_text(encoding='utf-8')
    except:
        return False
    
    name = cmd_path.stem
    fm = {
        "name": name,
        "description": f"TODO: Add description for /{name}"
    }
    
    body = content if not content.startswith("---") else get_markdown_body(cmd_path)
    
    if write_frontmatter(cmd_path, fm, body):
        result.record_fix("command", str(cmd_path), 
                         "Generated minimal frontmatter (needs description)")
        return True
    return False


def fix_hooks_missing_array(hooks_path: Path, result: ValidationResult) -> bool:
    """Initialize empty hooks array."""
    try:
        with open(hooks_path, 'r') as f:
            data = json.load(f)
        
        data["hooks"] = []
        
        with open(hooks_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        result.record_fix("hooks.json", str(hooks_path), 
                         "Initialized empty hooks array")
        return True
    except Exception:
        return False


def fix_invalid_hook_events(hooks_path: Path, invalid_events: list, result: ValidationResult) -> bool:
    """Remove hooks with invalid events."""
    try:
        with open(hooks_path, 'r') as f:
            data = json.load(f)
        
        original_hooks = data.get("hooks", [])
        valid_hooks = [h for h in original_hooks if h.get("event") in VALID_EVENTS]
        data["hooks"] = valid_hooks
        
        with open(hooks_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        result.record_fix("hooks.json", str(hooks_path), 
                         f"Removed hooks with invalid events: {invalid_events}")
        return True
    except Exception:
        return False


def fix_marketplace_name(marketplace_path: Path, result: ValidationResult) -> bool:
    """Fix missing marketplace name from directory."""
    try:
        with open(marketplace_path, 'r') as f:
            data = json.load(f)
        
        inferred_name = marketplace_path.parent.name
        data["name"] = inferred_name
        
        with open(marketplace_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        result.record_fix("marketplace.json", str(marketplace_path), 
                         f"Added name '{inferred_name}' (inferred from directory)")
        return True
    except Exception:
        return False


def fix_marketplace_plugins_array(marketplace_path: Path, result: ValidationResult) -> bool:
    """Initialize empty plugins array."""
    try:
        with open(marketplace_path, 'r') as f:
            data = json.load(f)
        
        data["plugins"] = []
        
        with open(marketplace_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        result.record_fix("marketplace.json", str(marketplace_path), 
                         "Initialized empty plugins array")
        return True
    except Exception:
        return False


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_plugin_json(plugin_dir: Path, result: ValidationResult, do_fix: bool) -> Optional[dict]:
    """Validate plugin.json and return manifest if valid."""
    plugin_json = plugin_dir / "plugin.json"
    
    if not plugin_json.exists():
        result.error("plugin.json", str(plugin_json), 
                    "Missing plugin.json manifest file",
                    fix_guidance="Create plugin.json with: {\"name\": \"...\", \"version\": \"1.0.0\", \"description\": \"...\"}")
        return None
    
    # Parse JSON
    try:
        with open(plugin_json, 'r') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        result.error("plugin.json", str(plugin_json),
                    f"Invalid JSON syntax at line {e.lineno}, column {e.colno}: {e.msg}",
                    fix_guidance="Fix the JSON syntax error manually")
        return None
    
    # Check required fields: name
    if "name" not in manifest or not manifest.get("name"):
        if do_fix and fix_plugin_name(plugin_dir, result):
            # Mark as fixed, reload manifest
            with open(plugin_json, 'r') as f:
                manifest = json.load(f)
        else:
            result.error("plugin.json", str(plugin_json),
                        "Missing required field 'name'",
                        can_fix=True,
                        fix_description=f"Infer from directory: '{plugin_dir.name}'",
                        fix_guidance=f"Add: \"name\": \"{plugin_dir.name}\"")
    
    # Check required fields: version
    if "version" not in manifest:
        if do_fix and fix_plugin_version(plugin_dir, result):
            with open(plugin_json, 'r') as f:
                manifest = json.load(f)
        else:
            result.error("plugin.json", str(plugin_json),
                        "Missing required field 'version'",
                        can_fix=True,
                        fix_description="Default to '1.0.0'",
                        fix_guidance="Add: \"version\": \"1.0.0\"")
    else:
        # Validate semver format
        version = manifest.get("version", "")
        if not SEMVER_PATTERN.match(version):
            if do_fix and fix_semver_format(plugin_dir, version, result):
                with open(plugin_json, 'r') as f:
                    manifest = json.load(f)
            else:
                result.warning("plugin.json", str(plugin_json),
                             f"Version '{version}' is not valid semver format",
                             can_fix=True,
                             fix_description="Normalize to X.Y.Z format",
                             fix_guidance="Use format: \"1.0.0\"")
    
    # Check required fields: description
    if "description" not in manifest or not manifest.get("description"):
        result.error("plugin.json", str(plugin_json),
                    "Missing required field 'description'",
                    fix_guidance="Add: \"description\": \"Your plugin description here\"")
    
    return manifest


def validate_component_paths(plugin_dir: Path, manifest: dict, result: ValidationResult):
    """Validate that all component paths exist."""
    missing_paths = []
    
    for comp_type in ["skills", "agents", "commands"]:
        components = manifest.get(comp_type, [])
        for comp in components:
            path_str = comp.get("path", "")
            if not path_str:
                continue
            
            path = plugin_dir / path_str
            if not path.exists():
                missing_paths.append(path_str)
                result.error(comp_type, str(path),
                           f"Referenced path does not exist: {path_str}",
                           fix_guidance=f"Create the file at {path_str} or remove the entry from plugin.json")
    
    return missing_paths


def validate_agents(plugin_dir: Path, manifest: dict, result: ValidationResult, do_fix: bool):
    """Validate agent frontmatter."""
    for agent in manifest.get("agents", []):
        path_str = agent.get("path", "")
        if not path_str:
            continue
        
        agent_path = plugin_dir / path_str
        if not agent_path.exists():
            continue  # Already reported in path validation
        
        fm, error = parse_frontmatter(agent_path)
        
        # Check for missing/invalid frontmatter
        if error:
            if "No frontmatter" in error or "Invalid frontmatter format" in error:
                if do_fix and fix_missing_agent_frontmatter(agent_path, result):
                    fm, _ = parse_frontmatter(agent_path)
                else:
                    result.error("agent", str(agent_path),
                               "Missing frontmatter",
                               can_fix=True,
                               fix_description="Generate minimal frontmatter",
                               fix_guidance="Add YAML frontmatter between --- markers")
                    continue
            else:
                result.error("agent", str(agent_path),
                           f"Invalid frontmatter: {error}",
                           fix_guidance="Fix the YAML syntax error")
                continue
        
        if fm is None:
            continue
        
        # Check required: name
        if "name" not in fm or not fm.get("name"):
            expected = agent_path.stem
            if do_fix and fix_agent_name(agent_path, result):
                fm["name"] = expected
            else:
                result.error("agent", str(agent_path),
                           "Missing 'name' in frontmatter",
                           can_fix=True,
                           fix_description=f"Infer from filename: '{expected}'",
                           fix_guidance=f"Add: name: {expected}")
        else:
            # Check name matches filename
            name = fm["name"]
            expected = agent_path.stem
            if name != expected:
                if do_fix and fix_agent_name_mismatch(agent_path, name, result):
                    fm["name"] = expected
                else:
                    result.warning("agent", str(agent_path),
                                 f"Name '{name}' doesn't match filename '{expected}'",
                                 can_fix=True,
                                 fix_description=f"Rename to '{expected}'",
                                 fix_guidance=f"Change name to: {expected}")
        
        # Check required: description
        if "description" not in fm or not fm.get("description"):
            result.error("agent", str(agent_path),
                        "Missing 'description' in frontmatter",
                        fix_guidance="Add: description: \"Your agent description\"")
        
        # Check model validity
        if "model" in fm:
            model = fm["model"]
            if model not in VALID_MODELS:
                if do_fix and fix_agent_model(agent_path, model, result):
                    pass
                else:
                    result.warning("agent", str(agent_path),
                                 f"Invalid model '{model}'",
                                 can_fix=True,
                                 fix_description="Default to 'sonnet'",
                                 fix_guidance=f"Valid models: {', '.join(sorted(VALID_MODELS))}")
        
        # Check tools validity
        if "tools" in fm:
            tools = fm["tools"]
            if isinstance(tools, list):
                invalid_tools = [t for t in tools if t not in VALID_TOOLS]
                if invalid_tools:
                    if do_fix and fix_agent_tools(agent_path, invalid_tools, result):
                        pass
                    else:
                        result.warning("agent", str(agent_path),
                                     f"Invalid tools: {invalid_tools}",
                                     can_fix=True,
                                     fix_description="Remove invalid tools",
                                     fix_guidance=f"Valid tools: {', '.join(sorted(VALID_TOOLS))}")


def validate_skills(plugin_dir: Path, manifest: dict, result: ValidationResult, do_fix: bool):
    """Validate skill frontmatter."""
    for skill in manifest.get("skills", []):
        path_str = skill.get("path", "")
        if not path_str:
            continue
        
        skill_path = plugin_dir / path_str
        if not skill_path.exists():
            continue
        
        fm, error = parse_frontmatter(skill_path)
        
        if error:
            if "No frontmatter" in error or "Invalid frontmatter format" in error:
                if do_fix and fix_missing_skill_frontmatter(skill_path, result):
                    fm, _ = parse_frontmatter(skill_path)
                else:
                    result.error("skill", str(skill_path),
                               "Missing frontmatter",
                               can_fix=True,
                               fix_description="Generate minimal frontmatter",
                               fix_guidance="Add YAML frontmatter between --- markers")
                    continue
            else:
                result.error("skill", str(skill_path),
                           f"Invalid frontmatter: {error}",
                           fix_guidance="Fix the YAML syntax error")
                continue
        
        if fm is None:
            continue
        
        # Check required: name
        if "name" not in fm or not fm.get("name"):
            expected = skill_path.parent.name
            if do_fix and fix_skill_name(skill_path, result):
                fm["name"] = expected
            else:
                result.error("skill", str(skill_path),
                           "Missing 'name' in frontmatter",
                           can_fix=True,
                           fix_description=f"Infer from directory: '{expected}'",
                           fix_guidance=f"Add: name: {expected}")
        
        # Check required: description
        if "description" not in fm or not fm.get("description"):
            result.error("skill", str(skill_path),
                        "Missing 'description' in frontmatter",
                        fix_guidance="Add: description: \"Your skill description\"")
        
        # Check triggers
        if "triggers" not in fm:
            if do_fix and fix_skill_triggers(skill_path, result):
                fm["triggers"] = []
            else:
                result.warning("skill", str(skill_path),
                             "Missing 'triggers' array",
                             can_fix=True,
                             fix_description="Add empty triggers array",
                             fix_guidance="Add: triggers: [\"trigger phrase 1\", \"trigger phrase 2\"]")
        elif not fm.get("triggers"):
            result.warning("skill", str(skill_path),
                         "Empty 'triggers' array",
                         fix_guidance="Add trigger phrases for discoverability")


def validate_commands(plugin_dir: Path, manifest: dict, result: ValidationResult, do_fix: bool):
    """Validate command frontmatter."""
    for cmd in manifest.get("commands", []):
        path_str = cmd.get("path", "")
        if not path_str:
            continue
        
        cmd_path = plugin_dir / path_str
        if not cmd_path.exists():
            continue
        
        fm, error = parse_frontmatter(cmd_path)
        
        if error:
            if "No frontmatter" in error or "Invalid frontmatter format" in error:
                if do_fix and fix_missing_command_frontmatter(cmd_path, result):
                    fm, _ = parse_frontmatter(cmd_path)
                else:
                    result.error("command", str(cmd_path),
                               "Missing frontmatter",
                               can_fix=True,
                               fix_description="Generate minimal frontmatter",
                               fix_guidance="Add YAML frontmatter between --- markers")
                    continue
            else:
                result.error("command", str(cmd_path),
                           f"Invalid frontmatter: {error}",
                           fix_guidance="Fix the YAML syntax error")
                continue
        
        if fm is None:
            continue
        
        # Check required: name
        if "name" not in fm or not fm.get("name"):
            expected = cmd_path.stem
            if do_fix and fix_command_name(cmd_path, result):
                fm["name"] = expected
            else:
                result.error("command", str(cmd_path),
                           "Missing 'name' in frontmatter",
                           can_fix=True,
                           fix_description=f"Infer from filename: '{expected}'",
                           fix_guidance=f"Add: name: {expected}")
        
        # Check required: description
        if "description" not in fm or not fm.get("description"):
            result.error("command", str(cmd_path),
                        "Missing 'description' in frontmatter",
                        fix_guidance="Add: description: \"Your command description\"")


def validate_hooks_json(plugin_dir: Path, manifest: dict, result: ValidationResult, do_fix: bool):
    """Validate hooks.json schema."""
    hooks_path_str = manifest.get("hooks")
    if not hooks_path_str:
        return  # Hooks are optional
    
    hooks_path = plugin_dir / hooks_path_str
    if not hooks_path.exists():
        result.error("hooks.json", str(hooks_path),
                    f"Hooks file not found: {hooks_path_str}",
                    fix_guidance="Create hooks.json or remove 'hooks' from plugin.json")
        return
    
    # Parse JSON
    try:
        with open(hooks_path, 'r') as f:
            hooks_config = json.load(f)
    except json.JSONDecodeError as e:
        result.error("hooks.json", str(hooks_path),
                    f"Invalid JSON syntax at line {e.lineno}: {e.msg}",
                    fix_guidance="Fix the JSON syntax error")
        return
    
    # Check hooks array exists
    if "hooks" not in hooks_config:
        if do_fix and fix_hooks_missing_array(hooks_path, result):
            hooks_config["hooks"] = []
        else:
            result.error("hooks.json", str(hooks_path),
                        "Missing 'hooks' array",
                        can_fix=True,
                        fix_description="Initialize empty array",
                        fix_guidance="Add: \"hooks\": []")
            return
    
    # Validate each hook
    invalid_events = []
    for hook in hooks_config.get("hooks", []):
        event = hook.get("event")
        if event and event not in VALID_EVENTS:
            invalid_events.append(event)
        
        # Check hook has nested hooks array with type and command
        nested_hooks = hook.get("hooks", [])
        for nested in nested_hooks:
            hook_type = nested.get("type")
            if hook_type not in ["command", "prompt"]:
                result.warning("hooks.json", str(hooks_path),
                             f"Invalid hook type: {hook_type}",
                             fix_guidance="Valid types: 'command' or 'prompt'")
            
            if hook_type == "command" and "command" not in nested:
                result.error("hooks.json", str(hooks_path),
                           "Command hook missing 'command' field",
                           fix_guidance="Add: \"command\": \"your-command-here\"")
    
    if invalid_events:
        if do_fix and fix_invalid_hook_events(hooks_path, invalid_events, result):
            pass
        else:
            result.warning("hooks.json", str(hooks_path),
                         f"Invalid hook events: {invalid_events}",
                         can_fix=True,
                         fix_description="Remove hooks with invalid events",
                         fix_guidance=f"Valid events: {', '.join(sorted(VALID_EVENTS))}")


def validate_marketplace_json(plugin_dir: Path, result: ValidationResult, do_fix: bool):
    """Validate marketplace.json if it exists."""
    marketplace_path = plugin_dir / "marketplace.json"
    if not marketplace_path.exists():
        return  # marketplace.json is optional
    
    # Parse JSON
    try:
        with open(marketplace_path, 'r') as f:
            marketplace = json.load(f)
    except json.JSONDecodeError as e:
        result.error("marketplace.json", str(marketplace_path),
                    f"Invalid JSON syntax at line {e.lineno}: {e.msg}",
                    fix_guidance="Fix the JSON syntax error")
        return
    
    # Check required: name
    if "name" not in marketplace or not marketplace.get("name"):
        if do_fix and fix_marketplace_name(marketplace_path, result):
            pass
        else:
            result.error("marketplace.json", str(marketplace_path),
                        "Missing required field 'name'",
                        can_fix=True,
                        fix_description=f"Infer from directory: '{plugin_dir.name}'",
                        fix_guidance=f"Add: \"name\": \"{plugin_dir.name}\"")
    
    # Check required: owner
    if "owner" not in marketplace or not marketplace.get("owner"):
        result.error("marketplace.json", str(marketplace_path),
                    "Missing required field 'owner'",
                    fix_guidance="Add: \"owner\": {\"name\": \"Your Name\", \"url\": \"...\"}")
    
    # Check plugins array
    if "plugins" not in marketplace:
        if do_fix and fix_marketplace_plugins_array(marketplace_path, result):
            marketplace["plugins"] = []
        else:
            result.error("marketplace.json", str(marketplace_path),
                        "Missing 'plugins' array",
                        can_fix=True,
                        fix_description="Initialize empty array",
                        fix_guidance="Add: \"plugins\": []")
    elif not marketplace.get("plugins"):
        result.warning("marketplace.json", str(marketplace_path),
                      "Empty 'plugins' array",
                      fix_guidance="Add plugins to the marketplace")
    else:
        # Check for duplicate plugin names
        names = [p.get("name") for p in marketplace.get("plugins", [])]
        duplicates = [n for n in names if names.count(n) > 1]
        if duplicates:
            result.error("marketplace.json", str(marketplace_path),
                        f"Duplicate plugin names: {list(set(duplicates))}",
                        fix_guidance="Rename duplicate plugins to be unique")
        
        # Check plugin source paths
        for plugin in marketplace.get("plugins", []):
            source = plugin.get("source", {})
            local_path = source.get("local")
            if local_path:
                full_path = plugin_dir / local_path
                if not full_path.exists():
                    result.error("marketplace.json", str(marketplace_path),
                               f"Plugin source not found: {local_path}",
                               fix_guidance=f"Create plugin at {local_path} or update the path")


def validate_python_syntax(plugin_dir: Path, result: ValidationResult):
    """Check Python files for syntax errors."""
    python_files = list(plugin_dir.rglob("*.py"))
    
    for py_file in python_files:
        if "__pycache__" in str(py_file):
            continue
        
        try:
            with open(py_file, 'r') as f:
                compile(f.read(), py_file, "exec")
        except SyntaxError as e:
            result.error("python", str(py_file),
                        f"Syntax error at line {e.lineno}: {e.msg}",
                        fix_guidance="Fix the Python syntax error")


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_text_output(result: ValidationResult, plugin_dir: Path) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("FORGE SCHEMA VALIDATION REPORT")
    lines.append("=" * 60)
    lines.append(f"Plugin: {plugin_dir}")
    lines.append("")
    
    # Errors
    if result.errors:
        lines.append("❌ ERRORS (must fix):")
        for issue in result.errors:
            lines.append(f"  • [{issue.component}] {issue.message}")
            lines.append(f"    File: {issue.file_path}")
            if issue.can_fix:
                lines.append(f"    Auto-fix: {issue.fix_description}")
            if issue.fix_guidance:
                lines.append(f"    → {issue.fix_guidance}")
            lines.append("")
    
    # Warnings
    if result.warnings:
        lines.append("⚠️  WARNINGS:")
        for issue in result.warnings:
            lines.append(f"  • [{issue.component}] {issue.message}")
            lines.append(f"    File: {issue.file_path}")
            if issue.can_fix:
                lines.append(f"    Auto-fix: {issue.fix_description}")
            if issue.fix_guidance:
                lines.append(f"    → {issue.fix_guidance}")
            lines.append("")
    
    # Auto-fixes applied
    if result.fixes_applied:
        lines.append("✅ AUTO-FIXED:")
        for fix in result.fixes_applied:
            lines.append(f"  • [{fix['component']}] {fix['description']}")
            lines.append(f"    File: {fix['file_path']}")
            lines.append("")
    
    # Summary
    lines.append("-" * 60)
    error_count = len(result.errors)
    warning_count = len(result.warnings)
    fix_count = len(result.fixes_applied)
    
    if result.is_valid:
        lines.append(f"✓ Plugin is VALID ({warning_count} warning(s), {fix_count} auto-fix(es))")
    else:
        lines.append(f"✗ Plugin is INVALID ({error_count} error(s), {warning_count} warning(s), {fix_count} auto-fix(es))")
    
    # Hint about fixable issues
    fixable_count = len(result.fixable)
    if fixable_count > 0:
        lines.append(f"\n💡 {fixable_count} issue(s) can be auto-fixed. Run with --fix to apply.")
    
    return "\n".join(lines)


def format_json_output(result: ValidationResult, plugin_dir: Path) -> str:
    """Format results as JSON."""
    output = {
        "plugin_dir": str(plugin_dir),
        "is_valid": result.is_valid,
        "errors": [
            {
                "component": i.component,
                "file_path": i.file_path,
                "message": i.message,
                "can_fix": i.can_fix,
                "fix_description": i.fix_description,
                "fix_guidance": i.fix_guidance
            }
            for i in result.errors
        ],
        "warnings": [
            {
                "component": i.component,
                "file_path": i.file_path,
                "message": i.message,
                "can_fix": i.can_fix,
                "fix_description": i.fix_description,
                "fix_guidance": i.fix_guidance
            }
            for i in result.warnings
        ],
        "fixes_applied": result.fixes_applied,
        "summary": {
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
            "fix_count": len(result.fixes_applied),
            "fixable_count": len(result.fixable)
        }
    }
    return json.dumps(output, indent=2)


# =============================================================================
# MAIN
# =============================================================================

def validate_plugin(plugin_dir: Path, do_fix: bool = False) -> ValidationResult:
    """Run all validations on a plugin directory."""
    result = ValidationResult()
    
    # 1. Validate plugin.json
    manifest = validate_plugin_json(plugin_dir, result, do_fix)
    
    if manifest:
        # 2. Validate component paths
        validate_component_paths(plugin_dir, manifest, result)
        
        # 3. Validate agent frontmatter
        validate_agents(plugin_dir, manifest, result, do_fix)
        
        # 4. Validate skill frontmatter
        validate_skills(plugin_dir, manifest, result, do_fix)
        
        # 5. Validate command frontmatter
        validate_commands(plugin_dir, manifest, result, do_fix)
        
        # 6. Validate hooks.json
        validate_hooks_json(plugin_dir, manifest, result, do_fix)
    
    # 7. Validate marketplace.json (optional)
    validate_marketplace_json(plugin_dir, result, do_fix)
    
    # 8. Validate Python syntax
    validate_python_syntax(plugin_dir, result)
    
    return result


def main():
    # Parse arguments
    plugin_dir = Path.cwd()
    do_fix = False
    json_output = False
    
    args = sys.argv[1:]
    for arg in args:
        if arg == "--fix":
            do_fix = True
        elif arg == "--json":
            json_output = True
        elif not arg.startswith("-"):
            plugin_dir = Path(arg)
    
    # Also check environment variable
    if "CLAUDE_PLUGIN_ROOT" in os.environ:
        plugin_dir = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
    
    # Validate
    result = validate_plugin(plugin_dir, do_fix)
    
    # Output
    if json_output:
        print(format_json_output(result, plugin_dir))
    else:
        print(format_text_output(result, plugin_dir))
    
    # Exit code
    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
