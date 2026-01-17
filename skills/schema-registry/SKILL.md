---
name: schema-registry
description: "Schema templates and validation rules for different solution types"
triggers:
  - "schema for"
  - "template for"
  - "structure for"
  - "validate schema"
  - "plugin schema"
  - "frontmatter"
---

# Schema Registry

Templates and validation rules for all solution types.

## Plugin Schemas

### plugin.json
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "skills": [
    {
      "name": "skill-name",
      "description": "Skill description for matching",
      "path": "skills/skill-name/SKILL.md"
    }
  ],
  "agents": [
    {
      "name": "agent-name",
      "description": "Use when... <example>...</example>",
      "path": "agents/agent-name.md"
    }
  ],
  "commands": [
    {
      "name": "command-name",
      "description": "What the command does",
      "path": "commands/command-name.md"
    }
  ],
  "hooks": "hooks/hooks.json"
}
```

**Validation Rules:**
- `name`: Required, lowercase, alphanumeric + hyphens
- `version`: Required, semver format
- `description`: Required, non-empty string
- Component paths: Must exist relative to plugin root
- `hooks`: If specified, file must exist

### marketplace.json (GitHub install)
```json
{
  "name": "my-marketplace",
  "owner": {
    "name": "Author Name",
    "url": "https://github.com/author"
  },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./",
      "skills": ["./skills/..."],
      "commands": ["./commands/..."],
      "agents": ["./agents/..."]
    }
  ]
}
```

**Validation Rules:**
- `name`: Required
- `owner.name`: Required
- `plugins[].name`: Required, unique
- `plugins[].source`: Required, valid path

### Agent Frontmatter
```yaml
---
name: my-agent
description: "Use when... <example>Context\\nuser: request\\nassistant: response</example>"
model: sonnet
tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
---
```

**Validation Rules:**
- `name`: Required, matches filename
- `description`: Required, should include `<example>` for triggering
- `model`: Optional, defaults to sonnet (options: haiku, sonnet, opus)
- `tools`: Optional, list of valid tool names

**Valid Tools:**
```
Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion,
WebFetch, WebSearch, TodoWrite, NotebookEdit, KillShell
```

### Skill Frontmatter
```yaml
---
name: my-skill
description: "This skill should be used when..."
triggers:
  - "keyword1"
  - "keyword2"
  - "phrase that triggers"
---
```

**Validation Rules:**
- `name`: Required, matches filename/folder
- `description`: Required, starts with "This skill should be used when"
- `triggers`: Required, list of 2+ trigger phrases

### Command Frontmatter
```yaml
---
name: my-command
description: "What this command does"
---
```

**Validation Rules:**
- `name`: Required, matches filename (without .md)
- `description`: Required

### hooks.json
```json
{
  "hooks": [
    {
      "event": "PreToolUse",
      "matcher": {
        "tool_name": "Write|Edit"
      },
      "hooks": [
        {
          "type": "command",
          "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py"
        }
      ]
    }
  ]
}
```

**Valid Events:**
- `PreToolUse` - Before tool execution (can block)
- `PostToolUse` - After tool execution
- `Stop` - Session ending
- `SubagentStop` - Subagent finishing
- `SessionStart` - Session beginning
- `SessionEnd` - Session cleanup
- `UserPromptSubmit` - User sends message
- `PreCompact` - Before context compaction
- `Notification` - External notification
- `PermissionRequest` - Tool permission requested

**Hook Types:**
- `command` - Execute shell command
- `prompt` - LLM-based hook

## Script Schemas

### Python Script Template
```python
#!/usr/bin/env python3
"""
Script: <name>
Purpose: <what it does>
Usage: python3 <name>.py [args]
"""
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Script description"
    )
    # Add arguments
    parser.add_argument("input", help="Input file or value")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("-v", "--verbose", action="store_true")
    
    args = parser.parse_args()
    
    # Implementation
    try:
        # ... logic ...
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Validation Rules:**
- Shebang line present
- Docstring with purpose/usage
- argparse for CLI
- Proper exit codes (0=success)

### Bash Script Template
```bash
#!/bin/bash
# Script: <name>
# Purpose: <what it does>
# Usage: ./<name>.sh [args]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
usage() {
    echo "Usage: $0 [options] <arg>"
    echo "Options:"
    echo "  -h, --help    Show this help"
    exit 1
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) usage ;;
            *) break ;;
        esac
        shift
    done
    
    # Implementation
    echo "Running..."
}

main "$@"
```

**Validation Rules:**
- Shebang line present
- `set -euo pipefail` for safety
- Usage function
- Proper quoting

## Integration Schemas

### MCP Server (.mcp.json)
```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["server.js"],
      "env": {
        "API_KEY": "${MY_API_KEY}"
      }
    }
  }
}
```

**Server Types:**
- `stdio` - Standard I/O (command + args)
- `sse` - Server-Sent Events (url)
- `http` - HTTP transport (url)

## Validation Logic

### Quick Validation Script
```python
#!/usr/bin/env python3
"""Validate solution against schema."""
import json
import yaml
import sys
from pathlib import Path

def validate_plugin(plugin_dir: Path) -> list[str]:
    """Validate plugin structure and schema."""
    errors = []
    
    # Check plugin.json
    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        errors.append("Missing plugin.json")
        return errors
    
    try:
        with open(plugin_json) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in plugin.json: {e}")
        return errors
    
    # Required fields
    for field in ["name", "version", "description"]:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")
    
    # Validate component paths
    for comp_type in ["skills", "agents", "commands"]:
        for comp in manifest.get(comp_type, []):
            path = plugin_dir / comp.get("path", "")
            if not path.exists():
                errors.append(f"{comp_type} path not found: {comp['path']}")
    
    # Validate hooks file
    if "hooks" in manifest:
        hooks_path = plugin_dir / manifest["hooks"]
        if not hooks_path.exists():
            errors.append(f"Hooks file not found: {manifest['hooks']}")
    
    return errors

def validate_frontmatter(file_path: Path) -> list[str]:
    """Validate YAML frontmatter in markdown file."""
    errors = []
    
    content = file_path.read_text()
    if not content.startswith("---"):
        errors.append("Missing YAML frontmatter")
        return errors
    
    # Extract frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("Invalid frontmatter format")
        return errors
    
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML: {e}")
        return errors
    
    # Check required fields
    if "name" not in fm:
        errors.append("Missing 'name' in frontmatter")
    if "description" not in fm:
        errors.append("Missing 'description' in frontmatter")
    
    return errors
```

## Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Missing plugin.json | No manifest | Create plugin.json with required fields |
| Path not found | Invalid component path | Check relative path in manifest |
| Invalid frontmatter | YAML syntax error | Fix YAML formatting |
| Missing triggers | Skill has no triggers | Add trigger phrases |
| Invalid tool name | Tool doesn't exist | Use valid tool from list |

## Schema Quick Reference

```
Plugin Structure:
├── plugin.json          # Manifest (required)
├── skills/
│   └── skill-name/
│       └── SKILL.md     # Frontmatter: name, description, triggers
├── agents/
│   └── agent-name.md    # Frontmatter: name, description, model, tools
├── commands/
│   └── command-name.md  # Frontmatter: name, description
└── hooks/
    └── hooks.json       # Events + matchers + hook handlers
```
