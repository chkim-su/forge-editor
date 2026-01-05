# AGENT / COMMAND Routes

## AGENT Route

Create a subagent that uses skills with isolated context.

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
