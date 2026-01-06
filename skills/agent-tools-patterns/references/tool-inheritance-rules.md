# Tool Inheritance Rules

## How Claude Code Handles Agent Tools

According to Claude Code official documentation:

> "Omit the `tools` field to inherit all tools from the main thread (default), including MCP tools"

### Inheritance Mechanism

1. **No tools field** = Agent inherits ALL tools from parent context
   - Includes all Claude Code tools (Read, Write, Bash, etc.)
   - Includes all MCP tools (Serena, Playwright, etc.)
   - This is the default and recommended for most agents

2. **Empty array `tools: []`** = Agent has NO tool access
   - Cannot use any Claude Code tools
   - Cannot use any MCP tools
   - Agent can only generate text responses
   - Use only for pure reasoning/thinking agents

3. **Specific tools `tools: ["Read", "Grep"]`** = Only listed tools
   - Minimum privilege principle
   - MCP tools CANNOT be listed this way
   - Use for read-only or restricted agents

---

## Common Mistakes

### Mistake 1: Using `tools: []` for MCP agents

```yaml
# WRONG - Agent cannot use Serena MCP
---
name: serena-executor
description: Uses Serena MCP for code analysis
tools: []
---
```

```yaml
# CORRECT - Inherits all tools including MCP
---
name: serena-executor
description: Uses Serena MCP for code analysis
# tools field omitted = inherits all
---
```

### Mistake 2: Trying to list MCP tools

```yaml
# WRONG - MCP tools cannot be listed explicitly
---
name: browser-agent
tools: ["mcp__playwright__browser_click"]
---
```

```yaml
# CORRECT - Omit tools to inherit MCP tools
---
name: browser-agent
# tools field omitted = includes Playwright MCP
---
```

### Mistake 3: Forgetting to document `tools: []`

```yaml
# AMBIGUOUS - Is this intentional?
---
name: idea-generator
tools: []
---
```

```yaml
# CLEAR - Intent is documented
---
name: idea-generator
tools: []  # Intentional: pure reasoning agent
---
```

---

## Tool Categories

### Claude Code Native Tools
- Read, Write, Edit
- Bash
- Grep, Glob
- WebSearch, WebFetch
- Task, Skill
- AskUserQuestion
- TodoWrite

### MCP Tools (Examples)
- Serena MCP: find_symbol, replace_symbol_body, etc.
- Playwright MCP: browser_click, browser_type, etc.
- Context7 MCP: query-docs, resolve-library-id
- Firebase MCP: firebase_* tools

**Key**: MCP tools are inherited automatically; never list them explicitly.

---

## Decision Matrix

| Agent Type | Needs MCP | Needs Write | Needs Read | Config |
|------------|-----------|-------------|------------|--------|
| MCP Executor | Yes | Yes | Yes | Omit tools |
| Code Analyzer | Maybe | No | Yes | Omit tools or ["Read", "Grep"] |
| External Fetcher | No | No | No | ["WebSearch", "WebFetch"] |
| SDK Caller | No | No | No | ["Bash"] |
| Pure Thinker | No | No | No | tools: [] with comment |

---

## Validation

The `validate_all.py` script checks for:

1. **W049**: `tools: []` with description implying tool usage
   - CRITICAL: Agent is non-functional
   - Fix: Remove the tools line

2. **W050**: `tools: []` without clear intent
   - WARNING: Ambiguous configuration
   - Fix: Add comment or remove line
