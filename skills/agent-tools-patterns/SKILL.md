---
name: agent-tools-patterns
description: Patterns for configuring agent tools correctly
allowed-tools: ["Read"]
---

# Agent Tools Configuration Patterns

## Core Principle

> **`tools: []` ≠ `tools` omission**

| Configuration | Meaning | Use Case |
|---------------|---------|----------|
| `tools` field **omitted** | Inherit ALL tools (including MCP) | Default, MCP-using agents |
| `tools: []` (empty array) | **NO tools** | Pure reasoning agents only |
| `tools: ["Read", "Grep"]` | Specific tools only | Minimum privilege |

---

## Decision Tree

```
Does agent need MCP tools (Serena, Playwright, etc.)?
├─ YES → OMIT tools field (inherit all)
└─ NO
    ├─ Needs specific Claude Code tools → tools: ["Read", "Grep", "Bash"]
    ├─ External access only → tools: ["WebSearch", "WebFetch"]
    └─ Pure thinking, no tools → tools: []  # Add comment!
```

---

## Pattern Catalog

### Pattern 1: MCP Tool Inheritance (Default)
**When**: Agent uses Serena MCP, Playwright MCP, or other MCP tools
**Config**: Omit tools field entirely
**Rationale**: MCP tools cannot be listed explicitly; they're inherited

```yaml
---
name: mcp-executor
description: Executes refactoring via Serena MCP
# tools field intentionally omitted - inherits all including MCP
---
```

### Pattern 2: Read-Only Analysis
**When**: Agent only analyzes, never modifies
**Config**: `tools: ["Read", "Grep", "Glob"]`
**Rationale**: Minimum privilege for safety

### Pattern 3: External Access Only
**When**: Agent fetches from external sources, no file access
**Config**: `tools: ["WebSearch", "WebFetch"]` or `tools: ["Bash"]`
**Rationale**: Restrict file system access

### Pattern 4: Pure Reasoning (Rare)
**When**: Agent only generates text, no tool use
**Config**: `tools: []` with comment
**Rationale**: Must be explicit and documented

```yaml
---
name: pure-thinker
description: Generates creative ideas without tool access
tools: []  # Intentional: pure reasoning agent
---
```

---

## Anti-patterns

| Anti-pattern | Problem | Fix |
|--------------|---------|-----|
| `tools: []` without comment | Unclear intent | Add comment or remove |
| `tools: []` with MCP description | Agent is broken | Remove tools line |
| Listing MCP tools explicitly | MCP tools can't be listed | Omit tools field |

---

## Validation Codes

| Code | Meaning | Action |
|------|---------|--------|
| W049 | `tools: []` but description implies tool usage | Remove tools line |
| W050 | `tools: []` without clear intent | Add comment or remove |

---

## Quick Reference

```
MCP agent → omit tools
Read-only → tools: ["Read", "Grep", "Glob"]
External → tools: ["WebSearch", "WebFetch"]
SDK only → tools: ["Bash"]
Thinking → tools: []  # Intentional
```
