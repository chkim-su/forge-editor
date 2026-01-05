---
name: wizard
description: Smart routing wizard for creating skills, agents, commands with complexity-based skill loading
allowed-tools: ["Read", "Write", "Bash", "Grep", "Glob", "Task", "Skill", "AskUserQuestion"]
---

# Wizard Skill

Smart routing for plugin development with complexity-based skill loading.

## Self-Enforcement (W028 Compliance)

All MUST/CRITICAL keywords are hookified via `hooks/hooks.json`:
- `PreToolUse/PostToolUse → validate_all.py`
- `PostToolUse:Task → solution-synthesis-gate.py`

---

## Complexity Detection

| Level | Keywords | Skills to Load |
|-------|----------|----------------|
| **Simple** | simple, basic | skill-design |
| **Standard** | standard, normal | + orchestration-patterns, hook-templates |
| **Advanced** | advanced, complex, serena, mcp | ALL pattern skills |

If no keyword detected, ask:
```yaml
AskUserQuestion:
  question: "Select project complexity"
  header: "Complexity"
  options:
    - label: "Simple"
    - label: "Standard (Recommended)"
    - label: "Advanced"
```

---

## Routing

| Pattern | Route | Details |
|---------|-------|---------|
| `forge\|clarify\|idea\|vague\|unsure\|not sure` | FORGE | `Skill("forge-editor:forge-analyzer")` |
| `init\|new.*project` | PROJECT_INIT | `Read("references/route-project-init.md")` |
| `skill.*create` | SKILL | `Read("references/route-skill.md")` |
| `convert\|from.*code` | SKILL_FROM_CODE | `Read("references/route-skill.md")` |
| `agent\|subagent` | AGENT | `Read("references/route-agent-command.md")` |
| `command\|workflow` | COMMAND | `Read("references/route-agent-command.md")` |
| `analyze\|review` | ANALYZE | `Read("references/route-analyze.md")` |
| `validate\|check` | VALIDATE | `Read("references/route-validate.md")` |
| `publish\|deploy` | PUBLISH | `Read("references/route-publish.md")` |
| `register\|local` | LOCAL_REGISTER | `Read("references/route-publish.md")` |
| `llm\|sdk\|background.*agent` | LLM_INTEGRATION | `Read("references/route-llm-integration.md")` + `Skill("forge-editor:llm-sdk-guide")` |
| `hook.*design\|proper.*hook` | HOOK_DESIGN | `Read("references/route-hook-design.md")` |
| `skill-rules\|auto-activation\|trigger` | SKILL_RULES | `Read("references/route-skill-rules.md")` |
| `mcp\|gateway\|isolation\|serena\|playwright` | MCP | `Read("references/route-mcp.md")` |
| no match / ambiguous | **SEMANTIC** | See Semantic Routing below |

---

## Semantic Routing (Fallback)

When regex patterns fail to match, use LLM-based semantic classification:

### Step 1: Invoke Semantic Librarian

```
Task(
  subagent_type="forge-editor:semantic-librarian",
  prompt="MODE: ROUTE_CLASSIFICATION

Classify this user intent into ONE route. Output ONLY the route name.

Input: '{user_input}'

Routes: VALIDATE, SKILL, AGENT, COMMAND, ANALYZE, PUBLISH, MCP, HOOK_DESIGN, FORGE

Output format:
Route: {ROUTE_NAME}",
  model="haiku"
)
```

### Step 2: Route Mapping

The semantic-librarian will analyze intent and return one of:
- `VALIDATE` - validation, checking, verification intents
- `SKILL` - skill creation, design intents
- `AGENT` - agent creation, automation intents
- `ANALYZE` - analysis, review intents
- `PUBLISH` - deployment, publishing intents
- `FORGE` - unclear, needs clarification

### Step 3: Execute Route

Use the returned route to load the appropriate reference file.

### Example Flow

```
User: "현재 프로젝트 전체적 검증"
      ↓
Regex: No match
      ↓
Semantic: "validation intent detected" → VALIDATE
      ↓
Execute: Skill("forge-editor:validate-full")
```

---

## MENU

```yaml
AskUserQuestion:
  question: "What would you like to do?"
  header: "Action"
  options:
    - label: "Clarify Idea (Forge)"
      description: "I have a vague idea - help me figure out what I need"
    - label: "New Project"
      description: "Initialize new plugin/marketplace"
    - label: "Skill"
      description: "Create new skill"
    - label: "Agent"
      description: "Create subagent with skills"
    - label: "Command"
      description: "Create workflow command"
    - label: "Hook Design"
      description: "Design hook with proper skill selection"
    - label: "LLM Integration"
      description: "Direct LLM calls from hooks/agents"
    - label: "Skill Rules"
      description: "Configure auto-activation triggers"
    - label: "MCP Gateway"
      description: "Design MCP tool isolation for subagents"
    - label: "Analyze"
      description: "Validation + design principles"
    - label: "Validate"
      description: "Quick schema/path check"
    - label: "Publish"
      description: "Deploy to marketplace"
```

Route selection to corresponding reference file.

---

## Common Post-Action Steps

After any creation (SKILL, AGENT, COMMAND):

### Validation (MANDATORY)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json
```

- **status="fail"**: Show errors, ask for auto-fix
- **status="warn"**: Show warnings, allow proceed
- **status="pass"**: Continue to next steps

### Next Steps Template
```markdown
1. **Local Register**: `/wizard register`
2. **Test**: Restart Claude Code → Test functionality
3. **Publish**: `/wizard publish`
```

---

## References

Each route has detailed instructions:

| Route | Reference |
|-------|-----------|
| FORGE | `Skill("forge-editor:forge-analyzer")` or `Task(subagent_type: "architecture-smith")` |
| PROJECT_INIT | [route-project-init.md](references/route-project-init.md) |
| SKILL, SKILL_FROM_CODE | [route-skill.md](references/route-skill.md) |
| AGENT, COMMAND | [route-agent-command.md](references/route-agent-command.md) |
| ANALYZE | [route-analyze.md](references/route-analyze.md) |
| VALIDATE | [route-validate.md](references/route-validate.md) |
| PUBLISH, LOCAL_REGISTER | [route-publish.md](references/route-publish.md) |
| LLM_INTEGRATION | [route-llm-integration.md](references/route-llm-integration.md) |
| HOOK_DESIGN | [route-hook-design.md](references/route-hook-design.md) |
| SKILL_RULES | [route-skill-rules.md](references/route-skill-rules.md) |
| MCP | [route-mcp.md](references/route-mcp.md) |
