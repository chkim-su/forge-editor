# Orchestration Templates

Templates for forcing skill/agent activation via hooks.

## Why Orchestration Matters

```
Hook = 100% execution guarantee
Skill/Agent/MCP = ~20-80% (Claude's judgment)
```

## Template 1: Forced Evaluation (84% Success)

Forces Claude to evaluate and activate relevant skills.

### skill-rules.json

```json
{
  "skills": {
    "backend-dev": {
      "enforcement": "suggest",
      "promptTriggers": {
        "keywords": ["backend", "API", "controller", "service", "prisma"],
        "intentPatterns": ["(create|add|implement).*?(route|endpoint|API)"]
      }
    },
    "frontend-dev": {
      "enforcement": "suggest",
      "promptTriggers": {
        "keywords": ["frontend", "component", "react", "UI", "MUI"]
      }
    }
  }
}
```

### skill-activation.sh (UserPromptSubmit)

```bash
#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')
CWD=$(echo "$INPUT" | jq -r '.cwd')

MATCHED_SKILLS=()

# Load skill-rules.json if exists
RULES_FILE="$CWD/.claude/skill-rules.json"
if [ -f "$RULES_FILE" ]; then
    # Dynamic matching from rules
    for skill in $(jq -r '.skills | keys[]' "$RULES_FILE"); do
        keywords=$(jq -r ".skills[\"$skill\"].promptTriggers.keywords | join(\"|\")" "$RULES_FILE")
        if echo "$PROMPT" | grep -qiE "$keywords"; then
            MATCHED_SKILLS+=("$skill")
        fi
    done
else
    # Fallback static matching
    if echo "$PROMPT" | grep -qiE "backend|API|controller|service"; then
        MATCHED_SKILLS+=("backend-dev-guidelines")
    fi
    if echo "$PROMPT" | grep -qiE "frontend|component|react|UI"; then
        MATCHED_SKILLS+=("frontend-dev-guidelines")
    fi
fi

if [ ${#MATCHED_SKILLS[@]} -gt 0 ]; then
    cat << EOF
🎯 MANDATORY SKILL CHECK

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

## Template 2: Agent Router (100% with Plugin Agents)

Routes to specialized agents via Task tool.

### agent-router.sh (UserPromptSubmit)

```bash
#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Backend patterns → backend-dev agent
if echo "$PROMPT" | grep -qiE "backend|API|controller|service|prisma|database"; then
    cat << 'EOF'
🎯 MANDATORY AGENT DELEGATION

This task requires the **backend-dev** agent.
The agent has specialized skills pre-loaded.

ACTION REQUIRED:
Use Task tool with subagent_type="cipherpowers:code-agent"

DO NOT proceed without delegating to this agent.
EOF
    exit 0
fi

# Frontend patterns → frontend-dev agent
if echo "$PROMPT" | grep -qiE "frontend|component|react|vue|UI|CSS|styling"; then
    cat << 'EOF'
🎯 MANDATORY AGENT DELEGATION

This task requires the **frontend-dev** agent.

ACTION REQUIRED:
Use Task tool with subagent_type="frontend-dev"
EOF
    exit 0
fi

# Rust patterns → rust agent
if echo "$PROMPT" | grep -qiE "rust|cargo|crate|\.rs\b"; then
    cat << 'EOF'
🎯 MANDATORY AGENT DELEGATION

This task requires the **rust-agent** specialist.

ACTION REQUIRED:
Use Task tool with subagent_type="cipherpowers:rust-agent"
EOF
    exit 0
fi

exit 0
```

### ⚠️ Critical: Task Tool Limitation

```
┌───────────────────────────────────────────────────────────────┐
│  Task tool only recognizes plugin-registered agents           │
│  Local agents (.claude/agents/*.md) CANNOT be called via Task │
└───────────────────────────────────────────────────────────────┘
```

| Agent Type | Location | Task Tool |
|------------|----------|-----------|
| Plugin Agent | `.claude-plugin/agents/*.md` | ✅ Works |
| Local Agent | `.claude/agents/*.md` | ❌ Fails |

**Solution**: Use Template 1 (Forced Eval) if you don't have plugin agents.

## Template 3: Context Injection

Inject project context at session start.

### context-injector.sh (SessionStart)

```bash
#!/bin/bash
INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')

# Project-specific context
if [ -f "$CWD/.project-context.md" ]; then
    echo "📋 Project Context Loaded:"
    cat "$CWD/.project-context.md"
fi

# Tech stack detection
if [ -f "$CWD/package.json" ]; then
    echo ""
    echo "📦 Detected: Node.js project"
    if grep -q '"react"' "$CWD/package.json"; then
        echo "⚛️ Framework: React"
    fi
    if grep -q '"next"' "$CWD/package.json"; then
        echo "▲ Framework: Next.js"
    fi
fi

if [ -f "$CWD/Cargo.toml" ]; then
    echo ""
    echo "🦀 Detected: Rust project"
fi

exit 0
```

## Template 4: Domain Router (Combined)

Combines skill suggestion with agent delegation.

### domain-router.sh (UserPromptSubmit)

```bash
#!/bin/bash
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Determine domain
DOMAIN=""
if echo "$PROMPT" | grep -qiE "backend|API|database|prisma"; then
    DOMAIN="backend"
elif echo "$PROMPT" | grep -qiE "frontend|component|react|UI"; then
    DOMAIN="frontend"
elif echo "$PROMPT" | grep -qiE "test|spec|coverage"; then
    DOMAIN="testing"
elif echo "$PROMPT" | grep -qiE "deploy|docker|kubernetes|CI"; then
    DOMAIN="devops"
fi

if [ -n "$DOMAIN" ]; then
    cat << EOF
🎯 Domain Detected: **$DOMAIN**

REQUIRED ACTIONS:
1. Load the ${DOMAIN}-guidelines skill: Skill("${DOMAIN}-guidelines")
2. If complex task, delegate to ${DOMAIN}-dev agent

Proceed with skill/agent activation BEFORE implementation.
EOF
fi

exit 0
```

## Registration Examples

### Basic Setup (Forced Eval Only)

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/skill-activation.sh"
      }]
    }]
  }
}
```

### Full Setup (Context + Routing)

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/context-injector.sh"
      }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/domain-router.sh"
      }]
    }]
  }
}
```

## Success Rate Comparison

| Pattern | Success Rate | Complexity |
|---------|--------------|------------|
| Skill (default) | ~20% | Low |
| Forced Eval | **84%** | Medium |
| Agent Router (plugin) | **100%** | High |
| Combined Approach | **~90%** | Medium |
