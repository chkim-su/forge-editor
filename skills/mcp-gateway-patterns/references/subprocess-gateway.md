# Subprocess Gateway Pattern

## When to Use

Use subprocess isolation when:
- Main session must have **zero MCP token overhead**
- MCP is rarely used but very large
- Stateless operations are acceptable
- Session startup latency (5-15s) is tolerable

## Architecture

```
Main Session (no MCP loaded)
    ↓
Python Gateway Script
    ↓
subprocess: claude --mcp-config {mcp}.mcp.json
    ↓
JSON Response back to main session
```

---

## MCP Config File

Create dedicated config for isolated MCP:

`config/{mcp}.mcp.json`:
```json
{
  "mcpServers": {
    "{mcp}": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/{org}/{mcp}@{commit_sha}", "{mcp}", "start-mcp-server"]
    }
  }
}
```

**Important**: Pin to specific commit SHA for reproducibility.

---

## Python Gateway Script Template

`scripts/{mcp}_gateway.py`:

```python
#!/usr/bin/env python3
"""
{MCP_NAME} Gateway - Subprocess Isolation Pattern

Executes {MCP_NAME} operations in isolated Claude session.
Main session has zero MCP token overhead.
"""

import subprocess
import json
import sys
import time
import argparse
from pathlib import Path
from typing import Any

# Configuration
DEFAULT_TIMEOUT_MS = 300_000  # 5 minutes
MCP_CONFIG = "config/{mcp}.mcp.json"
MCP_NAME = "{mcp}"


def create_request(
    intent: str,
    action: str,
    effect: str,
    artifact: str,
    params: dict,
    project_root: str = ".",
    caller: str = None
) -> dict:
    """Create standard gateway request."""
    return {
        "intent": intent,
        "action": action,
        "effect": effect,
        "artifact": artifact,
        "params": params,
        "constraints": {
            "timeout_ms": DEFAULT_TIMEOUT_MS,
            "isolation": "subprocess"
        },
        "context": {
            "caller": caller,
            "project_root": project_root
        }
    }


def create_success_response(
    request: dict,
    data: Any,
    duration_ms: int,
    affected_files: list = None,
    affected_symbols: list = None
) -> dict:
    """Create standard success response."""
    return {
        "ok": True,
        "request": {
            "intent": request["intent"],
            "action": request["action"],
            "effect": request["effect"]
        },
        "result": {
            "artifact_type": request["artifact"],
            "data": data,
            "affected_files": affected_files or [],
            "affected_symbols": affected_symbols or []
        },
        "meta": {
            "duration_ms": duration_ms,
            "mcp_name": MCP_NAME,
            "isolation_used": "subprocess"
        }
    }


def create_error_response(
    request: dict,
    error_type: str,
    message: str,
    duration_ms: int,
    recoverable: bool = True,
    suggestion: str = None,
    exit_code: int = None
) -> dict:
    """Create standard error response."""
    return {
        "ok": False,
        "request": {
            "intent": request.get("intent", "UNKNOWN"),
            "action": request.get("action", "UNKNOWN"),
            "effect": request.get("effect", "UNKNOWN")
        },
        "error": {
            "type": error_type,
            "message": message,
            "recoverable": recoverable,
            "suggestion": suggestion
        },
        "meta": {
            "duration_ms": duration_ms,
            "exit_code": exit_code,
            "mcp_name": MCP_NAME,
            "isolation_used": "subprocess"
        }
    }


def run_gateway(request: dict) -> dict:
    """Execute request in isolated Claude session."""
    start_time = time.time()
    timeout_s = request.get("constraints", {}).get("timeout_ms", DEFAULT_TIMEOUT_MS) / 1000
    project_root = request.get("context", {}).get("project_root", ".")

    # Build prompt from request
    prompt = build_prompt_from_request(request)

    # Build command
    cmd = [
        "claude",
        "--mcp-config", str(Path(MCP_CONFIG).resolve()),
        "-p", prompt,
        "--output-format", "json",
        "--max-turns", "3"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=project_root
        )

        duration_ms = int((time.time() - start_time) * 1000)

        if result.returncode != 0:
            return create_error_response(
                request=request,
                error_type="MCP_ERROR",
                message=f"Claude CLI exited with code {result.returncode}",
                duration_ms=duration_ms,
                recoverable=True,
                suggestion="Check MCP config and try again",
                exit_code=result.returncode
            )

        # Parse Claude output
        try:
            output_data = parse_claude_output(result.stdout)
            return create_success_response(
                request=request,
                data=output_data,
                duration_ms=duration_ms
            )
        except json.JSONDecodeError as e:
            return create_error_response(
                request=request,
                error_type="VALIDATION",
                message=f"Failed to parse Claude output: {e}",
                duration_ms=duration_ms,
                recoverable=False,
                suggestion="Check Claude output format"
            )

    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        return create_error_response(
            request=request,
            error_type="TIMEOUT",
            message=f"Request timed out after {timeout_s}s",
            duration_ms=duration_ms,
            recoverable=True,
            suggestion="Increase timeout or simplify request"
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return create_error_response(
            request=request,
            error_type="UNKNOWN",
            message=str(e),
            duration_ms=duration_ms,
            recoverable=False
        )


def build_prompt_from_request(request: dict) -> str:
    """Convert request to Claude prompt."""
    action = request["action"]
    params = request["params"]

    # Build action-specific prompt
    # Customize this for your MCP
    prompt = f"""Execute the following {MCP_NAME} operation:

Action: {action}
Parameters: {json.dumps(params, indent=2)}

Return the result as structured JSON.
"""
    return prompt


def parse_claude_output(stdout: str) -> Any:
    """Parse Claude CLI JSON output."""
    # Claude --output-format json returns structured output
    # Extract the actual result from Claude's response
    data = json.loads(stdout)

    # Navigate to actual content based on Claude output structure
    if "result" in data:
        return data["result"]
    return data


def main():
    parser = argparse.ArgumentParser(description=f"{MCP_NAME} Gateway")
    parser.add_argument("--request", "-r", type=str, help="JSON request string")
    parser.add_argument("--request-file", "-f", type=str, help="JSON request file")
    parser.add_argument("--project", "-d", type=str, default=".", help="Project directory")

    args = parser.parse_args()

    # Load request
    if args.request:
        request = json.loads(args.request)
    elif args.request_file:
        with open(args.request_file) as f:
            request = json.load(f)
    else:
        # Read from stdin
        request = json.load(sys.stdin)

    # Override project root if specified
    if args.project != ".":
        request.setdefault("context", {})["project_root"] = args.project

    # Execute and output
    response = run_gateway(request)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
```

---

## Usage Examples

### Command Line

```bash
# Direct request
python3 scripts/{mcp}_gateway.py -r '{
  "intent": "QUERY",
  "action": "find_symbol",
  "effect": "READ_ONLY",
  "artifact": "JSON",
  "params": {"name": "MyClass"}
}'

# From file
python3 scripts/{mcp}_gateway.py -f request.json

# From stdin
echo '{"intent": "QUERY", ...}' | python3 scripts/{mcp}_gateway.py
```

### From Agent

```python
import subprocess
import json

request = {
    "intent": "QUERY",
    "action": "find_symbol",
    "effect": "READ_ONLY",
    "artifact": "JSON",
    "params": {"name": "MyClass"}
}

result = subprocess.run(
    ["python3", "scripts/{mcp}_gateway.py"],
    input=json.dumps(request),
    capture_output=True,
    text=True
)

response = json.loads(result.stdout)
if response["ok"]:
    data = response["result"]["data"]
else:
    error = response["error"]
```

---

## Disabling MCP in Main Session

To achieve zero token overhead, disable MCP in main session:

`~/.claude/settings.json`:
```json
{
  "{mcp}@claude-plugins-official": false
}
```

Verify with `/context` command - MCP tools should not appear.

---

## Error Handling Best Practices

1. **Always output valid JSON** - Even on crash, catch and wrap
2. **Include recovery suggestions** - Help caller fix the issue
3. **Mark recoverability** - `recoverable: true/false`
4. **Preserve exit codes** - For debugging subprocess issues

---

## Timeout Guidelines

| Effect | Recommended Timeout |
|--------|---------------------|
| READ_ONLY | 60s |
| MUTATING | 120s |
| EXTERNAL_EXEC | 300s (default) |

Override per-request via `constraints.timeout_ms`.
