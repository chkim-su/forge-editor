# MCP-SSE Protocol Reference

## Protocol Overview

Model Context Protocol over Server-Sent Events for persistent daemon connections.

```
┌─────────┐          ┌─────────┐          ┌─────────┐
│ Client  │──GET────▶│ /sse    │◀─events──│ Daemon  │
│         │──POST───▶│/messages│─────────▶│ :8765   │
└─────────┘          └─────────┘          └─────────┘
```

## Connection Lifecycle

### 1. SSE Connection

```http
GET /sse HTTP/1.1
Host: localhost:8765
Accept: text/event-stream
```

Response (streaming):
```
data: http://localhost:8765/messages/?session_id=abc123def456

event: message
data: {...json...}
```

### 2. Session ID Extraction

First `data:` line contains the message endpoint with session ID:

```
data: http://localhost:8765/messages/?session_id=abc123def456
                                               └──────────────┘
                                               Extract this
```

### 3. Initialize Handshake

**Request:**
```http
POST /messages/?session_id=abc123def456 HTTP/1.1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "serena-query",
      "version": "0.1.0"
    }
  }
}
```

**Response** (via SSE):
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "serena",
      "version": "0.1.0"
    }
  }
}
```

### 4. Initialized Notification

After receiving init response, send notification (no response expected):

```http
POST /messages/?session_id=abc123def456 HTTP/1.1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

**Note:** No `id` field - this is a notification, not a request.

### 5. Tool Call

Now tools can be called:

```http
POST /messages/?session_id=abc123def456 HTTP/1.1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "list_dir",
    "arguments": {
      "relative_path": ".",
      "recursive": false
    }
  }
}
```

**Response** (via SSE):
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"dirs\": [\"src\", \"tests\"], \"files\": [\"main.py\"]}"
      }
    ],
    "isError": false
  }
}
```

## Message Types

### Requests (with id)

| Method | Purpose |
|--------|---------|
| `initialize` | Start MCP session |
| `tools/call` | Invoke a tool |
| `tools/list` | List available tools |
| `resources/read` | Read a resource |

### Notifications (no id)

| Method | Purpose |
|--------|---------|
| `notifications/initialized` | Confirm init complete |
| `notifications/cancelled` | Cancel pending request |

## Response Structure

### Success Response

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "...result data..."
      }
    ],
    "isError": false
  }
}
```

### Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32602,
    "message": "Invalid params: missing required field 'relative_path'"
  }
}
```

### Common Error Codes

| Code | Meaning |
|------|---------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

## State Machine

```
     ┌─────────────┐
     │ DISCONNECTED│
     └──────┬──────┘
            │ GET /sse
            ▼
     ┌─────────────┐
     │ CONNECTING  │──timeout──▶ Error
     └──────┬──────┘
            │ session_id received
            ▼
     ┌─────────────┐
     │ INITIALIZING│──error────▶ Error
     └──────┬──────┘
            │ init response id=1
            ▼
     ┌─────────────┐
     │   READY     │
     └──────┬──────┘
            │ tools/call
            ▼
     ┌─────────────┐
     │  WAITING    │──timeout──▶ Error
     └──────┬──────┘
            │ result id=N
            ▼
     ┌─────────────┐
     │    DONE     │
     └─────────────┘
```

## Implementation Notes

### Why SSE over HTTP/2?

- **Persistent connection:** No reconnect overhead per call
- **Server push:** Daemon can send events proactively
- **Stateful session:** Context maintained between calls

### Session Management

- Session ID is ephemeral per SSE connection
- Closing SSE connection invalidates session
- Each CLI invocation creates new session (acceptable overhead)

### Timeout Handling

```python
async with httpx.AsyncClient(timeout=60.0) as client:
    # 60 second timeout for entire operation
    # Individual operations complete faster
```

### Concurrent Requests

MCP supports multiple in-flight requests via unique IDs:

```python
msg_id += 1  # Increment for each request
# Match response id to request id
if data.get("id") == msg_id:
    return data
```
