---
description: Suggest relevant skills based on your current task or prompt
argument-hint: "<describe your task>"
allowed-tools: ["Read", "Glob"]
---

# Skill Suggestion

Analyze your task and recommend the most relevant skills.

## Your Task

1. Parse the user's task description: `$ARGUMENTS`

2. Load skill rules:
   ```
   Read(".claude/skills/skill-rules.json")
   ```

3. Match against keywords and patterns:

   | Skill | Keywords | Patterns |
   |-------|----------|----------|
   | skill-design | skill, create skill, 스킬 | (create\|make\|build).*skill |
   | orchestration-patterns | agent, subagent, 에이전트 | (create\|make).*agent |
   | mcp-gateway-patterns | mcp, gateway, serena | mcp.*gateway |
   | hook-templates | hook, trigger, 훅 | (pre\|post).*tool |
   | skill-activation-patterns | auto-activation, rules | auto.*(load\|activate) |
   | workflow-state-patterns | workflow, phase, gate | multi.*phase |

4. Detect complexity level:
   - **simple**: basic, 단순, 기본
   - **standard**: normal, 일반
   - **advanced**: complex, 고급, 복잡

5. Output recommendations:

```
═══════════════════════════════════════════════════════
💡 RECOMMENDED SKILLS FOR YOUR TASK
═══════════════════════════════════════════════════════

Task: "$ARGUMENTS"
Complexity: STANDARD

⚡ High Priority
  • skill-design - You're creating a new skill

💡 Medium Priority  
  • hook-templates - Consider adding activation hooks

📌 Optional
  • skill-activation-patterns - For auto-loading rules

═══════════════════════════════════════════════════════
Load with: Skill("forge-editor:<name>")
═══════════════════════════════════════════════════════
```

6. If no arguments provided, ask:
   ```
   What are you trying to build? Describe your task and I'll suggest relevant skills.
   ```
