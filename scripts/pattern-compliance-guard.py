#!/usr/bin/env python3
"""
Pattern Compliance Guard - Runtime enforcement for W033/W034 patterns.

Multi-hook enforcement that triggers on:
- Task: Alert when launching agents with pattern issues
- Write/Edit: Alert when creating/modifying agents/skills with issues
- Skill: Alert when loading skills with issues

This is a NOTIFICATION hook - it doesn't block, but ensures LLM awareness.
The goal is to force CONSIDERATION, not implementation.
"""

import json
import sys
import re
import os
from pathlib import Path


def find_plugin_root() -> Path:
    """Find the plugin root directory."""
    if 'CLAUDE_PLUGIN_ROOT' in os.environ:
        return Path(os.environ['CLAUDE_PLUGIN_ROOT'])

    current = Path(__file__).parent.parent
    for _ in range(5):
        if (current / ".claude-plugin" / "marketplace.json").exists():
            return current
        current = current.parent

    return Path(__file__).parent.parent


def check_content_patterns(content: str, file_type: str) -> list:
    """Check content for W033/W034 pattern issues."""
    issues = []

    # Parse frontmatter
    frontmatter_raw = {}
    body_content = content

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            fm_content = parts[1].strip()
            for line in fm_content.split('\n'):
                if ':' in line:
                    key = line.split(':')[0].strip()
                    value = ':'.join(line.split(':')[1:]).strip()
                    frontmatter_raw[key] = value
            body_content = parts[2]

    # W033: Skills declared but no Skill() usage (for agents/commands)
    if file_type in ['agent', 'command']:
        skill_call_patterns = [
            r'Skill\s*\(',
            r'Skill\s*tool',
            r'invoke.*skill',
            r'load.*skill',
            r'use.*Skill',
        ]
        has_skill_call = any(re.search(p, body_content, re.IGNORECASE) for p in skill_call_patterns)

        if 'skills' in frontmatter_raw and not has_skill_call:
            issues.append({
                'code': 'W033',
                'message': f'Declares skills [{frontmatter_raw["skills"]}] but no Skill() usage found',
                'action': 'Consider: Skill("plugin:skill-name") for explicit loading, or frontmatter is sufficient',
                'reference': 'Skill("forge-editor:orchestration-patterns") → "Skill Invocation Patterns" section'
            })

    # W034: Multi-stage workflow without per-stage skill loading
    stage_patterns = [
        r'#{1,3}\s*(Phase|Step|Stage|단계)\s*\d',
        r'#{1,3}\s*\d+\.\s',
        r'#{1,3}\s*(First|Second|Third|Fourth|Fifth)',
        r'#{1,3}\s*(처음|둘째|셋째|첫번째|두번째)',
    ]

    stage_count = sum(len(re.findall(p, content, re.IGNORECASE | re.MULTILINE)) for p in stage_patterns)

    if stage_count >= 3:
        skill_calls = len(re.findall(r'Skill\s*\(', content))
        if skill_calls < stage_count // 2:
            issues.append({
                'code': 'W034',
                'message': f'Multi-stage workflow ({stage_count} stages) with only {skill_calls} Skill() calls',
                'action': 'Consider: Per-stage skill loading for context isolation',
                'reference': 'Skill("forge-editor:workflow-state-patterns") → multi-phase workflow design'
            })

    # W029: Missing frontmatter (for skills)
    if file_type == 'skill':
        required = ['name', 'description']
        missing = [f for f in required if f not in frontmatter_raw]
        if missing:
            issues.append({
                'code': 'W029',
                'message': f'Missing frontmatter: {", ".join(missing)}',
                'action': 'Add frontmatter with name, description, allowed-tools',
                'reference': 'Skill("forge-editor:skill-design") → "SKILL.md Structure" section'
            })

    # W030: Missing frontmatter (for agents)
    if file_type == 'agent':
        required = ['name', 'description', 'tools']
        missing = [f for f in required if f not in frontmatter_raw]
        if missing:
            issues.append({
                'code': 'W030',
                'message': f'Missing frontmatter: {", ".join(missing)}',
                'action': 'Add frontmatter with name, description, tools, skills',
                'reference': 'Skill("forge-editor:orchestration-patterns") → "Agent Frontmatter" section'
            })

    return issues


def check_agent_file(agent_name: str, plugin_root: Path) -> list:
    """Check an agent file for pattern issues."""
    agents_dir = plugin_root / "agents"
    agent_file = agents_dir / f"{agent_name}.md"

    if not agent_file.exists():
        return []

    try:
        content = agent_file.read_text(encoding='utf-8')
        return check_content_patterns(content, 'agent')
    except Exception:
        return []


def check_skill_file(skill_name: str, plugin_root: Path) -> list:
    """Check a skill for pattern issues."""
    skills_dir = plugin_root / "skills"
    skill_dir = skills_dir / skill_name
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.exists():
        return []

    try:
        content = skill_file.read_text(encoding='utf-8')
        return check_content_patterns(content, 'skill')
    except Exception:
        return []


def detect_file_type(file_path: str) -> tuple:
    """Detect if a file path is an agent, skill, or command."""
    path = Path(file_path)

    if '/agents/' in file_path or '\\agents\\' in file_path:
        return 'agent', path.stem
    elif '/skills/' in file_path or '\\skills\\' in file_path:
        if path.name == 'SKILL.md':
            return 'skill', path.parent.name
        return 'skill_ref', path.stem
    elif '/commands/' in file_path or '\\commands\\' in file_path:
        return 'command', path.stem

    return None, None


def print_alert(context: str, name: str, issues: list):
    """Print a formatted alert."""
    if not issues:
        return

    print("")
    print("━" * 55)
    print("⚠️  PATTERN COMPLIANCE ALERT (고찰 필요)")
    print("━" * 55)
    print(f"  Context: {context}")
    print(f"  Target: {name}")
    print("")

    for issue in issues:
        print(f"  [{issue['code']}] {issue['message']}")
        print(f"         → {issue['action']}")
        if 'reference' in issue:
            print(f"         📚 {issue['reference']}")
        print("")

    print("  ℹ️  This is a notification to ensure awareness.")
    print("     Load the referenced skill for detailed guidance.")
    print("━" * 55)
    print("")


def handle_task(tool_input: dict, plugin_root: Path):
    """Handle Task tool - check agent being launched."""
    subagent_type = tool_input.get("subagent_type", "")
    if not subagent_type:
        return

    agent_name = subagent_type.split(':')[-1] if ':' in subagent_type else subagent_type
    issues = check_agent_file(agent_name, plugin_root)
    print_alert("Launching agent via Task", agent_name, issues)


def handle_skill(tool_input: dict, plugin_root: Path):
    """Handle Skill tool - check skill being loaded."""
    skill = tool_input.get("skill", "")
    if not skill:
        return

    skill_name = skill.split(':')[-1] if ':' in skill else skill
    issues = check_skill_file(skill_name, plugin_root)
    print_alert("Loading skill", skill_name, issues)


def handle_write_edit(tool_input: dict, plugin_root: Path):
    """Handle Write/Edit - check content being written."""
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    file_type, name = detect_file_type(file_path)
    if not file_type or file_type == 'skill_ref':
        return

    # For Write, check new_content or content
    content = tool_input.get("content", "") or tool_input.get("new_string", "")
    if not content:
        return

    issues = check_content_patterns(content, file_type)
    if issues:
        print_alert(f"Writing {file_type} file", name, issues)


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    plugin_root = find_plugin_root()

    if tool_name == "Task":
        handle_task(tool_input, plugin_root)
    elif tool_name == "Skill":
        handle_skill(tool_input, plugin_root)
    elif tool_name in ["Write", "Edit"]:
        handle_write_edit(tool_input, plugin_root)


if __name__ == "__main__":
    main()
