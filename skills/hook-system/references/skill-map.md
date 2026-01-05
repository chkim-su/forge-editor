# Hook Skill Selection Guide

## Skill Mapping by Situation

### Learning / Understanding Phase

| Situation | Skill | File |
|-----------|-------|------|
| New to Hook system | hook-system | SKILL.md |
| Want to know available events | hook-capabilities | event-details.md |
| Want to know what's possible/impossible | hook-capabilities | SKILL.md (Can vs Cannot) |

### Implementation Phase

| Situation | Skill | File |
|-----------|-------|------|
| Block dangerous commands | hook-capabilities | patterns-detailed.md (Gate) |
| Auto-action after file changes | hook-capabilities | patterns-detailed.md (Side Effect) |
| Track session state | hook-capabilities | patterns-detailed.md (State) |
| Send Slack/Discord notifications | hook-capabilities | advanced-patterns.md |
| Auto-commit to Git | hook-capabilities | advanced-patterns.md |

### LLM Integration

| Situation | Skill | File |
|-----------|-------|------|
| Need AI evaluation in hooks | hook-sdk-integration | SKILL.md |
| Background LLM calls | hook-sdk-integration | background-agent.md |
| Cost optimization methods | hook-sdk-integration | cost-optimization.md |
| type: "prompt" vs SDK comparison | hook-sdk-integration | SKILL.md |

### Advanced Patterns

| Situation | Skill | File |
|-----------|-------|------|
| Force skill/agent activation | hook-capabilities | **orchestration-patterns.md** |
| Hook → Agent → Skill pattern | hook-capabilities | orchestration-patterns.md |
| Iteration Control | hook-capabilities | advanced-patterns.md |
| Promise Detection | hook-capabilities | advanced-patterns.md |
| Transcript Parsing | hook-capabilities | advanced-patterns.md |
| Workflow State Machine | workflow-state-patterns | SKILL.md |

### Templates / Quick Start

| Situation | Skill | File |
|-----------|-------|------|
| Need Gate Hook template | hook-templates | gate-patterns.md |
| Need Side Effect template | hook-templates | side-effect-patterns.md |

## Skill Relationship Diagram

```
hook-system (Entry Point)
    │
    ├─→ hook-capabilities (What: events, patterns, possibilities)
    │       │
    │       ├─→ event-details.md (10 event specs)
    │       ├─→ patterns-detailed.md (30 basic patterns)
    │       ├─→ orchestration-patterns.md (force skill/agent activation) ★ NEW
    │       ├─→ advanced-patterns.md (advanced combo patterns)
    │       └─→ real-world-examples.md (implementation examples)
    │
    ├─→ hook-sdk-integration (SDK/CLI LLM calls)
    │       │
    │       ├─→ sdk-patterns.md (u-llm-sdk usage)
    │       ├─→ background-agent.md (non-blocking execution)
    │       ├─→ cost-optimization.md (cost structure)
    │       └─→ real-world-projects.md (GitHub projects)
    │
    ├─→ hook-templates (Quick implementation templates)
    │
    └─→ workflow-state-patterns (State-based workflows)
```

## FAQ

### Q: Can hooks modify files?
**A**: Yes → hook-capabilities/patterns-detailed.md (PostToolUse)

### Q: Can hooks call external APIs?
**A**: Yes → hook-capabilities/advanced-patterns.md (External Integration)

### Q: Can hooks call Claude?
**A**: Yes → hook-sdk-integration (Background Agent recommended)

### Q: Does type: "prompt" hook incur costs?
**A**: Yes (subscription usage) → hook-sdk-integration/cost-optimization.md

### Q: Can I get session info via environment variables?
**A**: No (stdin JSON) → hook-capabilities/SKILL.md (Data Passing section)

### Q: How can I force skill activation reliably?
**A**: Use Forced Eval pattern (84%) or Hook → Agent → Skill (100%) → hook-capabilities/orchestration-patterns.md

### Q: Why doesn't Claude use my skill automatically?
**A**: Skills have ~20% activation rate by default (description matching only). Use hooks to force. → hook-capabilities/orchestration-patterns.md
