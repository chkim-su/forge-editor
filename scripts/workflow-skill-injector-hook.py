#!/usr/bin/env python3
"""
Workflow Phase Skill Auto-Injector Hook

Auto-injects relevant skills when entering workflow phases.
Prevents knowledge forgetting by loading phase-appropriate skills via additionalContext.

Triggered by:
- UserPromptSubmit: Check active workflow and inject skills
- PostToolUse (forge-state.py): Inject skills when phase transitions

State source: .claude/local/forge-state.json
"""

import sys
import json
import os
from pathlib import Path
from typing import Optional

# Workflow to phase-specific skills mapping
# Each workflow type maps to skills needed at different phases
WORKFLOW_SKILLS = {
    "skill_creation": {
        "intro": ["skill-design", "skill-catalog"],
        "design": ["skill-design", "orchestration-patterns"],
        "implement": ["hook-templates", "hook-sdk-integration"],
        "test": ["plugin-test-framework", "comprehensive-validation"],
        "publish": ["cleanup-guide"]
    },
    "agent_creation": {
        "intro": ["skill-catalog", "orchestration-patterns"],
        "design": ["orchestration-patterns", "critical-analysis-patterns"],
        "implement": ["hook-templates", "llm-sdk-guide"],
        "test": ["plugin-test-framework"],
        "publish": ["cleanup-guide"]
    },
    "command_creation": {
        "intro": ["skill-catalog"],
        "design": ["orchestration-patterns", "workflow-state-patterns"],
        "implement": ["hook-templates"],
        "test": ["plugin-test-framework"],
        "publish": ["cleanup-guide"]
    },
    "hook_design": {
        "intro": ["hook-capabilities", "hook-system"],
        "design": ["hook-templates", "hook-capabilities"],
        "implement": ["hook-sdk-integration", "llm-sdk-guide"],
        "test": ["plugin-test-framework", "workflow-enforcement"]
    },
    "mcp_integration": {
        "intro": ["mcp-gateway-patterns", "mcp-daemon-isolation"],
        "design": ["mcp-gateway-patterns", "orchestration-patterns"],
        "implement": ["mcp-daemon-isolation", "hook-sdk-integration"],
        "test": ["plugin-test-framework"]
    },
    "wizard_routing": {
        "context_analysis": ["critical-analysis-patterns"],
        "intent_classification": ["skill-catalog", "skill-activation-patterns"],
        "route_execution": []  # Route-specific skills loaded dynamically
    },
    "analyze_only": {
        "intro": ["comprehensive-validation", "critical-analysis-patterns"],
        "analyze": ["forge-analyzer", "skill-catalog"]
    },
    "quick_fix": {
        "intro": ["hook-templates", "skill-design"],
        "fix": ["comprehensive-validation"]
    },
    "plugin_publish": {
        "intro": ["cleanup-guide", "comprehensive-validation"],
        "validate": ["plugin-test-framework", "workflow-enforcement"],
        "publish": ["cleanup-guide"]
    }
}

# Phase aliases for normalization
PHASE_ALIASES = {
    "phase_1": "intro",
    "phase_2": "design",
    "phase_3": "implement",
    "phase_4": "test",
    "phase_5": "publish",
    "validation": "validate",
    "implementation": "implement",
    "testing": "test"
}


def get_plugin_root() -> Path:
    """Get plugin root directory."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)

    # Fallback: find from script location
    script_path = Path(__file__).resolve()
    return script_path.parent.parent


def get_state_path() -> Path:
    """Get forge-state.json path."""
    cwd = Path.cwd()
    git_dir = cwd
    while git_dir != git_dir.parent:
        if (git_dir / ".git").exists():
            return git_dir / ".claude" / "local" / "forge-state.json"
        git_dir = git_dir.parent
    return cwd / ".claude" / "local" / "forge-state.json"


def load_forge_state() -> dict:
    """Load current forge state."""
    state_path = get_state_path()
    if not state_path.exists():
        return {}
    try:
        with open(state_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def get_current_workflow(state: dict) -> Optional[str]:
    """Get current active workflow type."""
    return state.get("current_workflow")


def get_current_phase(state: dict) -> Optional[str]:
    """Get current workflow phase."""
    # Check wizard routing state
    wizard_state = state.get("wizard_routing", {})
    if wizard_state:
        phases = wizard_state.get("phases", {})
        for phase_name in ["context_analysis", "intent_classification", "route_execution"]:
            phase_data = phases.get(phase_name, {})
            if phase_data.get("status") == "in_progress":
                return phase_name
            if phase_data.get("status") == "pending":
                return phase_name  # Return first pending phase

    # Check general workflow phase
    return state.get("current_phase")


def normalize_phase(phase: str) -> str:
    """Normalize phase name using aliases."""
    return PHASE_ALIASES.get(phase.lower(), phase.lower())


def read_skill_content(skill_name: str) -> Optional[str]:
    """Read skill SKILL.md content."""
    plugin_root = get_plugin_root()
    skill_path = plugin_root / "skills" / skill_name / "SKILL.md"

    if not skill_path.exists():
        return None

    try:
        content = skill_path.read_text(encoding="utf-8")
        # Extract content after frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content
    except IOError:
        return None


def get_skills_for_workflow_phase(workflow: str, phase: str) -> list:
    """Get list of skills for a workflow phase."""
    workflow_skills = WORKFLOW_SKILLS.get(workflow, {})
    normalized_phase = normalize_phase(phase)

    # Try exact match first
    skills = workflow_skills.get(normalized_phase, [])

    # If no match, try intro as fallback
    if not skills and normalized_phase not in workflow_skills:
        skills = workflow_skills.get("intro", [])

    return skills


def build_skill_injection_context(skills: list) -> str:
    """Build additionalContext with skill content."""
    if not skills:
        return ""

    sections = []
    loaded_skills = []

    for skill_name in skills:
        content = read_skill_content(skill_name)
        if content:
            # Truncate if too long (max 2000 chars per skill)
            if len(content) > 2000:
                content = content[:1997] + "..."

            sections.append(f"## Skill: {skill_name}\n\n{content}")
            loaded_skills.append(skill_name)

    if not sections:
        return ""

    header = f"""
## Auto-Injected Skills (Workflow Phase Context)

The following skills have been automatically loaded for the current workflow phase.
Use this knowledge to complete your task effectively.

**Loaded Skills**: {', '.join(loaded_skills)}

---

"""
    return header + "\n\n---\n\n".join(sections)


def detect_workflow_from_input(user_input: str) -> Optional[tuple]:
    """Detect workflow and phase from user input patterns."""
    input_lower = user_input.lower()

    # Workflow detection patterns (English only - Korean handled by skill-activation-hook)
    patterns = {
        "skill_creation": ["skill", "create skill", "new skill", "make skill"],
        "agent_creation": ["agent", "subagent", "create agent", "new agent"],
        "command_creation": ["command", "workflow command", "create command"],
        "hook_design": ["hook", "guard", "enforce", "prevent", "create hook"],
        "mcp_integration": ["mcp", "gateway", "daemon", "isolation", "serena", "playwright"],
        "analyze_only": ["analyze", "review", "diagnose", "check", "validate"],
        "plugin_publish": ["publish", "deploy", "release", "marketplace"]
    }

    for workflow, keywords in patterns.items():
        if any(kw in input_lower for kw in keywords):
            return (workflow, "intro")

    return None


def handle_user_prompt_submit(input_data: dict):
    """Handle UserPromptSubmit - check for workflow context and inject skills."""
    user_input = input_data.get("user_input", "")

    # Load current state
    state = load_forge_state()

    # Get active workflow and phase
    workflow = get_current_workflow(state)
    phase = get_current_phase(state)

    # If no active workflow, try to detect from input
    if not workflow:
        detected = detect_workflow_from_input(user_input)
        if detected:
            workflow, phase = detected

    if not workflow:
        # No workflow context
        sys.exit(0)

    if not phase:
        phase = "intro"

    # Get skills for this workflow phase
    skills = get_skills_for_workflow_phase(workflow, phase)

    if not skills:
        sys.exit(0)

    # Build and output skill injection context
    injection_context = build_skill_injection_context(skills)

    if injection_context:
        print(json.dumps({"additionalContext": injection_context}))

    sys.exit(0)


def handle_post_tool_use(input_data: dict):
    """Handle PostToolUse - inject skills on phase transition."""
    tool_input = input_data.get("tool_input", {})
    tool_output = input_data.get("tool_output", "")
    tool_name = input_data.get("tool_name", "")

    # Only react to Bash calls that ran forge-state.py
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if "forge-state.py" not in command:
        sys.exit(0)

    # Check for phase transition commands
    phase_commands = ["wizard-context", "wizard-classify", "wizard-phase", "mark-phase"]
    if not any(cmd in command for cmd in phase_commands):
        sys.exit(0)

    # Load updated state
    state = load_forge_state()
    workflow = get_current_workflow(state)
    phase = get_current_phase(state)

    if not workflow or not phase:
        sys.exit(0)

    # Get skills for the new phase
    skills = get_skills_for_workflow_phase(workflow, phase)

    if not skills:
        sys.exit(0)

    # Build and output skill injection context
    injection_context = build_skill_injection_context(skills)

    if injection_context:
        # Add phase transition notice
        notice = f"""
## Phase Transition Detected

Workflow: **{workflow}**
New Phase: **{phase}**

Skills have been auto-injected for this phase.

"""
        print(json.dumps({"additionalContext": notice + injection_context}))

    sys.exit(0)


def main():
    """Main entry point."""
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    # Determine hook type from input structure
    if "user_input" in input_data:
        handle_user_prompt_submit(input_data)
    elif "tool_output" in input_data:
        handle_post_tool_use(input_data)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
