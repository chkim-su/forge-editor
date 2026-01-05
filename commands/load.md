---
description: Load a specific skill by name
argument-hint: "<skill-name>"
allowed-tools: ["Read", "Glob", "Skill"]
---

# Load Skill

Load a specific skillmaker skill into context.

## Your Task

1. Parse skill name: `$ARGUMENTS`

2. If no argument, show available skills:
   ```
   Available skills:
   • skill-design
   • orchestration-patterns
   • mcp-gateway-patterns
   • hook-templates
   • hook-system
   • hook-capabilities
   • skill-activation-patterns
   • workflow-state-patterns
   • plugin-test-framework
   • critical-analysis-patterns
   
   Usage: /forge-editor:load <skill-name>
   ```

3. Validate skill exists:
   ```
   Glob("skills/$ARGUMENTS/SKILL.md")
   ```

4. If skill found, load it:
   ```
   Skill("forge-editor:$ARGUMENTS")
   ```

5. If skill not found, suggest closest match:
   ```
   ❌ Skill "$ARGUMENTS" not found.
   
   Did you mean:
   • skill-design
   • skill-activation-patterns
   
   Use /forge-editor:skills to see all available skills.
   ```

## Aliases

Support common abbreviations:
- `hook` → `hook-templates`
- `mcp` → `mcp-gateway-patterns`
- `workflow` → `workflow-state-patterns`
- `activation` → `skill-activation-patterns`
- `design` → `skill-design`
- `orchestration` → `orchestration-patterns`
