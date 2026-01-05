---
description: List all available skills with categories and descriptions
argument-hint: "[category filter]"
allowed-tools: ["Read", "Glob"]
---

# Skills List

Show all available skills in this plugin.

## Your Task

1. Scan skills directory:
   ```
   Glob("skills/*/SKILL.md")
   ```

2. For each skill, extract:
   - Name (directory name)
   - Description (from SKILL.md frontmatter or first paragraph)
   - Type (from skill-rules.json if exists)

3. Display categorized list:

```
═══════════════════════════════════════════════════════
📚 SKILLMAKER AVAILABLE SKILLS
═══════════════════════════════════════════════════════

🎯 Core Skills
  • skill-design          - Create well-structured skills
  • orchestration-patterns - Agent and subagent patterns

🔧 Integration Skills  
  • mcp-gateway-patterns  - MCP server integration
  • mcp-daemon-isolation  - Daemon process patterns

🪝 Hook Skills
  • hook-system           - Hook fundamentals
  • hook-templates        - Ready-to-use hook patterns
  • hook-capabilities     - Advanced hook features

📋 Workflow Skills
  • workflow-state-patterns - Multi-phase workflows
  • skill-activation-patterns - Auto-activation rules

═══════════════════════════════════════════════════════
Usage: Skill("forge-editor:<name>") to load
═══════════════════════════════════════════════════════
```

4. If argument provided, filter by category or keyword:
   - `$ARGUMENTS` = "hook" → show only hook-related skills
   - `$ARGUMENTS` = "mcp" → show only MCP-related skills
