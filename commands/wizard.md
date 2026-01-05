---
description: Create skills, agents, or commands with smart routing
argument-hint: "describe what to create (e.g., 'API skill', 'database agent')"
allowed-tools: ["Read", "Write", "Bash", "Grep", "Glob", "Task", "Skill", "AskUserQuestion"]
---

# Wizard Command

**Load the wizard skill for smart routing and complexity-based skill loading.**

```
Skill("forge-editor:wizard")
```

## Routing

Based on input, wizard skill routes to:

| Input Pattern | Route | Reference |
|---------------|-------|-----------|
| init, new project, 새 프로젝트 | PROJECT_INIT | route-project-init.md |
| skill create, 스킬 만들 | SKILL | route-skill.md |
| convert, from code, 변환 | SKILL_FROM_CODE | route-skill.md |
| agent, 에이전트 | AGENT | route-agent-command.md |
| command, workflow | COMMAND | route-agent-command.md |
| analyze, 분석, review | ANALYZE | route-analyze.md |
| validate, check, 검증 | VALIDATE | route-validate.md |
| publish, deploy, 배포 | PUBLISH | route-publish.md |
| register, local, 등록 | LOCAL_REGISTER | route-publish.md |
| (empty) | MENU | Show options |

## Self-Enforcement (W028)

All MUST/CRITICAL keywords are hookified:
- `PreToolUse/PostToolUse → validate_all.py`
- `PostToolUse:Task → solution-synthesis-gate.py`

## Usage

```bash
/wizard                    # Show menu
/wizard skill              # Create skill
/wizard analyze            # Analyze project
/wizard validate           # Quick validation
/wizard publish            # Deploy to marketplace
```
