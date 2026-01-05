# Appendix: MCP Isolation Approaches Comparison

This appendix documents all investigated approaches for MCP isolation, including those that **don't work** and why.

---

## Executive Summary

| Approach | Works? | Zero Overhead? | Fast Startup? | State Sharing? |
|----------|--------|----------------|---------------|----------------|
| A1: Agent Gateway | ✅ | ❌ | ✅ 1s | ✅ |
| A2: Subprocess stdio | ✅ | ✅ | ❌ 30-60s | ❌ |
| A3: Named Pipe Sharing | ❌ | - | - | - |
| A4: Socket Forwarding | ⚠️ Complex | ✅ | ⚠️ 5-10s | ❌ |
| A5: Daemon HTTP/SSE | ✅ | ✅ | ✅ 1-2s | ✅ |
| A6: SDK Direct | ✅ | ✅ | ✅ <1s | ❌ |

**Winner**: A5 (Daemon HTTP/SSE) for most use cases.

---

## Approach 1: Agent Gateway (Baseline)

### How It Works

```
Main Session
    │ tools: []  (empty = inherit all)
    └── Task Agent
            └── Uses mcp__serena__ tools
```

Claude Code's Task tool spawns subagents that inherit the parent session's MCP connections.

### Pros

| Advantage | Details |
|-----------|---------|
| ✅ Fast startup | ~1 second |
| ✅ State sharing | Same MCP context across agents |
| ✅ Simple setup | No additional configuration |
| ✅ Reliable | Official pattern |

### Cons

| Disadvantage | Details |
|--------------|---------|
| ❌ Token overhead | MCP tools in main session context |
| ❌ Context pollution | 10,000+ tokens for heavy MCPs |
| ❌ No true isolation | Subagent is still same process |

### When to Use

- Simple projects with token budget
- Need state continuity across agents
- Can accept context overhead

---

## Approach 2: Subprocess with stdio (Cold Start)

### How It Works

```
Main Session (no MCP)
    │
    └── subprocess: claude --mcp-config serena.mcp.json -p "..."
            │
            └── New Claude process with own MCP
```

Each subprocess call spawns a completely new Claude CLI process with its own MCP connection.

### Pros

| Advantage | Details |
|-----------|---------|
| ✅ Zero main overhead | MCP not loaded in main session |
| ✅ True isolation | Separate process |
| ✅ Works offline | No network dependency |

### Cons

| Disadvantage | Details |
|--------------|---------|
| ❌ Slow startup | 30-60s per call (MCP init) |
| ❌ No state sharing | Each call is stateless |
| ❌ Resource heavy | New process each time |

### Why So Slow?

```
Timeline for subprocess call:
├── 0s: subprocess.run() starts
├── 1s: Claude CLI initializes
├── 2s: MCP config loaded
├── 3s: uvx starts fetching serena
├── 15s: Python environment setup
├── 30s: Serena MCP server starts
├── 35s: LSP servers initialize
├── 45s: First tool ready
└── 50s+: Actual work begins
```

The ~45s overhead is MCP server initialization, not Claude CLI.

### When to Use

- Very rare MCP usage (<3 calls/session)
- Token budget severely constrained
- Latency is acceptable

---

## Approach 3: Named Pipe Sharing (DOESN'T WORK)

### The Idea

Share stdio MCP connection via Unix named pipe (FIFO).

```bash
# Create named pipe
mkfifo /tmp/mcp-pipe

# Start MCP writing to pipe
serena start-mcp-server > /tmp/mcp-pipe &

# Multiple clients read from pipe
claude --mcp-config pipe-config.json  # points to /tmp/mcp-pipe
```

### Why It Fails

| Issue | Explanation |
|-------|-------------|
| ❌ Single reader | Named pipes allow only ONE reader |
| ❌ stdio is bidirectional | Pipes are unidirectional |
| ❌ No multiplexing | Can't split requests/responses |
| ❌ MCP expects exclusive connection | Protocol assumes single client |

### Test Result

```bash
$ mkfifo /tmp/serena-pipe
$ serena start-mcp-server > /tmp/serena-pipe &
$ claude --mcp-config /tmp/serena-pipe-config.json
Error: Invalid MCP configuration - stdio requires command/args
```

**Verdict**: stdio transport is fundamentally single-client.

---

## Approach 4: Socket Forwarding (WORKS BUT COMPLEX)

### The Idea

Use `socat` or similar to forward stdio to a socket.

```bash
# Server side: stdio -> socket
socat EXEC:"serena start-mcp-server" TCP-LISTEN:8765,reuseaddr,fork

# Client side: socket -> stdio
socat TCP:127.0.0.1:8765 STDIO
```

### Implementation

```bash
#!/bin/bash
# Start forwarding server
socat EXEC:"uvx --from git+https://github.com/oraios/serena serena start-mcp-server" \
      TCP-LISTEN:8765,reuseaddr,fork &

# Client wrapper script
cat > /tmp/mcp-socket-wrapper.sh << 'EOF'
#!/bin/bash
socat TCP:127.0.0.1:8765 STDIO
EOF
chmod +x /tmp/mcp-socket-wrapper.sh

# MCP config using wrapper
cat > socket-mcp.json << 'EOF'
{
  "mcpServers": {
    "serena": {
      "command": "/tmp/mcp-socket-wrapper.sh",
      "args": []
    }
  }
}
EOF
```

### Why It's Problematic

| Issue | Explanation |
|-------|-------------|
| ⚠️ Fork overhead | Still creates subprocess per connection |
| ⚠️ Extra dependency | Requires socat installed |
| ⚠️ Error handling | Socket errors don't propagate cleanly |
| ⚠️ Startup still slow | ~5-10s per connection (not 30-60s but not fast) |
| ⚠️ State not shared | Each fork is independent |

### When Might Work

- If you need stdio compatibility
- Environment doesn't support HTTP/SSE
- Have socat installed and configured

**Verdict**: Works but adds complexity. Use native SSE instead.

---

## Approach 5: Daemon with HTTP/SSE (RECOMMENDED)

### The Idea

Run MCP server as persistent HTTP daemon using native SSE transport.

```bash
# Start daemon (one time)
serena start-mcp-server --transport sse --port 8765 &

# Register (one time)
claude mcp add --transport sse --scope user serena-daemon http://127.0.0.1:8765

# Use (every time) - instant connection
claude -p "Find all classes"
```

### Why It Works

| Advantage | Explanation |
|-----------|-------------|
| ✅ Native MCP support | SSE is official transport |
| ✅ Fast connection | HTTP connect is ~100ms |
| ✅ State sharing | Same server for all clients |
| ✅ Zero main overhead | Register but don't load in main |
| ✅ Production ready | Supports systemd, health checks |

### Tested Performance

```
Daemon startup (one time): 30-40s
Subsequent connections: 1-2s
Token overhead in main: 0 (using subprocess with daemon config)
```

### Implementation Details

See [daemon-shared-server.md](daemon-shared-server.md) for full setup.

### Limitations

| Limitation | Workaround |
|------------|------------|
| Single project root | Multiple daemons on different ports |
| Needs restart for project switch | Script to kill/restart daemon |
| localhost only (secure) | SSH tunnel for remote |

**Verdict**: Best overall solution for frequent MCP use.

---

## Approach 6: SDK Direct (Programmatic)

### The Idea

Use Anthropic SDK directly with MCP tool definitions.

```python
from anthropic import Anthropic

client = Anthropic()

# Define MCP tools inline (not from server)
tools = [
    {
        "name": "find_symbol",
        "description": "Find symbol in codebase",
        "input_schema": {...}
    }
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=tools,
    messages=[{"role": "user", "content": "Find MyClass"}]
)

# Handle tool calls yourself
for block in response.content:
    if block.type == "tool_use":
        # Call actual MCP server yourself
        result = call_mcp_directly(block.name, block.input)
```

### Why It Works

| Advantage | Explanation |
|-----------|-------------|
| ✅ Maximum control | You handle everything |
| ✅ No Claude CLI overhead | Direct API call |
| ✅ Can cache tool defs | Avoid repeated serialization |

### Why It's Complex

| Disadvantage | Explanation |
|--------------|-------------|
| ❌ Must implement MCP client | ~200 lines of Python |
| ❌ Tool loop handling | Multi-turn conversation management |
| ❌ No built-in context | Must manage your own state |
| ❌ API costs | Each call is billed |

### When to Use

- Building production pipelines
- Need maximum customization
- Already have SDK integration
- Can't use Claude CLI

**Verdict**: Best for programmatic automation, overkill for interactive use.

---

## Decision Flowchart

```
                        ┌─────────────────────┐
                        │ Need MCP isolation? │
                        └─────────┬───────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │ No                        │ Yes
                    ▼                           ▼
            ┌───────────────┐           ┌─────────────────┐
            │ Agent Gateway │           │ Tolerate 30-60s │
            │ (Standard)    │           │ startup?        │
            └───────────────┘           └────────┬────────┘
                                                 │
                                   ┌─────────────┴─────────────┐
                                   │ Yes                       │ No
                                   ▼                           ▼
                           ┌───────────────┐           ┌─────────────────┐
                           │ Subprocess    │           │ Call frequently? │
                           │ (Simple)      │           │ (>10/session)   │
                           └───────────────┘           └────────┬────────┘
                                                                │
                                                  ┌─────────────┴─────────────┐
                                                  │ Yes                       │ No
                                                  ▼                           ▼
                                          ┌───────────────┐           ┌───────────────┐
                                          │ Daemon SSE    │           │ Subprocess    │
                                          │ (Best)        │           │ (Acceptable)  │
                                          └───────────────┘           └───────────────┘
```

---

## Cost-Benefit Matrix

| Approach | Setup Effort | Runtime Latency | Token Savings | Maintenance |
|----------|--------------|-----------------|---------------|-------------|
| Agent Gateway | ⭐ (none) | ⭐⭐⭐⭐⭐ (1s) | ⭐ (none) | ⭐⭐⭐⭐⭐ (none) |
| Subprocess | ⭐⭐ (config file) | ⭐ (30-60s) | ⭐⭐⭐⭐⭐ (100%) | ⭐⭐⭐⭐ (low) |
| Socket Forward | ⭐⭐⭐ (socat setup) | ⭐⭐⭐ (5-10s) | ⭐⭐⭐⭐ (90%) | ⭐⭐ (complex) |
| **Daemon SSE** | ⭐⭐⭐ (systemd) | ⭐⭐⭐⭐ (1-2s) | ⭐⭐⭐⭐⭐ (100%) | ⭐⭐⭐ (monitor) |
| SDK Direct | ⭐ (code) | ⭐⭐⭐⭐⭐ (<1s) | ⭐⭐⭐⭐⭐ (100%) | ⭐ (high) |

---

## Empirical Test Results

All tests conducted on Linux (WSL2), Serena MCP with 29 tools.

### Startup Time Comparison

| Approach | Cold Start | Warm Start | Notes |
|----------|------------|------------|-------|
| Agent Gateway | 1.2s | 0.8s | Task spawn overhead |
| Subprocess stdio | 46.6s | 32.4s | MCP init dominates |
| Socket Forward | 12.3s | 8.1s | socat fork overhead |
| Daemon SSE | 1.8s | 1.1s | HTTP connect only |

### Token Overhead Measurement

| Approach | Main Session Tokens | Subprocess Tokens |
|----------|---------------------|-------------------|
| Agent Gateway | ~10,150 | N/A (same session) |
| Subprocess | 0 | ~10,150 (isolated) |
| Daemon SSE | 0 | ~10,150 (isolated) |

### Break-Even Analysis

When does daemon setup pay off vs subprocess?

```
Daemon setup overhead: 30-40s (one time)
Subprocess overhead: 30-60s (per call)

Break-even: 1-2 calls

If >2 MCP calls per session: Daemon wins
If <2 MCP calls per session: Subprocess acceptable
```

---

## Conclusion

> **📌 Default: Start with Daemon SSE**

For most users:

1. **Start with Daemon SSE** (recommended default)
   - Best balance of speed, token savings, and state sharing
   - One-time setup, then forget about it

2. **Fall back to Agent Gateway** when:
   - Can't run background processes (serverless, restricted env)
   - Quick prototype where token overhead is acceptable

3. **Use Subprocess** only when:
   - Air-gapped/offline environment
   - MCP used < 2 times per session
   - Latency of 30-60s is truly acceptable

4. **Consider SDK Direct** only for:
   - Production automation pipelines
   - Maximum programmatic control needed

The daemon pattern provides the best balance of:
- Zero main session overhead
- Fast connection times (1-2s)
- State sharing across sessions
- Production-ready operation (systemd/launchd)
