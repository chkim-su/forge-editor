# SAP2000 MCP Gateway Design Example

This example demonstrates how `mcp-gateway-designer` would design a **Subprocess Isolation** gateway for SAP2000 OAPI integration.

## MCP Characteristics

| Characteristic | Value | Implication |
|----------------|-------|-------------|
| Usage Frequency | Low | Subprocess isolation preferred |
| Tool Count | ~50+ COM methods | Large token overhead |
| Operation Type | External (COM) | EXTERNAL_EXEC effect |
| Latency Tolerance | High (analysis can take minutes) | Long timeout acceptable |

## Strategy Decision

**Subprocess Isolation** is recommended because:
1. SAP2000 is rarely used in typical dev sessions
2. Large tool schema would waste tokens in main session
3. Operations are stateless (each model analysis is independent)
4. COM calls already have startup latency (SAP2000 launch)

---

## Action Mapping

### Intent → Action Mapping

| Intent | Action | Serena Tool (hypothetical) | Effect | Artifact |
|--------|--------|---------------------------|--------|----------|
| QUERY | search_oapi | Search OAPI documentation | READ_ONLY | JSON |
| QUERY | resolve_com_type | Get COM type information | READ_ONLY | JSON |
| QUERY | get_model_info | Get current model metadata | READ_ONLY | JSON |
| GENERATE | generate_py_wrapper | Create Python wrapper function | READ_ONLY | CODE_PY |
| GENERATE | generate_batch_script | Create analysis batch script | READ_ONLY | CODE_PY |
| EXECUTE | run_analysis | Run structural analysis | EXTERNAL_EXEC | JSON |
| EXECUTE | apply_load_case | Apply load to model | EXTERNAL_EXEC | JSON |
| MODIFY | update_section | Modify section properties | MUTATING | JSON |

---

## Generated Files

### 1. MCP Config

`config/sap2000.mcp.json`:
```json
{
  "mcpServers": {
    "sap2000": {
      "command": "python",
      "args": ["-m", "sap2000_mcp.server", "--project", "."],
      "env": {
        "SAP2000_PATH": "C:\\Program Files\\CSI\\SAP2000 24\\SAP2000.exe"
      }
    }
  }
}
```

### 2. Python Gateway

`scripts/sap2000_gateway.py`:
See `subprocess-gateway.md` template with SAP2000-specific:
- Default timeout: 300s (analysis can be slow)
- Project path handling for `.sdb` files
- Error handling for COM exceptions

### 3. Disable in Main Session

`~/.claude/settings.json`:
```json
{
  "sap2000@local-mcp": false
}
```

---

## Usage Example

### From Main Session

```python
# Main session has zero SAP2000 MCP token overhead

request = {
    "intent": "GENERATE",
    "action": "generate_py_wrapper",
    "effect": "READ_ONLY",
    "artifact": "CODE_PY",
    "params": {
        "function_name": "SapModel.FrameObj.SetSection",
        "docstring": True
    },
    "context": {
        "project_root": "/path/to/structural/project"
    }
}

# Subprocess isolation - only this call loads SAP2000 MCP
response = run_sap2000_gateway(request)

if response["ok"]:
    wrapper_code = response["result"]["data"]
    # Use the generated wrapper code
```

### Direct CLI

```bash
python3 scripts/sap2000_gateway.py -r '{
  "intent": "EXECUTE",
  "action": "run_analysis",
  "effect": "EXTERNAL_EXEC",
  "artifact": "JSON",
  "params": {
    "model_path": "bridge_model.sdb",
    "load_case": "Dead Load"
  }
}'
```

---

## Timeout Guidelines

| Action | Recommended Timeout |
|--------|---------------------|
| search_oapi | 30s |
| resolve_com_type | 30s |
| generate_py_wrapper | 60s |
| run_analysis | 600s (10 min) |
| apply_load_case | 120s |

---

## Error Handling

SAP2000-specific error types:
- `COM_ERROR`: COM interop failure
- `MODEL_NOT_FOUND`: .sdb file doesn't exist
- `LICENSE_ERROR`: SAP2000 license issue
- `ANALYSIS_FAILED`: Structural analysis error

All errors are wrapped in standard response format with `recoverable` hint.
