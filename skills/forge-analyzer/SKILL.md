---
name: forge-analyzer
description: Analyze vague user ideas and recommend architecture based on actual needs, not predefined categories. Front-end for clarifying ambiguous requests before routing to appropriate skillmaker tools.
allowed-tools: ["Read", "Grep", "Glob", "Task", "AskUserQuestion"]
---

# Forge Analyzer

Understands what users actually need, not what category their project fits into.

## Philosophy

> **"What problem are you solving?"** - not "Is this a skill or an agent?"

Architecture emerges from understanding, not from matching patterns to templates.

---

## When to Use

Invoke this skill when:
- User has a vague or ambiguous request
- Wizard cannot determine the right route from pattern matching
- User says things like "I want to make something that..." or "I'm not sure what I need"
- Need to clarify requirements before creating skill/agent/command

---

## Analysis Dimensions

Instead of categories, analyze along these dimensions:

### 1. State Complexity

| Question | Implication |
|----------|-------------|
| Does it need to remember across calls? | Persistent state needed |
| Is state shared between components? | Centralized management |
| Can it be stateless? | Simpler architecture |

### 2. Interaction Boundary

| Question | Implication |
|----------|-------------|
| Who initiates the interaction? | User → command/skill; System → hook/daemon |
| How long does interaction last? | One-shot → skill; Ongoing → agent/session |
| Does it need external systems? | External → MCP/API integration |

### 3. Context Requirements

| Question | Implication |
|----------|-------------|
| How much context does it need? | Large → isolated agent; Small → inline skill |
| Is context shareable? | Shareable → skill; Isolated → subagent |
| Does it build on previous context? | Building → session state; Fresh → stateless |

### 4. Execution Pattern

| Question | Implication |
|----------|-------------|
| Synchronous or async? | Sync → direct; Async → background/daemon |
| Single task or workflow? | Single → function; Workflow → orchestration |
| Needs human in the loop? | HITL → interactive; Autonomous → agent |

### 5. Integration Surface

| Question | Implication |
|----------|-------------|
| What triggers it? | User input → command; Tool use → hook; Time → cron |
| What does it produce? | Text → response; Files → write; Actions → tool calls |
| What does it consume? | Files → read; APIs → fetch; User → ask |

---

## Analysis Process

### Step 1: Gather Requirements

Ask open-ended questions:

```yaml
AskUserQuestion:
  question: "What problem does this solve for you?"
  header: "Problem"
  options:
    - label: "Automate repetitive task"
      description: "Something I do often that could be automatic"
    - label: "Enforce a rule"
      description: "Prevent mistakes or ensure quality"
    - label: "Provide information"
      description: "Answer questions or give guidance"
    - label: "Connect systems"
      description: "Bridge between different tools/services"
```

### Step 2: Map Dimensions

```
State:        [stateless] -------- [session] -------- [persistent]
Interaction:  [reactive] --------- [interactive] ---- [proactive]
Context:      [minimal] ---------- [moderate] ------- [extensive]
Execution:    [sync] ------------- [mixed] ---------- [async]
Integration:  [internal] --------- [hybrid] --------- [external]
```

### Step 3: Derive Architecture & Route to Wizard

| Pattern | Dimension Profile | Wizard Route |
|---------|------------------|--------------|
| **Skill (Knowledge)** | Stateless + Minimal context + Sync | SKILL → skill-architect |
| **Skill (Tool)** | State + Script needed + Sync | SKILL → skill-architect |
| **Agent** | Extensive context + Any execution | AGENT → skill-orchestrator-designer |
| **Hook** | Reactive + Rule enforcement + Sync | HOOK_DESIGN |
| **LLM Integration** | External + Async + API | LLM_INTEGRATION |
| **Workflow** | Multi-step + Mixed execution | COMMAND |
| **Hybrid** | Conflicting requirements | architecture-smith agent |

---

## Output Format

After analysis, recommend and route:

```markdown
## Forge Analysis Result

### Problem Understanding
{Summary of what the user needs}

### Dimension Analysis
- State: {spectrum position} - {reason}
- Interaction: {spectrum position} - {reason}
- Context: {spectrum position} - {reason}
- Execution: {spectrum position} - {reason}
- Integration: {spectrum position} - {reason}

### Recommended Architecture
{Specific recommendation}

### Next Step
Routing to: {Wizard route or agent}
```

---

## Integration with Wizard

After forge analysis completes:

| Architecture | Action |
|--------------|--------|
| Skill | Route to SKILL → `Task(subagent_type: "skill-architect")` |
| Agent | Route to AGENT → `Task(subagent_type: "skill-orchestrator-designer")` |
| Hook | Route to HOOK_DESIGN |
| Complex/Hybrid | `Task(subagent_type: "architecture-smith")` for deep analysis |

---

## Anti-Patterns

| Trap | Problem | Better Approach |
|------|---------|----------------|
| Category-first | "Is this a skill?" | "What does it need to do?" |
| Template-matching | "This looks like X" | "What are the actual requirements?" |
| Over-engineering | "Let's add flexibility" | "What's the minimum that works?" |
| Under-engineering | "Just make it simple" | "What complexity is unavoidable?" |
