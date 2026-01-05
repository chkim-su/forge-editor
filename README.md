# Forge Editor

> Transform vague ideas into perfect skills and agents through dimensional analysis.

## Philosophy

**"What problem are you solving?"** - not "Is this a skill or an agent?"

Architecture emerges from understanding, not from matching patterns to templates.

## The Forge Approach

Instead of asking users to choose between skill/agent/hook/workflow, Forge Editor:

1. **Analyzes requirements** across 5 dimensions (State, Interaction, Context, Execution, Integration)
2. **Derives architecture** organically from the analysis
3. **Creates implementations** using explicit skill-based patterns

```
Vague Idea
    ↓
[Forge Analysis] - 5 dimensions
    ↓
Architecture Recommendation
    ↓
[Skill/Agent/Hook Creation]
    ↓
Working Implementation
```

## Commands

### `/forge-editor:wizard` - Smart Routing

Start here for any plugin development task.

```bash
/forge-editor:wizard              # Interactive menu
/forge-editor:wizard forge        # Clarify vague idea
/forge-editor:wizard skill        # Create new skill
/forge-editor:wizard agent        # Create subagent
```

### `/forge-editor:wizard forge` - Idea Clarification

When you're not sure what you need:

```bash
/forge-editor:wizard I want to automate something...
/forge-editor:wizard forge       # Explicit forge analysis
```

**Process:**
1. Ask open-ended questions about the problem
2. Map requirements to 5 dimensions
3. Derive appropriate architecture
4. Route to implementation tools

## Core Concepts

### 5-Dimension Analysis

| Dimension | Spectrum |
|-----------|----------|
| **State** | stateless ↔ session ↔ persistent |
| **Interaction** | reactive ↔ interactive ↔ proactive |
| **Context** | minimal ↔ moderate ↔ extensive |
| **Execution** | sync ↔ mixed ↔ async |
| **Integration** | internal ↔ hybrid ↔ external |

### Architecture Mapping

| Pattern | Dimension Profile |
|---------|------------------|
| **Inline Skill** | Stateless + Minimal context + Sync |
| **Subagent** | Extensive context + Any execution |
| **Hook** | Reactive + Rule enforcement + Sync |
| **Workflow** | Multi-step + Session state |
| **Background Daemon** | Proactive + Async + External |

## Features

- **17 Skills**: Pattern libraries and design guides
- **8 Commands**: Development workflow automation
- **13 Agents**: Specialized task handlers
- **Hooks**: Runtime validation and enforcement

## Installation

```bash
# Via marketplace
/install forge-editor@forge-editor-marketplace

# Local development
/install ./path/to/forge-editor
```

## Key Skills

| Skill | Purpose |
|-------|---------|
| `forge-analyzer` | Dimensional analysis for vague ideas |
| `skill-design` | Skill creation patterns |
| `orchestration-patterns` | Subagent architecture |
| `hook-templates` | Hook design patterns |
| `mcp-gateway-patterns` | MCP tool isolation |

## Key Agents

| Agent | Purpose |
|-------|---------|
| `architecture-smith` | Deep analysis for complex requirements |
| `skill-architect` | Skill creation with iterative questioning |
| `skill-orchestrator-designer` | Subagent design |
| `mcp-gateway-designer` | MCP isolation design |

## License

MIT
