# Hook Orchestration Patterns

Patterns for forcing skill/agent activation via hooks.

## The Core Problem: Claude's Goal-Focused Behavior

```
Claude focuses on goal achievement → skips skill/agent checks → works directly

"Skills just sit there. You have to remember to use them."
— diet103 (GitHub, 7.6k stars)
```

**Why this happens**:
- No algorithmic routing (embeddings, classifiers)
- Pure LLM inference on description text
- Goal-oriented behavior bypasses "optional" resources

## Activation Reliability Stats

| Method | Success Rate | Source |
|--------|--------------|--------|
| **Hook** | **100%** | Event-based auto-execution |
| Skill + Forced Eval Hook | **84%** | Scott Spence (200+ tests) |
| Skill + Simple Hook | ~50% | "coin flip" |
| Skill (default) | **~20%** | Description matching only |
| Subagent | ~70-80% | Description quality dependent |
| MCP (all tools loaded) | **~13%** | Tool overload |
| MCP (Tool Search) | ~43% | Subset search |

**Key insight**: Hook is the ONLY 100% guaranteed mechanism.

## Pattern 1: Forced Evaluation (84% Success)

### skill-rules.json Structure

```json
{
  "description": "Skill activation triggers",
  "skills": {
    "backend-dev-guidelines": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",

      "promptTriggers": {
        "keywords": ["backend", "API", "controller", "service"],
        "intentPatterns": [
          "(create|add|implement).*?(route|endpoint|API)",
          "(fix|debug).*?(error|exception)"
        ]
      },

      "fileTriggers": {
        "pathPatterns": ["services/**/*.ts", "controllers/**/*.ts"],
        "contentPatterns": ["import.*Prisma"]
      }
    }
  }
}
```

### Forced Eval Hook (UserPromptSubmit)

```bash
#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

MATCHED_SKILLS=()

if echo "$PROMPT" | grep -qiE "backend|API|controller|service"; then
  MATCHED_SKILLS+=("backend-dev-guidelines")
fi

if [ ${#MATCHED_SKILLS[@]} -gt 0 ]; then
  cat << EOF
MANDATORY SKILL CHECK

Step 1 - EVALUATE: For each skill, state YES/NO with reason
Step 2 - ACTIVATE: Use Skill() tool NOW
Step 3 - IMPLEMENT: Only after activation

Relevant skills:
$(for s in "${MATCHED_SKILLS[@]}"; do echo "- $s"; done)

CRITICAL: Evaluation is WORTHLESS unless you ACTIVATE.
EOF
fi
exit 0
```

**Why 84%**: Writing "YES - need this" creates commitment → compels activation.

### Enforcement Levels

| Level | Behavior | Use Case |
|-------|----------|----------|
| **suggest** | Recommend skill usage | General guidelines |
| **block** | Block action + require skill | Required rules/security |

## Pattern 2: Hook → Agent → Skill (100% Success)

Use Agent as skill "container":
- Hook forces Agent invocation
- Agent's `skills` field guarantees skill loading
- Context isolation + cost savings

### Architecture

```
UserPromptSubmit Hook
    │
    └─→ stdout: "MANDATORY: Use [agent-name] agent"
                              ↓
Claude Main
    │
    └─→ Task(subagent_type="backend-dev", prompt="...")
                              ↓
Subagent (backend-dev)
    ├── skills: backend-dev-guidelines ✅ Auto-loaded
    ├── tools: Restricted set
    ├── model: haiku (cost savings)
    └── Isolated context
```

### Agent Router Hook

```bash
#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

if echo "$PROMPT" | grep -qiE "backend|API|controller|service|prisma"; then
  cat << 'EOF'
MANDATORY AGENT DELEGATION

This task requires the **backend-dev** agent.
The agent has specialized skills pre-loaded.

ACTION REQUIRED:
Use Task tool with subagent_type="backend-dev"

DO NOT proceed without delegating to this agent.
EOF
fi
exit 0
```

### Agent Definition (.claude/agents/backend-dev.md)

```yaml
---
name: backend-dev
description: Use PROACTIVELY for backend - APIs, controllers, services
skills: backend-dev-guidelines
tools: Read, Edit, Bash, Grep, Glob
model: sonnet
---

You are a backend development specialist.

RULES:
1. Always follow the loaded backend-dev-guidelines skill
2. Use repository pattern for database access
3. Include proper error handling with Sentry
4. Write tests for new functionality
```

### Comparison

| Method | Context | Skill Load | Cost | Isolation |
|--------|---------|------------|------|-----------|
| Hook → Skill (Forced Eval) | Shared | 84% | Same | ❌ |
| Hook → Agent → Skill | Isolated | **100%** | Reduced | ✅ |

### ⚠️ Critical Limitation: Task Tool and Agent Types

```
┌───────────────────────────────────────────────────────────────┐
│  Task tool only recognizes plugin-registered agents           │
│  Local agents (.claude/agents/*.md) CANNOT be called via Task │
└───────────────────────────────────────────────────────────────┘
```

| Agent Type | Definition Location | Task Tool | Invocation Method |
|------------|--------------------|-----------|--------------------|
| **Plugin Agent** | `.claude-plugin/agents/*.md` | ✅ Works | `Task(subagent_type="name")` |
| **Local Agent** | `.claude/agents/*.md` | ❌ Fails | `/agents` or Claude's judgment |

**Actual Behavior**:
```python
# When hook outputs "Use backend-dev agent"
if "backend-dev" in plugin_registered_agents:
    # Task(subagent_type="backend-dev") works
else:
    # Task tool doesn't recognize → error or ignored
```

**Solutions**:
1. Register agent as plugin (`.claude-plugin/agents/`)
2. Or use Hook → Skill pattern (Forced Eval) directly

### Agent `skills` Field Behavior

**Works for**:
- Local agents (`.claude/agents/*.md`) - 100% skill loading guaranteed
- Plugin agents - via `skills` frontmatter field

**Does NOT guarantee invocation**:
- The `skills` field ensures loading when agent runs
- But agent invocation itself still depends on Claude's judgment (unless forced via Hook)

## Selection Guide

| Situation | Recommended |
|-----------|-------------|
| Simple project | Hook → Skill (Forced Eval) |
| Large project | Hook → Agent → Skill |
| Cost optimization | Agent (model: haiku) |
| Context isolation needed | Agent |
| External API connection | MCP |
| Auto-validation | Hook (PostToolUse) |
| Required rules enforcement | Hook (block) |

## References

- [diet103/claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase)
- [Scott Spence - How to Make Claude Code Skills Activate Reliably](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably)
- [Anthropic - Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
