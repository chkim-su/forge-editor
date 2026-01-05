#!/usr/bin/env python3
"""
Unified plugin validation and auto-fix script.

Runs all automated checks and optionally fixes issues:
- Registration integrity (marketplace.json ↔ files)
- Frontmatter validation (YAML syntax, required fields)
- Directory structure validation
- Settings.json validation

Usage:
    python3 scripts/validate_all.py [plugin-path]
    python3 scripts/validate_all.py --fix           # Auto-fix issues
    python3 scripts/validate_all.py --fix --dry-run # Preview fixes
    python3 scripts/validate_all.py --json          # JSON output

Exit codes:
    0 - All passed (or all fixed with --fix)
    1 - Errors found (deployment will fail)
    2 - Warnings only (deployment may work)
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import yaml
except ImportError:
    # Fallback: simple YAML parser for frontmatter
    yaml = None


class Fix:
    """Represents a fixable issue."""
    def __init__(self, description: str, fix_func, *args):
        self.description = description
        self.fix_func = fix_func
        self.args = args

    def apply(self) -> bool:
        """Apply the fix. Returns True if successful."""
        try:
            self.fix_func(*self.args)
            return True
        except Exception as e:
            print(f"  ⚠️  Fix failed: {e}")
            return False


class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
        self.fixes: List[Fix] = []  # Auto-fixable issues

    def add_error(self, msg: str, fix: Optional[Fix] = None):
        self.errors.append(msg)
        if fix:
            self.fixes.append(fix)

    def add_warning(self, msg: str, fix: Optional[Fix] = None):
        self.warnings.append(msg)
        if fix:
            self.fixes.append(fix)

    def add_pass(self, msg: str):
        self.passed.append(msg)

    def merge(self, other: 'ValidationResult'):
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.passed.extend(other.passed)
        self.fixes.extend(other.fixes)


# =============================================================================
# SKILL REFERENCES: Map warnings/problems to skillmaker skills with solutions
# =============================================================================
# When validation detects issues, include reference to which skill has the solution
# Format: { "warning_pattern": ("skill_name", "reference_file", "brief_solution") }

SKILL_REFERENCES = {
    # W028: MUST/CRITICAL without hooks
    "W028": (
        "hook-templates",
        "references/full-examples.md",
        "PreToolUse/PostToolUse로 행동 강제"
    ),
    # W029: Skill frontmatter missing
    "W029": (
        "skill-design",
        "references/structure-rules.md",
        "YAML frontmatter: name, description, allowed-tools"
    ),
    # W030: Agent frontmatter missing tools
    "W030": (
        "orchestration-patterns",
        "references/context-isolation.md",
        "tools: [] = no MCP access; tools: omitted = all tools"
    ),
    # W031/W032: Skill content too long / missing references
    "W031": (
        "skill-design",
        "references/progressive-disclosure.md",
        "Core <500 words, move details to references/"
    ),
    "W032": (
        "skill-design",
        "references/progressive-disclosure.md",
        "Create references/ directory and move detailed content"
    ),
    # W033: Missing Skill() usage
    "W033": (
        "orchestration-patterns",
        "references/skill-loading-patterns.md",
        "Skill() 도구로 명시적 스킬 로딩"
    ),
    # W034: Multi-stage workflow without per-stage skill loading
    "W034": (
        "workflow-state-patterns",
        "references/complete-workflow-example.md",
        "단계별 Skill() 로딩 또는 hook-based 자동 로딩"
    ),
    # W035: NOT YET HOOKIFIED markers
    "W035": (
        "hook-templates",
        "references/full-examples.md",
        "PreToolUse hook으로 강제 구현"
    ),
    # MCP/Gateway related (detected by keywords)
    "MCP_GATEWAY": (
        "mcp-gateway-patterns",
        "references/daemon-shared-server.md",
        "Daemon (SSE) 패턴: python -m server --sse --port 8080"
    ),
    # Agent tools:[] issue (MCP access)
    "AGENT_NO_MCP": (
        "mcp-gateway-patterns",
        "references/agent-gateway-template.md",
        "tools: [] = MCP 접근 불가. Daemon 패턴 또는 tools 명시 필요"
    ),
    # W037: Non-English content (Korean, etc.)
    "W037": (
        "comprehensive-validation",
        "references/language-guidelines.md",
        "English preferred for code/docs; user-facing messages may use localized text"
    ),
    # W038: Emoji usage in code/docs
    "W038": (
        "comprehensive-validation",
        "references/style-guidelines.md",
        "Avoid emojis in code/docs; user-facing UI elements may include emojis"
    ),
    # W045: Test bed validation
    "W045": (
        "plugin-test-framework",
        "templates/test-runner.py",
        "Run /forge-editor:run-tests or create tests/e2e-test-runner.py"
    ),
    # W040: Form selection audit
    "W040": (
        "orchestration-patterns",
        "references/form-selection-guide.md",
        "Run form-selection-auditor agent for deep analysis"
    ),
    # W046: Component connectivity
    "W046": (
        "orchestration-patterns",
        "references/integration-checklist.md",
        "Ensure all components are connected and referenced"
    ),
}


def get_skill_hint(warning_code: str, context: str = "") -> str:
    """Get skill reference hint for a warning code."""
    ref = SKILL_REFERENCES.get(warning_code)
    if not ref:
        # Check for context-based hints
        if "gateway" in context.lower() or "mcp" in context.lower() or "subagent" in context.lower():
            ref = SKILL_REFERENCES.get("MCP_GATEWAY")
        elif "tools" in context.lower() and "[]" in context:
            ref = SKILL_REFERENCES.get("AGENT_NO_MCP")

    if ref:
        skill_name, ref_file, brief = ref
        return f"\n       → Fix: forge-editor:{skill_name} | {ref_file} | {brief}"
    return ""


def find_marketplace_json(start_path: Path) -> Tuple[Path | None, str | None]:
    """
    Find marketplace.json in .claude-plugin/ directory.

    Returns:
        (path, warning) - path to marketplace.json and optional warning message
    """
    claude_plugin = start_path / ".claude-plugin"
    if claude_plugin.exists():
        marketplace = claude_plugin / "marketplace.json"
        if marketplace.exists():
            return marketplace, None

    # Check for legacy plugin.json (not supported by Claude Code)
    plugin_json = start_path / "plugin.json"
    if plugin_json.exists():
        warning = (
            "⚠️ LEGACY FORMAT: Found plugin.json but Claude Code requires .claude-plugin/marketplace.json\n"
            "   plugin.json is NOT recognized during installation.\n"
            "   → Migration required: Move plugin.json to .claude-plugin/marketplace.json"
        )
        return plugin_json, warning

    return None, None


def parse_frontmatter(content: str) -> Tuple[dict | None, str | None]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return None, "No frontmatter found"

    try:
        end_idx = content.index('---', 3)
        yaml_content = content[3:end_idx].strip()
        if yaml:
            return yaml.safe_load(yaml_content), None
        else:
            # Simple fallback parser
            result = {}
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    result[key.strip()] = value.strip().strip('"').strip("'")
            return result, None
    except (ValueError, Exception) as e:
        return None, str(e)


# ============================================================================
# FIX FUNCTIONS
# ============================================================================

def fix_add_to_marketplace(marketplace_path: Path, item_type: str, item_path: str):
    """Add an item to marketplace.json."""
    data = json.loads(marketplace_path.read_text())
    plugins = data.get("plugins", [data])

    for plugin in plugins:
        if item_type not in plugin:
            plugin[item_type] = []

        # Normalize path format
        if not item_path.startswith("./"):
            item_path = f"./{item_path}"

        if item_path not in plugin[item_type]:
            plugin[item_type].append(item_path)

    # Write back with proper formatting
    marketplace_path.write_text(json.dumps(data, indent=2) + "\n")


def fix_remove_from_marketplace(marketplace_path: Path, item_type: str, item_path: str):
    """Remove an item from marketplace.json."""
    data = json.loads(marketplace_path.read_text())
    plugins = data.get("plugins", [data])

    for plugin in plugins:
        items = plugin.get(item_type, [])
        # Try both formats
        for fmt in [item_path, f"./{item_path}", item_path.lstrip("./")]:
            if fmt in items:
                items.remove(fmt)
                break
        plugin[item_type] = items

    marketplace_path.write_text(json.dumps(data, indent=2) + "\n")


def fix_create_command_stub(cmd_path: Path, name: str):
    """Create a stub command file with proper frontmatter."""
    content = f'''---
description: TODO: Add description for {name}
argument-hint: "[optional args]"
allowed-tools: ["Read", "Write", "Bash", "Grep", "Glob"]
---

# {name.replace('-', ' ').title()}

TODO: Add command instructions here.
'''
    cmd_path.parent.mkdir(parents=True, exist_ok=True)
    cmd_path.write_text(content)


def fix_create_agent_stub(agent_path: Path, name: str):
    """Create a stub agent file with proper frontmatter."""
    content = f'''---
name: {name}
description: TODO: Add description for {name}
tools: ["Read", "Write", "Bash", "Grep", "Glob"]
model: sonnet
---

# {name.replace('-', ' ').title()} Agent

TODO: Add agent instructions here.
'''
    agent_path.parent.mkdir(parents=True, exist_ok=True)
    agent_path.write_text(content)


def fix_create_skill_stub(skill_dir: Path, name: str):
    """Create a stub SKILL.md file."""
    skill_md = skill_dir / "SKILL.md"
    content = f'''---
name: {name}
description: TODO: Add description for {name}
allowed-tools: ["Read", "Grep", "Glob"]
---

# {name.replace('-', ' ').title()}

TODO: Add skill instructions here.

## When to Use

- TODO: Add trigger scenarios

## How to Use

TODO: Add usage instructions
'''
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(content)


def fix_add_frontmatter(file_path: Path, frontmatter: dict):
    """Add or replace frontmatter in a markdown file."""
    content = file_path.read_text()

    # Build YAML frontmatter
    fm_lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            fm_lines.append(f'{key}: {json.dumps(value)}')
        elif isinstance(value, str) and '\n' in value:
            fm_lines.append(f'{key}: |')
            for line in value.split('\n'):
                fm_lines.append(f'  {line}')
        else:
            fm_lines.append(f'{key}: {value}')
    fm_lines.append("---\n")
    fm_str = '\n'.join(fm_lines)

    # Remove existing frontmatter if present
    if content.startswith('---'):
        try:
            end_idx = content.index('---', 3)
            content = content[end_idx + 3:].lstrip('\n')
        except ValueError:
            pass

    file_path.write_text(fm_str + content)


def fix_source_path(marketplace_path: Path, plugin_idx: int, new_source: str):
    """Fix source path in marketplace.json."""
    data = json.loads(marketplace_path.read_text())
    plugins = data.get("plugins", [data])

    if plugin_idx < len(plugins):
        plugins[plugin_idx]["source"] = new_source

    marketplace_path.write_text(json.dumps(data, indent=2) + "\n")


def fix_add_shebang(script_path: Path):
    """Add shebang to Python script."""
    content = script_path.read_text()
    if not content.startswith('#!'):
        content = '#!/usr/bin/env python3\n' + content
        script_path.write_text(content)


def fix_make_executable(script_path: Path):
    """Make script executable."""
    os.chmod(script_path, os.stat(script_path).st_mode | 0o111)


def fix_path_format(marketplace_path: Path, item_type: str, old_path: str, new_path: str):
    """Fix a path format in marketplace.json (e.g., add/remove .md extension)."""
    data = json.loads(marketplace_path.read_text())
    plugins = data.get("plugins", [data])

    for plugin in plugins:
        items = plugin.get(item_type, [])
        for i, item in enumerate(items):
            # Normalize for comparison
            if item.rstrip('/') == old_path.rstrip('/') or item == old_path:
                items[i] = new_path
                break

    marketplace_path.write_text(json.dumps(data, indent=2) + "\n")


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================


def extract_path(item: str | dict, path_key: str = "path") -> str:
    """Extract path from string or dictionary format.

    Plugins can define commands/agents/skills in two formats:
    1. String format: "./agents/agent-name.md"
    2. Dictionary format: {"name": "agent-name", "path": "agents/agent-name.md", ...}

    Returns the path string, or empty string if not extractable.
    """
    if isinstance(item, str):
        return item
    elif isinstance(item, dict):
        # Try common path keys
        for key in [path_key, "path", "file", "src"]:
            if key in item:
                return item[key]
        # Fallback: if has "name" but no path, construct default path
        if "name" in item:
            return item["name"]
    return ""


def validate_registration(plugin_root: Path, plugin_data: dict, marketplace_path: Path) -> ValidationResult:
    """Validate marketplace.json entries match actual files."""
    result = ValidationResult()

    registered_commands = plugin_data.get("commands", [])
    registered_agents = plugin_data.get("agents", [])
    registered_skills = plugin_data.get("skills", [])

    # Validate commands
    commands_dir = plugin_root / "commands"
    if commands_dir.exists():
        actual_commands = {f.stem for f in commands_dir.glob("*.md")}
        registered_set = set()

        for cmd_entry in registered_commands:
            # Extract path from string or dictionary format
            cmd = extract_path(cmd_entry)
            if not cmd:
                result.add_warning(f"Command entry has no extractable path: {cmd_entry}")
                continue

            # CRITICAL: Validate path format - commands MUST end with .md
            if not cmd.endswith(".md"):
                correct_path = cmd + ".md"
                result.add_error(
                    f'Command path "{cmd}" missing .md extension (plugin system will fail to load)',
                    Fix(f'Fix path to "{correct_path}"', fix_path_format, marketplace_path, "commands", cmd, correct_path)
                )
                # Still check if the file would exist with correct extension
                name = cmd.replace("./commands/", "").replace("commands/", "")
            else:
                name = cmd.replace("./commands/", "").replace("commands/", "").replace(".md", "")

            registered_set.add(name)

            cmd_file = commands_dir / f"{name}.md"
            if cmd_file.exists():
                if cmd.endswith(".md"):
                    result.add_pass(f"commands/{name}.md registered and exists")
            else:
                result.add_error(
                    f"commands/{name}.md NOT FOUND (registered in marketplace.json)",
                    Fix(f"Create stub commands/{name}.md", fix_create_command_stub, cmd_file, name)
                )

        for actual in actual_commands:
            if actual not in registered_set:
                result.add_error(
                    f"commands/{actual}.md exists but NOT REGISTERED in marketplace.json",
                    Fix(f"Add commands/{actual}.md to marketplace.json",
                        fix_add_to_marketplace, marketplace_path, "commands", f"commands/{actual}.md")
                )

    # Validate agents
    agents_dir = plugin_root / "agents"
    if agents_dir.exists():
        actual_agents = {f.stem for f in agents_dir.glob("*.md")}
        registered_set = set()

        for agent_entry in registered_agents:
            # Extract path from string or dictionary format
            agent = extract_path(agent_entry)
            if not agent:
                result.add_warning(f"Agent entry has no extractable path: {agent_entry}")
                continue

            # CRITICAL: Validate path format - agents MUST end with .md
            if not agent.endswith(".md"):
                correct_path = agent + ".md"
                result.add_error(
                    f'Agent path "{agent}" missing .md extension (plugin system will fail to load)',
                    Fix(f'Fix path to "{correct_path}"', fix_path_format, marketplace_path, "agents", agent, correct_path)
                )
                name = agent.replace("./agents/", "").replace("agents/", "")
            else:
                name = agent.replace("./agents/", "").replace("agents/", "").replace(".md", "")

            registered_set.add(name)

            agent_file = agents_dir / f"{name}.md"
            if agent_file.exists():
                if agent.endswith(".md"):
                    result.add_pass(f"agents/{name}.md registered and exists")
            else:
                result.add_error(
                    f"agents/{name}.md NOT FOUND",
                    Fix(f"Create stub agents/{name}.md", fix_create_agent_stub, agent_file, name)
                )

        for actual in actual_agents:
            if actual not in registered_set:
                result.add_error(
                    f"agents/{actual}.md exists but NOT REGISTERED",
                    Fix(f"Add agents/{actual}.md to marketplace.json",
                        fix_add_to_marketplace, marketplace_path, "agents", f"agents/{actual}.md")
                )

    # Validate skills
    skills_dir = plugin_root / "skills"
    if skills_dir.exists():
        actual_skills = {d.name for d in skills_dir.iterdir() if d.is_dir()}
        registered_set = set()

        for skill_entry in registered_skills:
            # Extract path from string or dictionary format
            skill = extract_path(skill_entry)
            if not skill:
                result.add_warning(f"Skill entry has no extractable path: {skill_entry}")
                continue

            # CRITICAL: Validate path format - skills are directories, must NOT end with .md
            if skill.endswith(".md"):
                correct_path = skill.replace(".md", "").rstrip("/")
                result.add_error(
                    f'Skill path "{skill}" has .md extension but skills are directories',
                    Fix(f'Fix path to "{correct_path}"', fix_path_format, marketplace_path, "skills", skill, correct_path)
                )
                name = skill.replace("./skills/", "").replace("skills/", "").replace(".md", "").rstrip("/")
            else:
                name = skill.replace("./skills/", "").replace("skills/", "").rstrip("/")

            registered_set.add(name)

            skill_md = skills_dir / name / "SKILL.md"
            if skill_md.exists():
                if not skill.endswith(".md"):
                    result.add_pass(f"skills/{name}/SKILL.md registered and exists")
            elif (skills_dir / name).exists():
                result.add_error(
                    f"skills/{name}/ exists but missing SKILL.md",
                    Fix(f"Create skills/{name}/SKILL.md", fix_create_skill_stub, skills_dir / name, name)
                )
            else:
                result.add_error(
                    f"skills/{name}/ NOT FOUND",
                    Fix(f"Create skills/{name}/ with SKILL.md", fix_create_skill_stub, skills_dir / name, name)
                )

        for actual in actual_skills:
            if actual not in registered_set:
                skill_md = skills_dir / actual / "SKILL.md"
                if skill_md.exists():
                    result.add_error(
                        f"skills/{actual}/ exists with SKILL.md but NOT REGISTERED",
                        Fix(f"Add skills/{actual} to marketplace.json",
                            fix_add_to_marketplace, marketplace_path, "skills", f"skills/{actual}")
                    )

    return result


def validate_frontmatter_fields(plugin_root: Path) -> ValidationResult:
    """Validate frontmatter in all markdown files."""
    result = ValidationResult()

    # Commands
    commands_dir = plugin_root / "commands"
    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.md"):
            content = cmd_file.read_text()
            fm, error = parse_frontmatter(content)

            if error or not fm:
                default_fm = {
                    "description": f"TODO: Add description for {cmd_file.stem}",
                    "argument-hint": "[optional args]",
                    "allowed-tools": ["Read", "Write", "Bash", "Grep", "Glob"]
                }
                result.add_error(
                    f"{cmd_file.name}: {error or 'Missing frontmatter'}",
                    Fix(f"Add frontmatter to {cmd_file.name}", fix_add_frontmatter, cmd_file, default_fm)
                )
                continue

            if not fm.get("description"):
                fm["description"] = f"TODO: Add description for {cmd_file.stem}"
                result.add_error(
                    f"{cmd_file.name}: Missing 'description' field",
                    Fix(f"Add description to {cmd_file.name}", fix_add_frontmatter, cmd_file, fm)
                )
            elif "TODO" in str(fm.get("description", "")):
                result.add_warning(f"{cmd_file.name}: description contains TODO")
            else:
                result.add_pass(f"{cmd_file.name}: frontmatter valid")

    # Agents
    agents_dir = plugin_root / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text()
            fm, error = parse_frontmatter(content)

            if error or not fm:
                default_fm = {
                    "name": agent_file.stem,
                    "description": f"TODO: Add description for {agent_file.stem}",
                    "tools": ["Read", "Write", "Bash", "Grep", "Glob"],
                    "model": "sonnet"
                }
                result.add_error(
                    f"{agent_file.name}: {error or 'Missing frontmatter'}",
                    Fix(f"Add frontmatter to {agent_file.name}", fix_add_frontmatter, agent_file, default_fm)
                )
                continue

            needs_fix = False
            if not fm.get("name"):
                fm["name"] = agent_file.stem
                needs_fix = True
                result.add_error(f"{agent_file.name}: Missing 'name' field")
            if not fm.get("description"):
                fm["description"] = f"TODO: Add description for {agent_file.stem}"
                needs_fix = True
                result.add_error(f"{agent_file.name}: Missing 'description' field")
            if "tools" not in fm:
                # W030: Decision-first approach for missing tools field
                w030_msg = [
                    f"W030: {agent_file.name}: Missing 'tools' field.",
                    "",
                    "🔍 DECISION REQUIRED - 이것이 의도적인지 판단하세요:",
                    "",
                    "  📋 판단 후 조치:",
                    "  ├─ YES (의도적, 모든 도구 사용) → 명시적으로 선언",
                    "  │   tools: [\"*\"]  # 또는 tools 생략 (all tools)",
                    "  │   주석: # Intentionally omitted for full access",
                    "  │",
                    "  └─ NO (실수, 제한 필요) → 필요한 도구만 명시",
                    "      tools: [\"Read\", \"Grep\", \"Glob\"]",
                    "      tools: []  # MCP 도구 없음",
                    "",
                    "⛔ tools 필드 누락을 무시하지 마세요 - 보안에 영향을 줄 수 있습니다.",
                    get_skill_hint("W030", "agent tools")
                ]
                result.add_warning("\n".join(w030_msg))

            if needs_fix:
                result.fixes.append(Fix(f"Fix frontmatter in {agent_file.name}", fix_add_frontmatter, agent_file, fm))
            elif fm.get("description") and "TODO" not in str(fm.get("description", "")):
                result.add_pass(f"{agent_file.name}: frontmatter valid")

    # Skills
    skills_dir = plugin_root / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            content = skill_md.read_text()
            fm, error = parse_frontmatter(content)

            if error or not fm:
                default_fm = {
                    "name": skill_dir.name,
                    "description": f"TODO: Add description for {skill_dir.name}",
                    "allowed-tools": ["Read", "Grep", "Glob"]
                }
                result.add_error(
                    f"skills/{skill_dir.name}/SKILL.md: {error or 'Missing frontmatter'}",
                    Fix(f"Add frontmatter to skills/{skill_dir.name}/SKILL.md", fix_add_frontmatter, skill_md, default_fm)
                )
                continue

            needs_fix = False
            if not fm.get("name"):
                fm["name"] = skill_dir.name
                needs_fix = True
                result.add_error(f"skills/{skill_dir.name}/SKILL.md: Missing 'name' field")
            if not fm.get("description"):
                fm["description"] = f"TODO: Add description for {skill_dir.name}"
                needs_fix = True
                result.add_error(f"skills/{skill_dir.name}/SKILL.md: Missing 'description' field")
            elif "TODO" in str(fm.get("description", "")):
                result.add_warning(f"skills/{skill_dir.name}/SKILL.md: description contains TODO")
            else:
                if not needs_fix:
                    result.add_pass(f"skills/{skill_dir.name}/SKILL.md: frontmatter valid")

            if needs_fix:
                result.fixes.append(Fix(f"Fix frontmatter in skills/{skill_dir.name}/SKILL.md",
                                       fix_add_frontmatter, skill_md, fm))

    return result


def validate_source_path(plugin_data: dict, marketplace_path: Path, plugin_idx: int) -> ValidationResult:
    """Validate source path format."""
    result = ValidationResult()
    source = plugin_data.get("source", "")

    if isinstance(source, str):
        if source and source not in [".", "./"] and not source.startswith("./"):
            fixed_source = f"./{source}"
            result.add_error(
                f'source "{source}" must start with "./" (e.g., "{fixed_source}")',
                Fix(f'Fix source path to "{fixed_source}"', fix_source_path, marketplace_path, plugin_idx, fixed_source)
            )
        else:
            result.add_pass("source path format valid")
    elif isinstance(source, dict):
        if "source" not in source or "repo" not in source:
            result.add_error('GitHub source format requires {"source": "github", "repo": "user/repo"}')
        else:
            result.add_pass("GitHub source format valid")

    return result


def validate_scripts(plugin_root: Path) -> ValidationResult:
    """Validate script files have shebang and are executable."""
    result = ValidationResult()

    scripts_dir = plugin_root / "scripts"
    if not scripts_dir.exists():
        return result

    for script in scripts_dir.glob("*.py"):
        content = script.read_text()

        # Check shebang
        if not content.startswith('#!'):
            result.add_warning(
                f"scripts/{script.name}: Missing shebang",
                Fix(f"Add shebang to {script.name}", fix_add_shebang, script)
            )
        else:
            result.add_pass(f"scripts/{script.name}: has shebang")

        # Check executable (Unix only)
        if os.name != 'nt':
            if not os.access(script, os.X_OK):
                result.add_warning(
                    f"scripts/{script.name}: Not executable",
                    Fix(f"Make {script.name} executable", fix_make_executable, script)
                )

    return result


def _analyze_keyword_context(content: str, keyword: str, pattern: str) -> List[Dict[str, Any]]:
    """
    Analyze the context around each keyword match to detect false positives.

    Returns list of matches with context analysis:
    - match: the matched text
    - context: surrounding text (±30 chars)
    - likely_false_positive: bool
    - reason: why it might be false positive
    """
    import re
    results = []

    # Find all matches with their positions
    for m in re.finditer(pattern, content, re.IGNORECASE):
        start = max(0, m.start() - 30)
        end = min(len(content), m.end() + 30)
        context = content[start:end].replace('\n', ' ')

        likely_fp = False
        reason = ""

        # Check for template variable pattern: {keyword_something}
        template_check = content[max(0, m.start()-1):m.end()+20]
        if re.search(r'\{[^}]*' + keyword + r'[^}]*\}', template_check, re.IGNORECASE):
            likely_fp = True
            reason = "템플릿 변수 (e.g., {critical_analysis})"

        # Check for table header pattern: | Keyword |
        table_check = content[max(0, m.start()-3):m.end()+3]
        if re.search(r'\|\s*' + keyword + r'\s*\|', table_check, re.IGNORECASE):
            likely_fp = True
            reason = "테이블 헤더"

        # Check if inside code block (``` ... ```)
        before_content = content[:m.start()]
        code_opens = before_content.count('```')
        if code_opens % 2 == 1:  # Odd number means we're inside a code block
            likely_fp = True
            reason = "코드 블록 내"

        # Check for inline code (`keyword`)
        inline_check = content[max(0, m.start()-1):m.end()+1]
        if re.search(r'`[^`]*' + keyword, inline_check, re.IGNORECASE):
            likely_fp = True
            reason = "인라인 코드"

        results.append({
            "match": m.group(),
            "context": context,
            "likely_false_positive": likely_fp,
            "reason": reason
        })

    return results


def validate_hookify_compliance(plugin_root: Path) -> ValidationResult:
    """
    W028: Check if MUST/CRITICAL/REQUIRED keywords exist without corresponding hooks.
    W035: Check for 'NOT YET HOOKIFIED' markers indicating known unhookified items.

    Per skillmaker's own principle: "문서 기반 강제는 무의미합니다"

    Enhanced with context-aware analysis to reduce false positives and guide
    proper decision-making (not bypass attempts).
    """
    result = ValidationResult()

    # Enforcement keywords that should be hookified
    enforcement_keywords = [
        (r'\bMUST\b', 'MUST'),
        (r'\bCRITICAL\b', 'CRITICAL'),
        (r'\bREQUIRED\b', 'REQUIRED'),
        (r'\bMANDATORY\b', 'MANDATORY'),
        (r'\b강제\b', '강제'),
        (r'\b반드시\b', '반드시')
    ]

    # Unhookified markers
    unhookified_markers = [
        'NOT YET HOOKIFIED',
        'NOT HOOKIFIED',
        '⚠️ **NOT YET HOOKIFIED**'
    ]

    import re

    # Check if hooks.json exists
    hooks_json = plugin_root / "hooks" / "hooks.json"
    has_hooks = hooks_json.exists()

    # Collect files to check
    files_to_check = []

    # Skills
    skills_dir = plugin_root / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    files_to_check.append(skill_md)

    # Agents
    agents_dir = plugin_root / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            files_to_check.append(agent_file)

    # Commands
    commands_dir = plugin_root / "commands"
    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.md"):
            files_to_check.append(cmd_file)

    # Track findings with context analysis
    files_with_enforcement = []  # [(rel_path, [analysis_results])]
    unhookified_found = []

    for file_path in files_to_check:
        try:
            content = file_path.read_text()
        except Exception:
            continue

        rel_path = file_path.relative_to(plugin_root)
        file_matches = []

        # Check for enforcement keywords with context analysis
        for pattern, keyword in enforcement_keywords:
            if re.search(pattern, content):
                analysis = _analyze_keyword_context(content, keyword, pattern)
                file_matches.extend(analysis)

        if file_matches:
            files_with_enforcement.append((str(rel_path), file_matches))

        # Check for unhookified markers (W035)
        for marker in unhookified_markers:
            if marker in content:
                # Count occurrences
                count = content.count(marker)
                unhookified_found.append((str(rel_path), count))
                break

    # W028: Enforcement keywords without hooks - with decision guidance
    if files_with_enforcement and not has_hooks:
        # Categorize matches
        likely_rules = []
        likely_fps = []

        for rel_path, matches in files_with_enforcement:
            for m in matches:
                if m["likely_false_positive"]:
                    likely_fps.append((rel_path, m))
                else:
                    likely_rules.append((rel_path, m))

        # Build decision-focused message
        msg_parts = [
            f"W028: {len(files_with_enforcement)} file(s) contain enforcement keywords.",
            "",
            "🔍 DECISION REQUIRED - 우회하지 말고 먼저 판단하세요:",
            ""
        ]

        # Show analysis per file
        for rel_path, matches in files_with_enforcement[:3]:  # Limit to 3 files
            msg_parts.append(f"  📄 {rel_path}:")
            for m in matches[:2]:  # Limit to 2 matches per file
                if m["likely_false_positive"]:
                    msg_parts.append(f"     \"{m['match']}\" → ⚠️ {m['reason']} (false positive 가능)")
                else:
                    msg_parts.append(f"     \"{m['match']}\" → 🔴 규칙으로 보임 (hook 필요 가능)")

        msg_parts.extend([
            "",
            "📋 판단 후 조치:",
            "  ├─ YES (진짜 규칙) → hook으로 강제 필요",
            "  │   경로: /forge-editor:hook-templates 또는 /hookify",
            "  │   참조: Skill(\"forge-editor:hook-sdk-integration\")",
            "  │",
            "  └─ NO (false positive) → 정당한 용어 변경",
            "      - 테이블 헤더: Required → 필수",
            "      - 템플릿 변수: {critical_X} → {critique_X}",
            "      - 또는 hooks/hooks.json 빈 파일 생성 (규칙 없음을 명시)",
            "",
            "⛔ 키워드만 바꿔서 경고를 우회하는 것은 금지됩니다."
        ])

        result.add_warning("\n".join(msg_parts))
    elif files_with_enforcement and has_hooks:
        # hooks.json exists, that's good
        result.add_pass(f"W028: Enforcement keywords found in {len(files_with_enforcement)} files, hooks.json exists")

    # W035: Unhookified markers found
    for rel_path, count in unhookified_found:
        hint = get_skill_hint("W035")
        result.add_warning(
            f"W035: {rel_path}: Contains {count} 'NOT YET HOOKIFIED' marker(s) - "
            f"known limitation awaiting hookification{hint}"
        )

    if not unhookified_found and files_to_check:
        result.add_pass("W035: No unhookified markers found")

    return result


def validate_unnecessary_files(plugin_root: Path) -> ValidationResult:
    """
    W036: Detect unnecessary files that should be cleaned up or gitignored.

    Categories:
    - DELETE: Files that should be removed (logs, caches)
    - GITIGNORE: Files that should be in .gitignore
    - SENSITIVE: Files that may contain secrets (.env)
    """
    result = ValidationResult()

    # Patterns to detect with recommendations
    # Format: (pattern, category, description, recommendation)
    patterns = [
        # Log files - DELETE
        ("firebase-debug.log", "DELETE", "Firebase debug log", "rm firebase-debug.log"),
        ("npm-debug.log", "DELETE", "NPM debug log", "rm npm-debug.log"),
        ("yarn-error.log", "DELETE", "Yarn error log", "rm yarn-error.log"),
        ("debug.log", "DELETE", "Debug log", "rm debug.log"),
        ("*.log", "DELETE", "Log files", "rm *.log"),

        # Cache directories - DELETE
        ("__pycache__", "DELETE", "Python cache", "rm -rf __pycache__"),
        (".pytest_cache", "DELETE", "Pytest cache", "rm -rf .pytest_cache"),
        (".mypy_cache", "DELETE", "Mypy cache", "rm -rf .mypy_cache"),
        ("node_modules", "DELETE", "Node modules (large)", "rm -rf node_modules"),
        (".cache", "DELETE", "Cache directory", "rm -rf .cache"),

        # System files - GITIGNORE
        (".DS_Store", "GITIGNORE", "macOS metadata", 'echo ".DS_Store" >> .gitignore'),
        ("Thumbs.db", "GITIGNORE", "Windows thumbnail", 'echo "Thumbs.db" >> .gitignore'),

        # IDE files - GITIGNORE (optional, some prefer to keep)
        (".idea", "GITIGNORE", "JetBrains IDE config", 'echo ".idea/" >> .gitignore'),
        (".vscode", "GITIGNORE", "VS Code config", 'echo ".vscode/" >> .gitignore'),

        # Sensitive files - SENSITIVE (should never be committed)
        (".env", "SENSITIVE", "Environment variables", "⚠️ Contains secrets - do not commit"),
        (".env.local", "SENSITIVE", "Local environment", "⚠️ Contains secrets - do not commit"),
        (".env.production", "SENSITIVE", "Production secrets", "⚠️ Contains secrets - do not commit"),
        ("credentials.json", "SENSITIVE", "Credentials file", "⚠️ Contains secrets - do not commit"),
        ("*.pem", "SENSITIVE", "Private key", "⚠️ Contains secrets - do not commit"),
        ("*.key", "SENSITIVE", "Private key", "⚠️ Contains secrets - do not commit"),
    ]

    found_issues = {
        "DELETE": [],
        "GITIGNORE": [],
        "SENSITIVE": []
    }

    # Check for files matching patterns
    for pattern, category, description, recommendation in patterns:
        if "*" in pattern:
            # Glob pattern
            matches = list(plugin_root.glob(pattern))
            # Also check in subdirectories (one level)
            for subdir in plugin_root.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    matches.extend(subdir.glob(pattern))
        else:
            # Exact match
            target = plugin_root / pattern
            matches = [target] if target.exists() else []

        for match in matches:
            rel_path = match.relative_to(plugin_root)
            found_issues[category].append((str(rel_path), description, recommendation))

    # Check .gitignore for proper entries
    gitignore_path = plugin_root / ".gitignore"
    gitignore_content = gitignore_path.read_text() if gitignore_path.exists() else ""

    # Generate warnings
    if found_issues["SENSITIVE"]:
        msg_parts = [
            "W036: SENSITIVE files detected - potential security risk!",
            "",
            "🔴 These files may contain secrets and should NEVER be committed:",
            ""
        ]
        for path, desc, rec in found_issues["SENSITIVE"]:
            msg_parts.append(f"  • {path} ({desc})")
            msg_parts.append(f"    {rec}")
        msg_parts.extend([
            "",
            "📋 Recommended actions:",
            "  1. Add to .gitignore IMMEDIATELY",
            "  2. If already committed, use 'git rm --cached <file>'",
            "  3. Consider rotating any exposed secrets"
        ])
        result.add_warning("\n".join(msg_parts))

    if found_issues["DELETE"]:
        msg_parts = [
            "W036: Unnecessary files found - cleanup recommended:",
            ""
        ]
        for path, desc, rec in found_issues["DELETE"][:10]:  # Limit to 10
            msg_parts.append(f"  • {path} ({desc})")
        if len(found_issues["DELETE"]) > 10:
            msg_parts.append(f"  ... and {len(found_issues['DELETE']) - 10} more")
        msg_parts.extend([
            "",
            "📋 Cleanup commands:",
        ])
        # Group by recommendation
        seen_recs = set()
        for _, _, rec in found_issues["DELETE"]:
            if rec not in seen_recs:
                msg_parts.append(f"  {rec}")
                seen_recs.add(rec)
        result.add_warning("\n".join(msg_parts))

    if found_issues["GITIGNORE"]:
        # Check if already in .gitignore
        not_ignored = []
        for path, desc, rec in found_issues["GITIGNORE"]:
            base_name = Path(path).name
            if base_name not in gitignore_content:
                not_ignored.append((path, desc, rec))

        if not_ignored:
            msg_parts = [
                "W036: Files that should be in .gitignore:",
                ""
            ]
            for path, desc, rec in not_ignored:
                msg_parts.append(f"  • {path} ({desc})")
            msg_parts.extend([
                "",
                "📋 Add to .gitignore:",
            ])
            for path, _, _ in not_ignored:
                base = Path(path).name
                if base.startswith("."):
                    msg_parts.append(f'  echo "{base}" >> .gitignore')
                else:
                    msg_parts.append(f'  echo "{base}/" >> .gitignore')
            result.add_warning("\n".join(msg_parts))

    if not any(found_issues.values()):
        result.add_pass("W036: No unnecessary files detected")

    return result


def validate_settings_json() -> ValidationResult:
    """Check for common settings.json misconfigurations."""
    result = ValidationResult()
    home = Path.home()

    settings_paths = [
        home / ".claude" / "settings.json",
        home / ".config" / "claude-code" / "settings.json",
    ]

    for settings_path in settings_paths:
        if not settings_path.exists():
            continue

        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, IOError):
            continue

        plugins = settings.get("plugins", [])
        for i, plugin in enumerate(plugins):
            if isinstance(plugin, dict):
                source = plugin.get("source", "")
                if isinstance(source, str) and source:
                    if not source.startswith("./") and not source.startswith("/"):
                        result.add_error(
                            f'settings.json plugins[{i}].source "{source}" must start with "./"'
                        )

        marketplaces = settings.get("extraKnownMarketplaces", {})
        for name, config in marketplaces.items():
            source = config.get("source", "")
            if isinstance(source, str) and source and not source.startswith("./"):
                result.add_error(
                    f'settings.json extraKnownMarketplaces.{name}.source must start with "./"'
                )

    return result


def validate_language_preference(plugin_root: Path) -> ValidationResult:
    """
    W037: Detect non-English content in code and documentation.

    Checks for Korean (and other non-ASCII) text in:
    - Python/JS code comments
    - Markdown documentation (SKILL.md, agent descriptions)
    - YAML frontmatter descriptions

    Exceptions (allowed):
    - User-facing messages (error messages, help text patterns)
    - i18n/localization files
    - Example/template strings clearly marked
    """
    import re
    result = ValidationResult()

    # Korean character pattern (Hangul)
    korean_pattern = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]+')

    # Patterns that indicate user-facing content (exceptions)
    user_facing_patterns = [
        r'error\s*[=:]\s*["\']',      # error = "..." or error: "..."
        r'message\s*[=:]\s*["\']',    # message = "..."
        r'print\s*\(',                 # print(...)
        r'console\.\w+\s*\(',          # console.log(...)
        r'raise\s+\w+Exception',       # raise SomeException
        r'\.help\s*=',                 # argument help text
        r'help\s*[=:]\s*["\']',       # help = "..."
        r'description.*user',          # description for user
        r'#\s*i18n',                   # i18n marker
        r'#\s*user-facing',            # user-facing marker
    ]
    user_facing_regex = re.compile('|'.join(user_facing_patterns), re.IGNORECASE)

    # Files to check
    files_to_check = []

    # Python files
    files_to_check.extend(plugin_root.rglob("*.py"))
    # Markdown files
    files_to_check.extend(plugin_root.rglob("*.md"))
    # JavaScript/TypeScript
    files_to_check.extend(plugin_root.rglob("*.js"))
    files_to_check.extend(plugin_root.rglob("*.ts"))

    # Skip certain directories
    skip_dirs = {'.git', 'node_modules', '__pycache__', '.pytest_cache', 'i18n', 'locales'}

    issues_found = []

    for filepath in files_to_check:
        # Skip if in excluded directory
        if any(skip in filepath.parts for skip in skip_dirs):
            continue

        try:
            content = filepath.read_text(encoding='utf-8')
        except (UnicodeDecodeError, IOError):
            continue

        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Check for Korean text
            korean_matches = korean_pattern.findall(line)
            if korean_matches:
                # Check if this is a user-facing exception
                if user_facing_regex.search(line):
                    continue  # Skip user-facing content

                rel_path = filepath.relative_to(plugin_root)
                # Limit to first few matches per file
                if len([i for i in issues_found if str(rel_path) in i]) < 3:
                    sample_text = korean_matches[0][:20]
                    issues_found.append(
                        f"{rel_path}:{line_num}: Korean text detected: '{sample_text}...'"
                    )

    hint = get_skill_hint("W037")

    if issues_found:
        msg_parts = [
            "W037: Non-English content detected in code/documentation",
            "",
            "English is preferred for maintainability and international collaboration.",
            "User-facing messages (errors, help text) may use localized text.",
            ""
        ]
        for issue in issues_found[:10]:  # Limit output
            msg_parts.append(f"  • {issue}")
        if len(issues_found) > 10:
            msg_parts.append(f"  ... and {len(issues_found) - 10} more")
        if hint:
            msg_parts.extend(["", hint])
        result.add_warning("\n".join(msg_parts))
    else:
        result.add_pass("W037: No non-English content issues detected")

    return result


def validate_emoji_usage(plugin_root: Path) -> ValidationResult:
    """
    W038: Detect emoji usage in code and documentation.

    Checks for emojis in:
    - Code files (Python, JS, TS)
    - Documentation (SKILL.md, agent descriptions)

    Exceptions (allowed):
    - User-facing UI elements (status indicators)
    - Validation output (this script's own output)
    - Example/template strings clearly marked
    - Files explicitly marked as UI components
    """
    import re
    result = ValidationResult()

    # Emoji pattern (common emoji ranges)
    # This covers most common emojis including emoticons, symbols, etc.
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U00002600-\U000026FF"  # misc symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended
        "]+",
        flags=re.UNICODE
    )

    # Patterns that indicate allowed emoji usage (UI/status indicators)
    allowed_patterns = [
        r'print\s*\(.*["\'].*["\']',   # print statements (validation output)
        r'STATUS:',                     # status indicators
        r'result\.add_',                # validation result methods
        r'#\s*ui-element',              # UI element marker
        r'#\s*status-indicator',        # status indicator marker
        r'user[_-]?facing',             # user-facing marker
        r'\.add_error\(',               # validation error output
        r'\.add_warning\(',             # validation warning output
        r'\.add_pass\(',                # validation pass output
    ]
    allowed_regex = re.compile('|'.join(allowed_patterns), re.IGNORECASE)

    # Files to check
    files_to_check = []
    files_to_check.extend(plugin_root.rglob("*.py"))
    files_to_check.extend(plugin_root.rglob("*.md"))
    files_to_check.extend(plugin_root.rglob("*.js"))
    files_to_check.extend(plugin_root.rglob("*.ts"))

    # Skip certain directories and files
    skip_dirs = {'.git', 'node_modules', '__pycache__', '.pytest_cache'}
    skip_files = {'validate_all.py'}  # This script uses emojis for output

    issues_found = []

    for filepath in files_to_check:
        # Skip if in excluded directory
        if any(skip in filepath.parts for skip in skip_dirs):
            continue
        # Skip specific files
        if filepath.name in skip_files:
            continue

        try:
            content = filepath.read_text(encoding='utf-8')
        except (UnicodeDecodeError, IOError):
            continue

        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Check for emojis
            emoji_matches = emoji_pattern.findall(line)
            if emoji_matches:
                # Check if this is an allowed usage
                if allowed_regex.search(line):
                    continue

                rel_path = filepath.relative_to(plugin_root)
                # Limit to first few matches per file
                if len([i for i in issues_found if str(rel_path) in i]) < 3:
                    emojis = ''.join(emoji_matches)[:5]
                    issues_found.append(
                        f"{rel_path}:{line_num}: Emoji detected: {emojis}"
                    )

    hint = get_skill_hint("W038")

    if issues_found:
        msg_parts = [
            "W038: Emoji usage detected in code/documentation",
            "",
            "Emojis are discouraged in code for professionalism and accessibility.",
            "User-facing UI elements and status indicators may include emojis.",
            ""
        ]
        for issue in issues_found[:10]:
            msg_parts.append(f"  • {issue}")
        if len(issues_found) > 10:
            msg_parts.append(f"  ... and {len(issues_found) - 10} more")
        if hint:
            msg_parts.extend(["", hint])
        result.add_warning("\n".join(msg_parts))
    else:
        result.add_pass("W038: No emoji usage issues detected")

    return result


def validate_test_coverage(plugin_root: Path) -> ValidationResult:
    """
    W045: Validate test bed testing completion.

    Checks for:
    - TEST-RESULTS.md existence
    - Test pass status
    - Recent test execution (within 24 hours for deployment)
    - E2E test infrastructure presence

    This is a MANDATORY gate for deployment.
    """
    from datetime import datetime, timedelta
    import re
    result = ValidationResult()

    test_results_path = plugin_root / "TEST-RESULTS.md"
    test_runner_path = plugin_root / "tests" / "test-runner.py"
    e2e_runner_path = plugin_root / "tests" / "e2e-test-runner.py"

    # Alternative locations
    alt_test_runner = plugin_root / "skills" / "plugin-test-framework" / "templates" / "test-runner.py"

    issues = []
    passed_checks = []

    # Check 1: TEST-RESULTS.md exists
    if not test_results_path.exists():
        issues.append("TEST-RESULTS.md not found - run tests before deployment")
    else:
        content = test_results_path.read_text()

        # Check 2: Verify tests passed
        if "ALL TESTS PASSED" in content or "Status: PASSED" in content.upper():
            passed_checks.append("Tests passed")
        elif "FAILED" in content.upper():
            issues.append("TEST-RESULTS.md shows test failures - fix before deployment")
        else:
            issues.append("TEST-RESULTS.md status unclear - verify test results")

        # Check 3: Recent test execution
        date_match = re.search(r'\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})', content)
        if date_match:
            test_date_str = date_match.group(1)
            try:
                test_date = datetime.strptime(test_date_str, "%Y-%m-%d")
                now = datetime.now()
                age = now - test_date

                if age > timedelta(days=7):
                    issues.append(
                        f"Tests are {age.days} days old - re-run for deployment "
                        f"(max 7 days)"
                    )
                elif age > timedelta(days=1):
                    # Warning but not blocking
                    passed_checks.append(f"Tests run {age.days} days ago (consider re-running)")
                else:
                    passed_checks.append("Tests run recently")
            except ValueError:
                pass  # Could not parse date

    # Check 4: Test infrastructure exists
    has_test_runner = (
        test_runner_path.exists() or
        alt_test_runner.exists() or
        (plugin_root / "run-tests.sh").exists()
    )

    if has_test_runner:
        passed_checks.append("Test runner infrastructure present")
    else:
        issues.append("No test runner found (tests/test-runner.py or run-tests.sh)")

    # Check 5: E2E test infrastructure (MANDATORY per user decision)
    # Check for any e2e test related files
    e2e_files = list(plugin_root.rglob("*e2e*.py")) + list(plugin_root.rglob("*e2e*.sh"))
    has_e2e = len(e2e_files) > 0 or e2e_runner_path.exists()

    if has_e2e:
        passed_checks.append("E2E test infrastructure present")
    else:
        # This is an ERROR since user chose E2E as mandatory
        issues.append(
            "E2E test infrastructure not found - create tests/e2e-test-runner.py or e2e tests"
        )

    # Check 6: hooks.json has test hooks configured
    hooks_path = plugin_root / "hooks" / "hooks.json"
    if hooks_path.exists():
        try:
            hooks_data = json.loads(hooks_path.read_text())
            # Check if Stop hook has test enforcement
            stop_hooks = hooks_data.get("hooks", [])
            has_test_hook = any(
                "test" in str(h).lower() or "plugin-test" in str(h).lower()
                for h in stop_hooks
                if isinstance(h, dict) and h.get("hook_event_name") == "Stop"
            )
            if has_test_hook:
                passed_checks.append("Stop hook has test enforcement")
        except (json.JSONDecodeError, IOError):
            pass

    hint = get_skill_hint("W045")

    if issues:
        msg_parts = [
            "W045: Test bed validation incomplete - DEPLOYMENT BLOCKED",
            "",
            "Test bed testing is MANDATORY before deployment.",
            "All tests must pass within 7 days of deployment.",
            ""
        ]
        for issue in issues:
            msg_parts.append(f"  [X] {issue}")
        for passed in passed_checks:
            msg_parts.append(f"  [+] {passed}")
        msg_parts.extend([
            "",
            "To fix: Run /forge-editor:run-tests or python3 tests/test-runner.py"
        ])
        if hint:
            msg_parts.extend(["", hint])
        result.add_error("\n".join(msg_parts))
    else:
        for passed in passed_checks:
            result.add_pass(f"W045: {passed}")

    return result


def validate_form_selection(plugin_root: Path) -> ValidationResult:
    """
    W040: Check if form selection audit has been performed.

    This is a soft check that recommends running the form-selection-auditor
    agent for LLM-based deep analysis of component appropriateness.

    Checks for:
    - FORM-AUDIT.md existence (audit report)
    - Recent audit (within 30 days)
    - No critical issues in audit
    """
    from datetime import datetime, timedelta
    import re
    result = ValidationResult()

    audit_path = plugin_root / "FORM-AUDIT.md"

    # Count components for context
    agents = list((plugin_root / "agents").glob("*.md")) if (plugin_root / "agents").exists() else []
    skills = list((plugin_root / "skills").glob("*/SKILL.md")) if (plugin_root / "skills").exists() else []
    commands = list((plugin_root / "commands").glob("*.md")) if (plugin_root / "commands").exists() else []

    total_components = len(agents) + len(skills) + len(commands)

    if not audit_path.exists():
        # Only warn if there are significant components
        if total_components >= 5:
            hint = get_skill_hint("W040")
            msg_parts = [
                f"W040: Form selection audit recommended ({total_components} components)",
                "",
                "LLM-based analysis can verify each component uses the optimal form:",
                "  - Agent: multi-step, autonomous tasks",
                "  - Skill: reusable knowledge/guidelines",
                "  - Hook: event-driven enforcement",
                "  - Command: user-initiated actions",
                "",
                "To run audit:",
                '  Task(subagent_type="forge-editor:form-selection-auditor",'
                '       prompt="Audit form selection for this plugin")',
            ]
            if hint:
                msg_parts.extend(["", hint])
            result.add_warning("\n".join(msg_parts))
        else:
            result.add_pass(f"W040: Small plugin ({total_components} components) - audit optional")
    else:
        content = audit_path.read_text()

        # Check for critical issues
        wrong_count = content.lower().count("wrong")
        suboptimal_count = content.lower().count("suboptimal")

        if wrong_count > 0:
            result.add_warning(
                f"W040: Form audit found {wrong_count} WRONG form selection(s) - review FORM-AUDIT.md"
            )
        elif suboptimal_count > 2:
            result.add_warning(
                f"W040: Form audit found {suboptimal_count} suboptimal selections - consider refactoring"
            )
        else:
            result.add_pass("W040: Form selection audit completed")

        # Check audit age
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
        if date_match:
            try:
                audit_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                age = datetime.now() - audit_date
                if age > timedelta(days=30):
                    result.add_warning(
                        f"W040: Form audit is {age.days} days old - consider re-running"
                    )
            except ValueError:
                pass

    return result


def validate_connectivity(plugin_root: Path) -> ValidationResult:
    """
    W046: Validate component connectivity.

    Checks that all components are properly connected/referenced:
    - Commands referenced in wizard routes or documentation
    - Agents called via Task() somewhere
    - Skills loaded via Skill() somewhere
    - Route files reference current commands/skills
    """
    result = ValidationResult()

    # Collect all components
    commands_dir = plugin_root / "commands"
    agents_dir = plugin_root / "agents"
    skills_dir = plugin_root / "skills"

    commands = set()
    agents = set()
    skills = set()

    if commands_dir.exists():
        for f in commands_dir.glob("*.md"):
            commands.add(f.stem)

    if agents_dir.exists():
        for f in agents_dir.glob("*.md"):
            agents.add(f.stem)

    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                skills.add(d.name)

    # Search all markdown and python files for references
    all_content = ""
    search_paths = [
        plugin_root / "skills",
        plugin_root / "commands",
        plugin_root / "agents",
        plugin_root / "hooks",
    ]

    for search_path in search_paths:
        if search_path.exists():
            for f in search_path.rglob("*.md"):
                try:
                    all_content += f.read_text(errors='ignore') + "\n"
                except:
                    pass
            for f in search_path.rglob("*.py"):
                try:
                    all_content += f.read_text(errors='ignore') + "\n"
                except:
                    pass

    # Check command connectivity
    unreferenced_commands = []
    for cmd in commands:
        # Look for references like: /forge-editor:cmd, Skill("...cmd"), validate-full, etc.
        patterns = [
            f":{cmd}",           # /forge-editor:cmd
            f'"{cmd}"',          # "cmd"
            f"'{cmd}'",          # 'cmd'
            f"/{cmd}",           # /cmd
            cmd.replace("-", "_"),  # underscore variant
        ]
        found = any(p in all_content for p in patterns)
        if not found:
            unreferenced_commands.append(cmd)

    # Check agent connectivity
    unreferenced_agents = []
    for agent in agents:
        patterns = [
            f'subagent_type="forge-editor:{agent}"',
            f"subagent_type='forge-editor:{agent}'",
            f'subagent_type: "{agent}"',        # YAML with quotes
            f"subagent_type: '{agent}'",        # YAML with single quotes
            f"subagent_type: {agent}",          # YAML without quotes
            f"Task: {agent}",                   # Simple YAML task reference
            f'"{agent}"',
            f":{agent}",
            agent.replace("-", "_"),
        ]
        found = any(p in all_content for p in patterns)
        if not found:
            unreferenced_agents.append(agent)

    # Check skill connectivity
    unreferenced_skills = []
    for skill in skills:
        patterns = [
            f'Skill("forge-editor:{skill}"',
            f"Skill('forge-editor:{skill}'",
            f'"{skill}"',
            f":{skill}",
            f"/{skill}",
            f"skills: {skill}",                # Frontmatter single skill
            f"skills: [{skill}",               # Frontmatter array start
            f", {skill}",                      # Frontmatter array middle
            f"{skill},",                       # Frontmatter array item
            skill.replace("-", "_"),           # underscore variant
        ]
        found = any(p in all_content for p in patterns)
        if not found:
            unreferenced_skills.append(skill)

    # Report findings
    total_unreferenced = len(unreferenced_commands) + len(unreferenced_agents) + len(unreferenced_skills)

    if total_unreferenced > 0:
        details = []
        if unreferenced_commands:
            details.append(f"Commands: {', '.join(sorted(unreferenced_commands))}")
        if unreferenced_agents:
            details.append(f"Agents: {', '.join(sorted(unreferenced_agents))}")
        if unreferenced_skills:
            details.append(f"Skills: {', '.join(sorted(unreferenced_skills))}")

        result.add_warning(
            "\n".join([
                f"W046: {total_unreferenced} component(s) may not be connected/referenced",
                "",
                "Unreferenced components found:",
                *[f"  • {d}" for d in details],
                "",
                "These components exist but aren't referenced in routes, docs, or code.",
                "Either:",
                "  1. Add references in wizard routes or documentation",
                "  2. Remove if truly unused",
                "  3. Ignore if intentionally standalone",
            ])
        )
    else:
        result.add_pass(f"W046: All {len(commands) + len(agents) + len(skills)} components properly connected")

    return result


def apply_fixes(fixes: List[Fix], dry_run: bool = False) -> Tuple[int, int]:
    """Apply all fixes. Returns (success_count, fail_count)."""
    success = 0
    fail = 0

    print("\n" + "=" * 60)
    print("APPLYING FIXES" if not dry_run else "FIXES PREVIEW (dry-run)")
    print("=" * 60)

    for fix in fixes:
        print(f"\n{'[DRY-RUN] ' if dry_run else ''}→ {fix.description}")

        if dry_run:
            success += 1
        else:
            if fix.apply():
                print(f"  ✅ Done")
                success += 1
            else:
                fail += 1

    return success, fail


def main():
    # Parse arguments
    json_output = "--json" in sys.argv
    fix_mode = "--fix" in sys.argv
    dry_run = "--dry-run" in sys.argv
    quiet = "--quiet" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    plugin_root = Path(args[0]).resolve() if args else Path.cwd()

    # Find marketplace.json
    marketplace_path, legacy_warning = find_marketplace_json(plugin_root)
    if not marketplace_path:
        # Not a plugin project - skip validation silently (exit 0)
        # This allows the hook to run in any project without errors
        if json_output:
            print(json.dumps({"status": "skip", "message": "Not a plugin project"}))
        # Only show message if not in quiet mode and not a hook context
        elif not quiet:
            print("SKIP: No .claude-plugin/marketplace.json found (not a plugin project)")
        sys.exit(0)  # Graceful skip, not an error

    # Show legacy format warning (plugin.json found but not supported)
    if legacy_warning:
        if json_output:
            print(json.dumps({"status": "error", "message": legacy_warning}))
            sys.exit(1)
        else:
            print(f"\n{legacy_warning}\n")
            print("=" * 60)
            print("VALIDATION BLOCKED - Fix legacy format before proceeding")
            print("=" * 60)
            sys.exit(1)

    # Check for marketplace.json and plugin.json conflict
    # This causes "no context" error in Claude Code runtime
    claude_plugin_dir = plugin_root / ".claude-plugin"
    if claude_plugin_dir.exists():
        has_marketplace = (claude_plugin_dir / "marketplace.json").exists()
        has_plugin_json = (claude_plugin_dir / "plugin.json").exists()
        if has_marketplace and has_plugin_json:
            error_msg = (
                "CONFLICT: .claude-plugin/ contains both marketplace.json and plugin.json\n"
                "  This causes 'no context' error during plugin installation.\n"
                "  Solution: Remove plugin.json when using marketplace.json for distribution."
            )
            if json_output:
                print(json.dumps({"status": "error", "message": error_msg}))
            else:
                print(f"ERROR: {error_msg}")
            sys.exit(1)

    # Parse marketplace.json
    try:
        data = json.loads(marketplace_path.read_text())
    except json.JSONDecodeError as e:
        if json_output:
            print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
        else:
            print(f"ERROR: Invalid JSON in {marketplace_path}: {e}")
        sys.exit(1)

    # Get plugins
    plugins = data.get("plugins", [data])

    # Run all validations
    total_result = ValidationResult()

    # Settings.json validation
    total_result.merge(validate_settings_json())

    for i, plugin in enumerate(plugins):
        source = plugin.get("source", "./")
        if source in [".", "./"]:
            effective_root = plugin_root
        else:
            effective_root = plugin_root / source.lstrip("./")

        total_result.merge(validate_source_path(plugin, marketplace_path, i))
        total_result.merge(validate_registration(effective_root, plugin, marketplace_path))
        total_result.merge(validate_frontmatter_fields(effective_root))
        total_result.merge(validate_scripts(effective_root))
        total_result.merge(validate_hookify_compliance(effective_root))
        total_result.merge(validate_unnecessary_files(effective_root))
        total_result.merge(validate_language_preference(effective_root))
        total_result.merge(validate_emoji_usage(effective_root))
        total_result.merge(validate_test_coverage(effective_root))
        total_result.merge(validate_form_selection(effective_root))
        total_result.merge(validate_connectivity(effective_root))

    # Output results
    if json_output:
        output = {
            "status": "fail" if total_result.errors else ("warn" if total_result.warnings else "pass"),
            "errors": total_result.errors,
            "warnings": total_result.warnings,
            "passed": len(total_result.passed),
            "fixable": len(total_result.fixes)
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 60)
        print("PLUGIN VALIDATION")
        print("=" * 60)
        print(f"Plugin: {plugin_root}")
        print()

        if total_result.errors:
            print("ERRORS:")
            for e in total_result.errors:
                print(f"  ❌ {e}")
            print()

        if total_result.warnings:
            print("WARNINGS:")
            for w in total_result.warnings:
                print(f"  ⚠️  {w}")
            print()

        print("SUMMARY:")
        print(f"  Errors:   {len(total_result.errors)}")
        print(f"  Warnings: {len(total_result.warnings)}")
        print(f"  Passed:   {len(total_result.passed)}")
        print(f"  Fixable:  {len(total_result.fixes)}")
        print()

        if total_result.errors:
            print("STATUS: ❌ DEPLOYMENT WILL FAIL")
        elif total_result.warnings:
            print("STATUS: ⚠️  DEPLOYMENT MAY HAVE ISSUES")
        else:
            print("STATUS: ✅ READY FOR DEPLOYMENT")

    # Apply fixes if requested
    if fix_mode and total_result.fixes:
        success, fail = apply_fixes(total_result.fixes, dry_run)
        print(f"\nFixes applied: {success}, Failed: {fail}")

        if not dry_run and success > 0:
            print("\n💡 Re-run validation to verify fixes:")
            print(f"   python3 {sys.argv[0]}")
    elif fix_mode and not total_result.fixes:
        print("\n✨ Nothing to fix!")
    elif total_result.fixes and not json_output:
        print(f"\n💡 {len(total_result.fixes)} issues can be auto-fixed. Run with --fix:")
        print(f"   python3 {sys.argv[0]} --fix")
        print(f"   python3 {sys.argv[0]} --fix --dry-run  # Preview only")

    # Exit code
    # Only errors block (exit 1). Warnings are advisory (exit 0).
    # This prevents hooks from blocking tool use on warnings.
    if total_result.errors and not (fix_mode and not dry_run):
        sys.exit(1)
    else:
        sys.exit(0)  # Warnings don't block


if __name__ == "__main__":
    main()
