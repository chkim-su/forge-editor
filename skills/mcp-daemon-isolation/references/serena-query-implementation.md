# serena-query Implementation Reference

## Core Components

### 1. MCP-SSE Client

Async HTTP client managing SSE connection lifecycle:

```python
async def call_serena(tool: str, params: dict, timeout: float = 60.0) -> dict:
    """
    State machine for MCP-SSE protocol:

    States:
    1. CONNECTING: Waiting for session_id from SSE stream
    2. INITIALIZING: Sent initialize, waiting for response
    3. READY: Sent notifications/initialized, can call tools
    4. WAITING: Sent tool call, waiting for result
    5. DONE: Result received, connection closed
    """

    base_url = "http://localhost:8765"
    session_id = None
    initialized = False
    tool_sent = False
    msg_id = 0

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("GET", f"{base_url}/sse") as sse:
            async for line in sse.aiter_lines():
                # State transitions happen here...
```

### 2. Content Extraction

MCP responses are nested JSON-RPC:

```python
def extract_content(data: dict) -> Any:
    """
    Response structure:
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "content": [
          {"type": "text", "text": "{...json string...}"}
        ]
      }
    }
    """
    result = data.get("result", {})
    text = result.get("content", [{}])[0].get("text", "")

    try:
        return json.loads(text)  # Parse inner JSON
    except:
        return text  # Return as-is if not JSON
```

### 3. Tool-Specific Formatters

Each Serena tool has a formatter optimized for its output:

#### list_dir Formatter

```python
def format_list_dir(content: dict) -> str:
    """
    Input: {"dirs": ["src", "tests", ...], "files": ["main.py", ...]}
    Output: "📁 Dirs(5): src, tests... 📄 Files(8): .py(3), .md(2)..."
    """
    dirs = content.get("dirs", [])
    files = content.get("files", [])

    # Group files by extension
    by_ext = {}
    for f in files:
        ext = Path(f).suffix or "(no ext)"
        by_ext.setdefault(ext, []).append(f)

    # Format output
    dir_line = f"📁 Dirs({len(dirs)}): {', '.join(dirs[:8])}"
    file_summary = ", ".join(f"{ext}({len(fs)})" for ext, fs in by_ext.items())

    return f"{dir_line}\n📄 Files({len(files)}): {file_summary}"
```

#### find_symbol Formatter

```python
def format_find_symbol(content: list) -> str:
    """
    Input: [{"name_path": "Class/method", "kind": "Function",
             "body_location": {"start_line": 42, "end_line": 98},
             "relative_path": "src/file.py"}, ...]

    Output:
    • Class/method [Function] @ src/file.py:42-98
    • AnotherSymbol [Variable] @ src/other.py:10-10
    """
    lines = []
    for sym in content[:10]:
        name = sym.get("name_path", sym.get("name", "?"))
        kind = sym.get("kind", "?")
        path = sym.get("relative_path", "")
        loc = sym.get("body_location", {})
        start = loc.get("start_line", "?")
        end = loc.get("end_line", "?")

        lines.append(f"• {name} [{kind}] @ {path}:{start}-{end}")

    return "\n".join(lines)
```

### 4. CLI Argument Parsing

Tool-aware positional argument mapping:

```python
def parse_args():
    positional_map = {
        "list_dir": ["relative_path"],
        "get_symbols_overview": ["relative_path"],
        "find_symbol": ["name_path_pattern"],
        "find_file": ["file_mask", "relative_path"],
        "search_for_pattern": ["substring_pattern"],
        "find_referencing_symbols": ["name_path", "relative_path"],
        "read_file": ["relative_path"],
    }

    # First positional arg maps to first key, etc.
    # --key value for explicit params
    # --output FILE saves full JSON
```

## Protocol Details

### MCP Message IDs

Sequential IDs track request-response pairs:

| ID | Message | Purpose |
|----|---------|---------|
| 1 | `initialize` | Protocol handshake |
| 2 | `tools/call` | Actual tool invocation |

### SSE Event Format

```
event: message
data: {"jsonrpc": "2.0", "id": 1, "result": {...}}

event: message
data: {"jsonrpc": "2.0", "id": 2, "result": {...}}
```

### Error Handling

```python
if "error" in data:
    err = data["error"]
    if isinstance(err, dict):
        return f"Error: {err.get('message', err)}"
    return f"Error: {err}"
```

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Connection setup | ~50ms |
| MCP init handshake | ~100ms |
| Tool call latency | ~200-500ms |
| Total round-trip | ~350-650ms |

Compared to direct MCP in session (same latency), but **result stays external**.

## Extension Points

### Adding New Formatter

```python
def format_new_tool(content: Any) -> str:
    """Custom formatter for new_tool output."""
    # Extract key fields
    # Format to 1-3 lines
    # Include actionable info (file:line, counts)
    return formatted_string

# Register in FORMATTERS dict
FORMATTERS["new_tool"] = format_new_tool
```

### Adding New Tool Parameters

```python
# In positional_map:
positional_map["new_tool"] = ["param1", "param2"]

# Params auto-converted:
# "true"/"false" → bool
# digits → int
```
