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

## Semantic Routing (MANDATORY Fallback)

When regex patterns fail to match, you **MUST** follow this procedure. Do NOT skip to MENU.

```
┌─────────────────────────────────────────────────────────────────┐
│  MANDATORY EXECUTION PATH (Hook-Enforced)                       │
│                                                                 │
│  Regex Fail → Context Analysis → Classification → Route/Q&A    │
│                                                                 │
│  Skipping directly to MENU is a ROUTING FAILURE.               │
│  A PreToolUse hook initializes wizard routing state.            │
│  A PostToolUse hook verifies phases were followed.              │
└─────────────────────────────────────────────────────────────────┘
```

### State Machine Integration (REQUIRED)

Each phase MUST be recorded via `forge-state.py`:

```bash
# Phase 1: After context analysis
python3 scripts/forge-state.py wizard-context "MCP,daemon,isolation" "Bridge MCP discussion" "true"

# Phase 2: After classification
python3 scripts/forge-state.py wizard-classify "MCP" "high"

# Phase 3: After route execution
python3 scripts/forge-state.py wizard-phase route_execution completed
```

**State Commands:**
| Command | Purpose |
|---------|---------|
| `wizard-context <keywords> <topics> <is_followup>` | Record context analysis |
| `wizard-classify <route> <confidence>` | Record intent classification |
| `wizard-phase <phase> <status>` | Update phase status |
| `wizard-status` | Check current state |
| `wizard-require <phase>` | Block if phase not complete |

### Step 0: Conversation Context Analysis (REQUIRED)

Before classifying the input, analyze the recent conversation for context clues:

```yaml
Context Extraction:
  topics: [recent discussion topics from conversation]
  keywords: [technical terms: MCP, skill, hook, agent, daemon, etc.]
  user_work: [what was the user working on?]
  is_followup: [does input reference previous discussion?]
```

**Context Keyword → Route Hints:**

| Context Keywords | Likely Route |
|------------------|--------------|
| MCP, daemon, isolation, gateway, serena, playwright | MCP |
| skill, knowledge, methodology | SKILL |
| agent, subagent, automation | AGENT |
| hook, guard, enforce, prevent | HOOK_DESIGN |
| validate, check, test, verify | VALIDATE |
| analyze, review, inspect | ANALYZE |
| publish, deploy, release | PUBLISH |

### Step 1: Intent Classification with Context

Combine input + context for classification:

```
Input: "{user_input}"
Context: {extracted_topics_and_keywords}

Classification Logic:
  IF context has strong signal (e.g., MCP keywords)
    AND input is ambiguous (e.g., "어떻게 생각해?", "what do you think?")
  THEN infer intent from context
```

### Step 2: Decision Tree

```
                    Input + Context
                         │
              ┌──────────┴──────────┐
              │                     │
        Context Clear?         No Context
              │                     │
         ┌────┴────┐           Route to FORGE
         │         │           (clarification needed)
    High Conf   Med Conf
         │         │
    Route to   Context-Aware
    inferred   Q&A (Step 3)
    route
```

### Step 3: Context-Aware Q&A

If medium confidence, ask with **context-based options** (NOT generic menu):

```yaml
# Example: After MCP discussion, user says "어떻게 생각해?"
AskUserQuestion:
  question: "어떤 도움이 필요하신가요?"
  header: "Clarify"
  options:
    - label: "MCP 패턴 조언"
      description: "이전 대화의 daemon/isolation 관련"
    - label: "새 컴포넌트 생성"
      description: "MCP gateway 스킬/에이전트 만들기"
    - label: "다른 주제"
      description: "MCP와 관련 없는 다른 작업"
```

**Options MUST reflect conversation context.** Generic menu is last resort only.

### Step 4: Route Execution

| Classification Result | Action |
|----------------------|--------|
| High confidence route | Execute route directly |
| User selects from Q&A | Execute selected route |
| "다른 주제" / No context | Route to FORGE for guided discovery |

### Step 5: Optional semantic-librarian for Complex Cases

For complex classification where manual context analysis is insufficient:

```
Task(
  subagent_type="forge-editor:semantic-librarian",
  prompt="MODE: ROUTE_CLASSIFICATION\nInput: '{user_input}'\nContext: {extracted_context}",
  model="haiku"
)
```

Use when multiple routes seem equally valid or input has complex requirements.

### Step 6: FORGE as Ultimate Fallback

If truly ambiguous with no context clues:

```
Skill("forge-editor:forge-analyzer")
```

FORGE handles ambiguous intents through dimensional analysis and guided questions.

### Example Flows

**Example 1: Context-Aware Routing**
```
Conversation: [User was discussing Bridge MCP Server patterns]
Input: "어떻게 생각해?"
      ↓
Context Analysis: keywords=[MCP, daemon, bridge, isolation]
      ↓
Classification: MCP-related opinion request (high confidence)
      ↓
Route: MCP → Read("references/route-mcp.md")
       OR Context-Aware Q&A about MCP options
```

**Example 2: No Context**
```
Conversation: [Fresh session, no prior context]
Input: "뭐 좀 만들어줘"
      ↓
Context Analysis: keywords=[], topics=[]
      ↓
Classification: Ambiguous, no context signal
      ↓
Route: FORGE → Skill("forge-editor:forge-analyzer")
```

**Example 3: Semantic Classification**
```
Input: "현재 프로젝트 전체적 검증"
      ↓
Context Analysis: keywords=[project, verification]
      ↓
Classification: VALIDATE intent (high confidence)
      ↓
Route: VALIDATE → Read("references/route-validate.md")
```

---

## MENU (Last Resort Only)

> **WARNING**: Only use this generic menu when:
> 1. User explicitly requests menu (`/wizard` with no args)
> 2. Semantic Routing completed but no context clues exist
> 3. FORGE analysis requests menu presentation
>
> **Prefer Context-Aware Q&A** from Semantic Routing Step 3 when conversation context exists.

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
