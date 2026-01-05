---
name: mcp-daemon-isolation
description: Context isolation for query-type MCP tools (LSP, search, database) via external CLI. Use when MCP query results consume too many context tokens.
allowed-tools: ["Read", "Bash", "Grep", "Glob"]
---

# MCP Daemon Isolation for Query-Type MCPs

External CLI pattern for isolating **query-type MCP** tool results from main context.

## Query-Type MCP Definition

| Type | Examples | Characteristics |
|------|----------|-----------------|
| **Query-type** | Serena (LSP), Database, Search | Unpredictable result size, potentially thousands of tokens |
| **Action-type** | File write, Git, Deploy | Small results, success/failure focused |

**Identification criteria:** Tools with `find_*`, `search_*`, `get_*`, `list_*` patterns

---

## Problem

```
Claude Session
├── mcp__serena__find_symbol("UserService")
│   └── Result: 2,500 tokens (full JSON)    ← CONSUMED
└── Context budget: rapidly depleting
```

**Daemon isolates tool definitions** (~350 tokens × tools), but **results still consume context**.

---

## Solution: External CLI + Structured Extraction

```
Claude Session
├── Bash: serena-query find_symbol UserService
│   └── stdout: "• UserService [Class] @ src/user.py:42"
│       (~50 tokens)                      ← MINIMAL
└── Full result stored: /tmp/serena-result.json
```

**Key insight**: Claude IS the LLM. Structured extraction provides 95%+ token savings.

---

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Claude       │────▶│ serena-query     │────▶│ Serena       │
│ Session      │     │ (external CLI)   │     │ Daemon :8765 │
└──────────────┘     └──────────────────┘     └──────────────┘
     Bash (~50 tok)     SSE + MCP Protocol       29 tools
```

For protocol details: `Read("references/mcp-sse-protocol.md")`

---

## Structured Extractors

| Tool | Full JSON | Extracted Output | Savings |
|------|-----------|------------------|---------|
| `list_dir` | ~800 | `📁 Dirs(12): hooks... 📄 Files(11)` | 95% |
| `get_symbols_overview` | ~1,200 | `Class(2): Config... Function(5)` | 96% |
| `find_symbol` | ~2,000 | `• UserService [Class] @ src/user.py:42-98` | 97% |
| `search_for_pattern` | ~1,500 | `Matches(15) in 8 files` | 95% |

For formatter code: `Read("references/extractors-and-examples.md")`

---

## Usage

### Output Modes

```bash
serena-query find_symbol UserService                    # summary (default)
serena-query find_symbol UserService --mode location    # location only (for Read)
serena-query find_symbol UserService --mode full        # full JSON
```

### Basic Commands

```bash
serena-query list_dir .
serena-query get_symbols_overview src/main.py --depth 1
serena-query find_symbol UserService --path src/
serena-query search_for_pattern "class.*Service" --path src/
serena-query find_symbol UserService --output /tmp/result.json
```

---

## Optimal Workflow: Explore-Locate-Read

```
1. Explore (--mode summary)   ~25 tokens  "What symbols exist?"
2. Locate (--mode location)   ~15 tokens  "Where exactly is it?"
3. Read (Read tool)           actual size  Only needed code
```

| Scenario | stdio approach | daemon+Read | Savings |
|----------|----------------|-------------|---------|
| Class analysis | ~525 | ~240 | 54% |
| 11 function analysis | ~4,300 | ~665 | 85% |
| Large-scale search | ~10,000+ | ~500 | 95% |

For detailed examples: `Read("references/extractors-and-examples.md")`

---

## Installation

```bash
pip install httpx
cp scripts/serena-query ~/.local/bin/
chmod +x ~/.local/bin/serena-query
```

### Daemon Setup

```bash
uvx --from git+https://github.com/oraios/serena \
  serena start-mcp-server --transport sse --port 8765 --project-from-cwd
```

---

## Decision: Structured vs LLM Summarization

| Aspect | LLM Summarization | Structured Extraction |
|--------|-------------------|----------------------|
| Latency | +2-5 seconds | ~0ms |
| Cost | API call per query | Zero |
| Consistency | Variable | Deterministic |

Claude IS the LLM consuming the output - no need for additional summarization.

---

## Isolation Strategy Guide

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Single symbol edit | stdio | Immediate modification |
| Codebase exploration | daemon | Expect large results |
| Reference tracking | daemon + location | Only need locations |
| Refactoring planning | daemon + full | Full structure analysis |

---

## Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Received request before initialization" | Missing handshake | `initialize` → `notifications/initialized` → `tools/call` sequence |
| "Connection refused on 8765" | Daemon not running | `systemctl --user start serena-daemon` |
| "Empty result" | Structure mismatch | Save raw JSON with `--output` and verify |

---

## References

### Implementation
- [serena-query CLI](../../scripts/serena-query)
- [Implementation Details](references/serena-query-implementation.md)
- [v2 Design](references/serena-query-v2-design.md)

### Protocol & Examples
- [MCP-SSE Protocol](references/mcp-sse-protocol.md)
- [Extractors & Examples](references/extractors-and-examples.md)
- [Integration Guide](references/integration-guide.md)

### Related
- [MCP Gateway Patterns](../mcp-gateway-patterns/SKILL.md)
