# MCP Route

Design MCP gateway for tool isolation in subagents.

## When to Use

- Subagent needs access to MCP tools (Serena, Playwright, etc.)
- Current approach fails: "MCP tool not available in subagent"
- Need to isolate MCP access from main conversation

## Step 1: Load MCP Patterns

```
Skill("forge-editor:mcp-gateway-patterns")
Skill("forge-editor:mcp-daemon-isolation")
```

## Step 2: Ask Integration Type

```yaml
AskUserQuestion:
  question: "What MCP server do you need?"
  header: "MCP Server"
  options:
    - label: "Serena (Code Analysis)"
      description: "Symbol-level code operations"
    - label: "Playwright (Browser)"
      description: "Web automation and testing"
    - label: "Custom MCP Server"
      description: "Other MCP server"
    - label: "Multiple Servers"
      description: "Combine multiple MCP servers"
```

## Step 3: Determine Isolation Strategy

```yaml
AskUserQuestion:
  question: "How should the MCP be accessed?"
  header: "Strategy"
  options:
    - label: "Agent Gateway (Recommended)"
      description: "Subagent with direct MCP access"
    - label: "Subprocess Gateway"
      description: "Separate process with stdin/stdout"
    - label: "Daemon SSE"
      description: "Shared daemon with SSE transport"
```

## Step 4: Launch Agent

```
Task: mcp-gateway-designer
Pass: mcp_server, isolation_strategy, use_case
```

The agent will:
1. Analyze the MCP server requirements
2. Determine optimal isolation pattern
3. Generate gateway implementation
4. Create necessary configuration files

## Step 5: Generated Artifacts

Depending on strategy:

**Agent Gateway:**
- `agents/{mcp}-gateway.md` - Gateway agent definition
- Usage: `Task(subagent_type="{mcp}-gateway", prompt="...")`

**Subprocess Gateway:**
- `scripts/{mcp}-gateway.py` - Subprocess handler
- `hooks/hooks.json` - Hook integration

**Daemon SSE:**
- `scripts/{mcp}-daemon.py` - Daemon process
- Configuration for SSE transport

## Step 6: Validation (MANDATORY)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json
```

## Step 7: Test Integration

```markdown
1. **Start daemon** (if SSE): `python3 scripts/{mcp}-daemon.py`
2. **Test gateway**: Launch agent with Task tool
3. **Verify isolation**: Check MCP tools work in subagent
```

---

## Common Patterns

### Serena Gateway (Most Common)

```yaml
Task:
  subagent_type: serena-gateway
  prompt: "Analyze symbol references for {function_name}"
```

### Playwright Gateway

```yaml
Task:
  subagent_type: playwright-gateway
  prompt: "Take screenshot of {url}"
```

### Combined Gateway

```yaml
Task:
  subagent_type: multi-mcp-gateway
  prompt: "Analyze code with Serena, then test in browser with Playwright"
```

## References

- [MCP Gateway Patterns](../../mcp-gateway-patterns/SKILL.md)
- [MCP Daemon Isolation](../../mcp-daemon-isolation/SKILL.md)
- [Orchestration Patterns](../../orchestration-patterns/SKILL.md)
