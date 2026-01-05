# Integration Guide

## Usage Contexts

### 1. Direct Claude Session

Use serena-query via Bash tool for context-efficient exploration:

```bash
# Quick structure overview
serena-query list_dir src/

# Find class definitions
serena-query find_symbol MyClass --path src/

# When details needed, save and read selectively
serena-query find_symbol ComplexClass --output /tmp/result.json
```

**Best Practice:** Start with summary output. Only read full JSON when you need specific details not in summary.

### 2. Agent Integration

Configure agents to use Bash tool instead of direct MCP:

```yaml
# agents/code-explorer.yml
---
name: code-explorer
description: Context-efficient codebase explorer
allowed-tools: ["Bash", "Read"]  # No MCP tools
---

# Code Explorer

Explore using serena-query for minimal context consumption:

## Workflow

1. **Directory scan:**
   ```bash
   serena-query list_dir . --recursive
   ```

2. **Symbol discovery:**
   ```bash
   serena-query get_symbols_overview target.py --depth 1
   ```

3. **Specific lookup:**
   ```bash
   serena-query find_symbol TargetClass
   ```

4. **Detail extraction (when needed):**
   ```bash
   serena-query find_symbol TargetClass --output /tmp/sym.json
   # Read file only for specific symbol bodies
   ```
```

### 3. Hook Integration

Use in pre-commit or validation hooks:

```bash
#!/bin/bash
# hooks/validate-symbols.sh

# Check for undefined references
result=$(serena-query search_for_pattern "TODO|FIXME" --path src/)
if [[ "$result" == *"Matches"* ]]; then
    echo "Warning: Found TODO/FIXME markers"
    echo "$result"
fi
```

### 4. Batch Operations

Process multiple queries efficiently:

```bash
#!/bin/bash
# scripts/analyze-module.sh

MODULE=$1
OUTPUT_DIR="/tmp/analysis"
mkdir -p "$OUTPUT_DIR"

# Parallel queries
serena-query list_dir "$MODULE" --output "$OUTPUT_DIR/structure.json" &
serena-query get_symbols_overview "$MODULE" --output "$OUTPUT_DIR/symbols.json" &
wait

# Summary to stdout
echo "=== $MODULE Analysis ==="
serena-query list_dir "$MODULE"
serena-query get_symbols_overview "$MODULE"
```

## Pattern: Incremental Detail Loading

Start broad, narrow when needed:

```
Level 1: serena-query list_dir .
         └─ See project structure (~100 tokens)

Level 2: serena-query get_symbols_overview src/services/
         └─ See what's in target directory (~150 tokens)

Level 3: serena-query find_symbol UserService
         └─ Get location info (~50 tokens)

Level 4: serena-query find_symbol UserService --output /tmp/sym.json
         cat /tmp/sym.json | jq '.result.content[0].text | fromjson | .[0].body'
         └─ Full body when specifically needed
```

**Total:** ~300 tokens for full exploration path
**Without isolation:** ~4,000+ tokens (all results in context)

## Pattern: Conditional Detail Fetch

```bash
# In agent or session:

# Quick check
result=$(serena-query find_symbol TargetMethod --path src/)

if echo "$result" | grep -q "No symbols found"; then
    # Search with pattern instead
    serena-query search_for_pattern "def target_" --path src/
else
    # Found it - details if complex
    if echo "$result" | grep -q "+[0-9]* more"; then
        # Multiple matches - save full list
        serena-query find_symbol TargetMethod --output /tmp/matches.json
    fi
fi
```

## Configuration

### Environment Variables

```bash
# Override daemon URL (default: localhost:8765)
export SERENA_DAEMON_URL="http://192.168.1.100:8765"

# Timeout override
export SERENA_TIMEOUT=120
```

### Project-Specific Aliases

```bash
# .bashrc or .zshrc
alias sq="serena-query"
alias sq-dir="serena-query list_dir"
alias sq-sym="serena-query get_symbols_overview"
alias sq-find="serena-query find_symbol"
alias sq-grep="serena-query search_for_pattern"
```

## Comparison: Direct MCP vs serena-query

| Scenario | Direct MCP | serena-query |
|----------|------------|--------------|
| List 10 files | ~400 tokens | ~80 tokens |
| Find 5 symbols | ~1,500 tokens | ~150 tokens |
| Pattern search (20 matches) | ~3,000 tokens | ~200 tokens |
| Full exploration cycle | ~8,000 tokens | ~600 tokens |

**Savings: 85-95% context reduction**

## When NOT to Use

Direct MCP is better when:
- You need full symbol bodies for immediate editing
- Single-shot operation (no exploration phase)
- Results are small (<200 tokens)
- You need real-time MCP features (watches, live reload)

serena-query is better when:
- Exploration phase with multiple queries
- Large result sets (symbols, pattern matches)
- Agent workflows with limited context budget
- Batch/scripted operations
