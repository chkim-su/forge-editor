# AGENT / COMMAND Routes

## State Machine Integration

AGENT/COMMAND routes use the same workflow phases as SKILL:

```bash
# Initialize workflow if not active
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py init

# Connectivity phase
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py start-phase connectivity_planning
# After Step 0
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py pass-gate connectivity_planned
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py complete-phase connectivity_planning

# Creation phase
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py start-phase component_creation
# After agent creates component
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py pass-gate component_created
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py complete-phase component_creation
```

---

## AGENT Route

Create a subagent that uses skills with isolated context.

### Step 0: Connectivity Planning (BEFORE CREATION)

**CRITICAL**: Plan connections BEFORE creating the agent.

```yaml
AskUserQuestion:
  question: "How will this agent be spawned?"
  header: "Spawn"
  options:
    - label: "Via Task tool"
      description: "Task(subagent_type: 'plugin:agent-name')"
    - label: "Via wizard route"
      description: "Wizard routes to this agent"
    - label: "Via command"
      description: "Command spawns this agent"
    - label: "Via another agent"
      description: "Parent agent spawns this as child"
```

**REQUIRED Registrations:**

| Registration | Location | Action |
|--------------|----------|--------|
| plugin.json | agents[] | Add agent path |
| marketplace.json | agents[] | Add agent entry |

If "Via wizard route": Also update wizard/SKILL.md routing table.

**Document the connection plan before proceeding.**

### Step 1: Check for Skills

```bash
Glob .claude/skills/*/SKILL.md
```

If none: "No skills found. Create skill first?" → Yes: goto SKILL

### Step 2: Select Skills

```yaml
AskUserQuestion:
  question: "Which skills?"
  header: "Skills"
  multiSelect: true
  options: [discovered skills]
```

### Step 3: Load orchestration-patterns

```
Skill("forge-editor:orchestration-patterns")
```

### Step 4: Launch Agent

```
Task: skill-orchestrator-designer
Pass: selected_skills, description
```

### Step 5: Validation (MANDATORY)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json
```

Same handling as SKILL route.

### Step 6: Next Steps

```markdown
1. **로컬 등록**: `/wizard register`
2. **테스트**: Claude Code 재시작 → Task agent 테스트
3. **배포**: `/wizard publish`
```

---

## COMMAND Route

Create a workflow command that coordinates agents.

### Step 0: Connectivity Planning (BEFORE CREATION)

**CRITICAL**: Plan connections BEFORE creating the command.

**REQUIRED Registrations:**

| Registration | Location | Action |
|--------------|----------|--------|
| plugin.json | commands[] | Add command path |
| marketplace.json | commands[] | Add command entry |

The command will be invoked as: `/plugin:command-name`

**Document the connection plan before proceeding.**

### Step 1: Check for Agents

```bash
Glob .claude/agents/*.md
```

If none: "No agents found. Create agent first?" → Yes: goto AGENT

### Step 2: Select Agents

```yaml
AskUserQuestion:
  question: "Which agents?"
  header: "Agents"
  multiSelect: true
```

### Step 3: Select Flow

```yaml
AskUserQuestion:
  question: "Coordination?"
  header: "Flow"
  options:
    - label: "Sequential"
    - label: "Parallel"
    - label: "Conditional"
```

### Step 4: Create Command

Write to `.claude/commands/{name}.md` with selected agents and flow pattern.

### Step 5-6: Validation and Next Steps

Same as AGENT route.
