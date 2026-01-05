# Subprocess Isolation Research Report

**Date**: 2024-12-28
**Version**: 1.0
**Status**: Verified

---

## Executive Summary

Subprocess isolation for MCP servers is **technically feasible and effective**, but comes with significant trade-offs. This report documents empirical findings from controlled experiments.

---

## Test Environment

| Component | Version/Details |
|-----------|-----------------|
| Claude Code | 1.0.40+ |
| MCP Server | Serena (29 tools) |
| Host OS | Linux (WSL2) |
| Test Type | Subprocess via `claude` CLI |

---

## Empirical Findings

### 1. Startup Overhead

| Metric | Value | Notes |
|--------|-------|-------|
| Cold start | **46.6s** | MCP server initialization |
| Warm start | ~30s | If uvx cache exists |
| Per-request | ~5-10s | After initial connection |

**Conclusion**: Subprocess startup is a significant cost. Not suitable for frequent calls.

---

### 2. Token Consumption Analysis

#### Subprocess Session (Isolated)
| Metric | Value |
|--------|-------|
| Input tokens (prompt only) | **3-4 tokens** |
| MCP overhead in subprocess | Included, but isolated |
| Main session overhead | **0 tokens** |

#### Main Session (MCP Loaded)
| MCP Server | Tools | Est. Token Overhead |
|------------|-------|---------------------|
| Serena | 29 | ~10,150 tokens |
| Playwright | 25 | ~6,250 tokens |
| Greptile | 12 | ~3,600 tokens |
| Context7 | 2 | ~400 tokens |

**Formula**: `overhead ≈ tool_count × 350 tokens`

**Conclusion**: Subprocess isolation saves **6,000-15,000 tokens** per session for heavy MCPs.

---

### 3. Information Flow Analysis

#### ✅ Data Transfer (VERIFIED)
```
Main Session → [JSON Request] → Subprocess → [JSON Response] → Main Session
```

- Complex data structures survive JSON serialization
- MCP results returned intact
- Tested with Serena's `find_symbol`, `list_dir`

#### ✅ State Isolation (VERIFIED)
```
Subprocess A ←×→ Subprocess B ←×→ Main Session
```

- Each subprocess has independent context
- No state leakage between processes
- LLM context doesn't persist across subprocess calls

#### ✅ Context Passing (VERIFIED)
```python
# Explicit context in prompt
prompt = f"""
Context from main session:
{json.dumps(context)}

Execute: {action}
"""
```

- Context must be explicitly passed in prompt
- No implicit sharing of conversation history
- Works reliably for structured data

---

### 4. Break-Even Analysis

| Usage Pattern | Recommendation |
|---------------|----------------|
| < 3 MCP calls/session | ✅ Use Subprocess |
| 3-10 MCP calls/session | ⚠️ Evaluate latency tolerance |
| > 10 MCP calls/session | ❌ Use Agent Gateway |

**Break-even formula**:
```
If (token_savings × cost_per_token) > (startup_time × time_cost)
   → Use Subprocess
Else
   → Use Agent Gateway
```

---

## Architecture Patterns

### Pattern A: Pure Subprocess Bridge

```
Main Session (no MCP)
    ↓
scripts/mcp_bridge.py
    ↓
subprocess: claude --mcp-config <config> -p <prompt>
    ↓
JSON response
```

**Best for**: Rare, expensive MCP operations (analysis, refactoring)

### Pattern B: Hybrid (Agent Gateway + Subprocess)

```
Main Session
    ├── Frequent ops → Agent Gateway (low latency)
    └── Heavy ops → Subprocess Bridge (zero overhead)
```

**Best for**: Mixed usage patterns

### Pattern C: Claude Only SDK Bridge

```python
from anthropic import Anthropic

def call_mcp_isolated(request):
    client = Anthropic()
    # Separate API call with MCP tools
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        tools=[mcp_tool_definitions],
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_response(response)
```

**Best for**: Programmatic integration, maximum control

---

## Decision Matrix

| Criteria | Agent Gateway | Subprocess | SDK Bridge |
|----------|---------------|------------|------------|
| Latency | ✅ Low (~1s) | ❌ High (30-60s) | ⚠️ Medium (5-10s) |
| Token overhead | ❌ Always present | ✅ Zero in main | ✅ Zero in main |
| State continuity | ✅ Maintained | ❌ Per-call | ❌ Per-call |
| Implementation | ⚠️ Agent config | ✅ Simple script | ⚠️ SDK setup |
| Use frequency | Frequent | Rare | Programmatic |

---

## Limitations & Caveats

### 1. Subprocess Startup Variance
- First call: 45-60s (MCP server + uvx download)
- Subsequent calls: 30-40s (uvx cached)
- No way to "pre-warm" subprocess

### 2. Context Size Limits
- Prompt + context must fit in single message
- Large context may need chunking
- No streaming in subprocess mode

### 3. Error Handling Complexity
- Subprocess errors need robust parsing
- Timeout handling critical
- Exit codes may not reflect MCP errors

### 4. Authentication
- Subprocess inherits environment variables
- API keys must be accessible
- No session token sharing

---

## Recommendations

### Use Subprocess Isolation When:
1. MCP has > 20 tools (> 7,000 token overhead)
2. Usage is < 3 times per session
3. Latency of 30-60s is acceptable
4. Token budget is constrained

### Use Agent Gateway When:
1. MCP is used frequently (> 10 times/session)
2. Low latency is required
3. State must persist across calls
4. MCP has < 10 tools

### Use SDK Bridge When:
1. Building automated pipelines
2. Need fine-grained control
3. Integrating with external systems
4. Custom error handling required

---

## Implementation Checklist

- [ ] Create dedicated MCP config file
- [ ] Pin MCP version (commit SHA)
- [ ] Implement timeout handling
- [ ] Add JSON response parsing
- [ ] Create error recovery logic
- [ ] Test cold/warm startup
- [ ] Validate data integrity
- [ ] Document context passing format

---

## Appendix: Test Scripts

- `subprocess-isolation-test.py`: Basic isolation verification
- `context-overhead-analysis.py`: Token measurement
- `information-flow-test.py`: Data transfer integrity

Results saved in `research/` directory.
