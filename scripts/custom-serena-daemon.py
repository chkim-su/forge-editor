#!/usr/bin/env python3
"""
Custom Serena MCP Daemon with Skillmaker-specific tools
Wraps original Serena with additional tools at daemon level
"""
import sys
import json
from pathlib import Path
from serena.mcp import SerenaMCPFactory

def main():
    # Create standard Serena MCP server
    factory = SerenaMCPFactory(
        context="desktop-app",  # or your preferred context
        project=None  # Will use --project-from-cwd behavior
    )

    mcp = factory.create_mcp_server(
        host="0.0.0.0",
        port=8765,
        modes=["interactive", "editing"]
    )

    # ===== Add custom tools at daemon level =====

    @mcp.tool()
    def analyze_skillmaker_plugin() -> str:
        """
        Analyze the current skillmaker plugin structure.
        Returns skill count, agent count, and validation status.
        """
        try:
            plugin_file = Path.cwd() / ".claude-plugin" / "marketplace.json"
            if not plugin_file.exists():
                return "Error: Not in a skillmaker plugin directory"

            with open(plugin_file) as f:
                data = json.load(f)

            skills = data.get("skills", [])
            agents = data.get("agents", [])

            return f"""Skillmaker Plugin Analysis:
- Skills: {len(skills)}
- Agents: {len(agents)}
- Plugin version: {data.get('version', 'unknown')}
- Skills list: {', '.join(s.get('name', '') for s in skills)}
"""
        except Exception as e:
            return f"Error analyzing plugin: {e}"

    @mcp.tool()
    def validate_skill_frontmatter(skill_path: str) -> str:
        """
        Validate skill frontmatter using skillmaker's validation rules.

        :param skill_path: Path to skill markdown file (e.g., "skills/wizard/SKILL.md")
        """
        # This would integrate with your existing validation script
        try:
            from subprocess import run, PIPE
            result = run(
                ["python", "scripts/validate_all.py"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True
            )
            return f"Validation output:\n{result.stdout}\n{result.stderr}"
        except Exception as e:
            return f"Error running validation: {e}"

    @mcp.tool()
    def get_skill_references(skill_name: str) -> str:
        """
        Get all reference documents for a specific skill.

        :param skill_name: Name of the skill (e.g., "wizard", "mcp-daemon-isolation")
        """
        try:
            refs_dir = Path.cwd() / "skills" / skill_name / "references"
            if not refs_dir.exists():
                return f"No references directory found for skill: {skill_name}"

            ref_files = list(refs_dir.glob("*.md"))
            return f"""References for {skill_name}:
Files: {len(ref_files)}
{chr(10).join(f'- {f.name}' for f in ref_files)}
"""
        except Exception as e:
            return f"Error: {e}"

    # ===== Run the MCP server =====
    print(f"Starting Custom Serena MCP Daemon with {len(mcp._tool_manager._tools)} tools", file=sys.stderr)
    print(f"Standard Serena tools + {3} custom skillmaker tools", file=sys.stderr)

    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
