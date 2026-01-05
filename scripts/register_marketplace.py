#!/usr/bin/env python3
"""
Register items (skills, agents, commands) to marketplace.json.

Usage:
    python register_marketplace.py --items skill:my-skill agent:my-agent command:my-cmd
    python register_marketplace.py --path /path/to/project --items skill:my-skill

This script:
1. Reads the .claude-plugin/marketplace.json
2. Adds the specified items to the appropriate arrays
3. Saves the updated marketplace.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple


def parse_items(items: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """Parse item specifications into categorized lists.

    Format: type:name or type:path
    Examples:
        skill:my-skill
        agent:my-agent.md
        command:my-command.md
    """
    skills = []
    agents = []
    commands = []

    for item in items:
        if ":" not in item:
            print(f"Warning: Invalid item format '{item}', expected 'type:name'", file=sys.stderr)
            continue

        item_type, item_name = item.split(":", 1)
        item_type = item_type.lower().strip()
        item_name = item_name.strip()

        # Normalize paths
        if item_type == "skill":
            # Skills are directories, path format: ./skills/skill-name
            if not item_name.startswith("./"):
                item_name = f"./skills/{item_name}"
            # Remove trailing SKILL.md if present
            if item_name.endswith("/SKILL.md"):
                item_name = item_name[:-9]
            skills.append(item_name)
        elif item_type == "agent":
            # Agents are .md files, path format: ./agents/agent-name.md
            if not item_name.startswith("./"):
                item_name = f"./agents/{item_name}"
            if not item_name.endswith(".md"):
                item_name = f"{item_name}.md"
            agents.append(item_name)
        elif item_type == "command":
            # Commands are .md files, path format: ./commands/command-name.md
            if not item_name.startswith("./"):
                item_name = f"./commands/{item_name}"
            if not item_name.endswith(".md"):
                item_name = f"{item_name}.md"
            commands.append(item_name)
        else:
            print(f"Warning: Unknown item type '{item_type}'", file=sys.stderr)

    return skills, agents, commands


def read_marketplace(marketplace_path: Path) -> dict:
    """Read marketplace.json."""
    with open(marketplace_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_marketplace(data: dict, marketplace_path: Path) -> None:
    """Save marketplace.json."""
    with open(marketplace_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # Trailing newline


def register_items(
    marketplace_data: dict,
    skills: List[str],
    agents: List[str],
    commands: List[str]
) -> dict:
    """Register items to marketplace.json data."""
    changes = {
        "skills_added": [],
        "agents_added": [],
        "commands_added": [],
        "skills_skipped": [],
        "agents_skipped": [],
        "commands_skipped": []
    }

    # Get the first plugin (or create structure if needed)
    plugins = marketplace_data.get("plugins", [])
    if not plugins:
        plugins = [{"name": "default", "skills": [], "agents": [], "commands": []}]
        marketplace_data["plugins"] = plugins

    plugin = plugins[0]

    # Ensure arrays exist
    if "skills" not in plugin:
        plugin["skills"] = []
    if "agents" not in plugin:
        plugin["agents"] = []
    if "commands" not in plugin:
        plugin["commands"] = []

    # Add skills
    for skill in skills:
        if skill not in plugin["skills"]:
            plugin["skills"].append(skill)
            changes["skills_added"].append(skill)
        else:
            changes["skills_skipped"].append(skill)

    # Add agents
    for agent in agents:
        if agent not in plugin["agents"]:
            plugin["agents"].append(agent)
            changes["agents_added"].append(agent)
        else:
            changes["agents_skipped"].append(agent)

    # Add commands
    for command in commands:
        if command not in plugin["commands"]:
            plugin["commands"].append(command)
            changes["commands_added"].append(command)
        else:
            changes["commands_skipped"].append(command)

    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Register items to marketplace.json"
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Path to the plugin project directory (default: current directory)"
    )
    parser.add_argument(
        "--items",
        nargs="+",
        required=True,
        help="Items to register in format 'type:name' (e.g., skill:my-skill agent:my-agent)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON"
    )

    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    marketplace_path = project_path / ".claude-plugin" / "marketplace.json"

    # Validate
    if not marketplace_path.exists():
        error = f"Error: marketplace.json not found at {marketplace_path}"
        if args.json:
            print(json.dumps({"success": False, "error": error}))
        else:
            print(error, file=sys.stderr)
        sys.exit(1)

    # Parse items
    skills, agents, commands = parse_items(args.items)

    if not skills and not agents and not commands:
        error = "Error: No valid items specified"
        if args.json:
            print(json.dumps({"success": False, "error": error}))
        else:
            print(error, file=sys.stderr)
        sys.exit(1)

    # Read and update marketplace.json
    marketplace_data = read_marketplace(marketplace_path)
    changes = register_items(marketplace_data, skills, agents, commands)

    if args.dry_run:
        if args.json:
            print(json.dumps({
                "success": True,
                "dry_run": True,
                "changes": changes,
                "marketplace_preview": marketplace_data
            }, indent=2))
        else:
            print("Dry run - would make the following changes:")
            if changes["skills_added"]:
                print(f"  Skills to add: {', '.join(changes['skills_added'])}")
            if changes["agents_added"]:
                print(f"  Agents to add: {', '.join(changes['agents_added'])}")
            if changes["commands_added"]:
                print(f"  Commands to add: {', '.join(changes['commands_added'])}")
            if changes["skills_skipped"]:
                print(f"  Skills already registered: {', '.join(changes['skills_skipped'])}")
            if changes["agents_skipped"]:
                print(f"  Agents already registered: {', '.join(changes['agents_skipped'])}")
            if changes["commands_skipped"]:
                print(f"  Commands already registered: {', '.join(changes['commands_skipped'])}")
    else:
        save_marketplace(marketplace_data, marketplace_path)

        total_added = len(changes["skills_added"]) + len(changes["agents_added"]) + len(changes["commands_added"])

        if args.json:
            print(json.dumps({
                "success": True,
                "total_added": total_added,
                "changes": changes
            }, indent=2))
        else:
            print(f"Successfully registered {total_added} item(s) to marketplace.json")
            if changes["skills_added"]:
                print(f"  Skills: {', '.join(changes['skills_added'])}")
            if changes["agents_added"]:
                print(f"  Agents: {', '.join(changes['agents_added'])}")
            if changes["commands_added"]:
                print(f"  Commands: {', '.join(changes['commands_added'])}")
            if changes["skills_skipped"] or changes["agents_skipped"] or changes["commands_skipped"]:
                skipped = changes["skills_skipped"] + changes["agents_skipped"] + changes["commands_skipped"]
                print(f"  Skipped (already registered): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
