---
name: solution-router
description: "Guide for determining what type of solution to build based on user intent"
triggers:
  - "what should I build"
  - "how to approach"
  - "solution type"
  - "project structure"
  - "what kind of"
  - "which approach"
---

# Solution Type Router

High-level decision guidance for determining what KIND of solution fits your intent.

## Decision Tree

```
What is your goal?
│
├─ Extend Claude Code capabilities?
│  └─ **Plugin** → Collection of skills/agents/commands/hooks
│
├─ Standalone utility or automation?
│  └─ **Script** → Python/Bash executable
│
├─ Improve existing codebase?
│  └─ **Refactor** → Analyze → Design → Modify
│
├─ Add functionality to existing project?
│  └─ **Feature** → Integrate into current architecture
│
├─ Connect multiple systems?
│  └─ **Integration** → APIs, MCP servers, bridges
│
└─ Not sure yet?
   └─ **Analysis First** → Run /diagnose to understand
```

## Solution Type Comparison

| Type | When to Use | Output | Validation |
|------|-------------|--------|------------|
| **Plugin** | Extend Claude Code | plugin.json + components | Plugin schema |
| **Script** | One-off automation | .py or .sh file | Syntax + execution |
| **Refactor** | Improve existing code | Modified files | Tests pass |
| **Feature** | Add to existing project | New + modified files | Integration tests |
| **Integration** | Connect systems | APIs, configs | E2E tests |

## Solution Type Details

### Plugin
**Use when:** You want to extend Claude Code with new capabilities

**Components:**
- `plugin.json` - Plugin manifest
- `skills/` - Domain knowledge and guidance
- `agents/` - Autonomous task executors
- `commands/` - Slash commands for users
- `hooks/` - Event-driven automation

**Workflow:** Full Forge 5-phase workflow

### Script
**Use when:** You need a standalone utility

**Output:**
- Single executable file
- argparse for CLI interface
- Self-contained dependencies

**Workflow:** Design → Implement → Test

### Refactor
**Use when:** Existing code needs improvement

**Process:**
1. Analyze current state
2. Identify issues/patterns
3. Propose improvements
4. Execute changes (incremental)
5. Verify behavior preserved

**Workflow:** `/refactor` command or `forge:analysis-agent`

### Feature
**Use when:** Adding to an existing project

**Process:**
1. Understand existing architecture
2. Find integration points
3. Design feature to fit patterns
4. Implement following conventions
5. Add tests

**Workflow:** Standard development

### Integration
**Use when:** Connecting systems/services

**Components:**
- MCP servers
- API bridges
- Webhooks
- Data transformers

**Workflow:** Depends on scope

## Project Context Analysis

Before deciding solution type, analyze:

### 1. Existing Structure
```bash
# Check project type indicators
ls -la  # Look for package.json, setup.py, Cargo.toml, etc.
cat package.json  # Understand project type
```

### 2. Technology Stack
- What languages/frameworks?
- What patterns are established?
- What conventions exist?

### 3. Integration Points
- Where does new code connect?
- What APIs/interfaces exist?
- What events can be hooked?

### 4. Testing Strategy
- Existing test framework?
- How to verify changes?
- CI/CD pipeline?

## Quick Decision Guide

| User Says | Likely Solution |
|-----------|-----------------|
| "I want Claude to..." | Plugin |
| "Make a script that..." | Script |
| "Clean up this code..." | Refactor |
| "Add feature X to my app..." | Feature |
| "Connect my app to service Y..." | Integration |
| "I'm not sure what I need..." | Analysis First |

## Next Steps by Solution Type

### If Plugin:
```
Run /forge to start the 5-phase workflow
```

### If Script:
```
Describe the script purpose and I'll create it
```

### If Refactor:
```
Run /refactor or describe what needs improvement
```

### If Feature:
```
Describe the feature and target project
```

### If Integration:
```
Describe the systems to connect and data flow
```
