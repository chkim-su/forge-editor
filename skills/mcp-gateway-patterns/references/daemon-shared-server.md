# MCP Daemon Pattern: Shared Server Architecture

**Problem**: Subprocess isolation gives zero main-session overhead but suffers 30-60s startup per call.

**Solution**: Run MCP server as persistent HTTP/SSE daemon, share across all sessions.

---

## When to Use

| Scenario | Daemon Pattern |
|----------|----------------|
| Frequent MCP calls + zero main overhead | ✅ Ideal |
| Multiple Claude Code sessions simultaneously | ✅ Ideal |
| CI/CD pipelines with repeated MCP access | ✅ Ideal |
| Single session, rare MCP use | ❌ Use Subprocess |
| Simple project, token budget OK | ❌ Use Agent Gateway |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Daemon (Persistent)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  serena start-mcp-server --transport sse --port 8765      │  │
│  │  Running continuously (systemd/screen/nohup)              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
              │                    │                    │
              │ SSE/HTTP           │ SSE/HTTP           │ SSE/HTTP
              ▼                    ▼                    ▼
     ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
     │ Claude Session │   │ Claude Session │   │ Subprocess     │
     │ (Main Editor)  │   │ (Terminal 2)   │   │ (Gateway)      │
     └────────────────┘   └────────────────┘   └────────────────┘
              │                    │                    │
              └──────────────────────────────────────────┘
                          Shared MCP State
```

### Performance Comparison

| Pattern | Startup | Main Session Overhead | State Sharing |
|---------|---------|----------------------|---------------|
| Agent Gateway | ~1s | ~10,000 tokens | ✅ Yes |
| Subprocess | 30-60s | 0 tokens | ❌ No |
| **Daemon** | **1-2s** | **0 tokens** | **✅ Yes** |

---

## Transport Options

### MCP Protocol Transports

| Transport | Protocol | Daemon Capable | Claude Support |
|-----------|----------|----------------|----------------|
| `stdio` | Pipe | ❌ No | ✅ Default |
| `sse` | HTTP + SSE | ✅ Yes | ✅ `--transport sse` |
| `streamable-http` | HTTP POST/GET | ✅ Yes | ⚠️ Limited |
| `websocket` | WebSocket | ✅ Yes | ❌ Not supported |

**Recommendation**: Use `sse` transport - best compatibility.

---

## Quick Start

### Step 1: Start Daemon

```bash
# Using screen (development)
screen -dmS serena-daemon uvx --from git+https://github.com/oraios/serena \
  serena start-mcp-server \
  --transport sse \
  --host 127.0.0.1 \
  --port 8765 \
  --project-root /path/to/project

# Verify running
curl -s http://127.0.0.1:8765/health || echo "Not running"
```

### Step 2: Register with Claude Code

```bash
# Register shared MCP (user scope)
claude mcp add \
  --transport sse \
  --scope user \
  serena-shared \
  http://127.0.0.1:8765

# Verify registration
claude mcp list | grep serena-shared
```

### Step 3: Restart Claude Code

MCP changes require session restart:
```bash
# In Claude Code
/exit

# Relaunch
claude
```

### Step 4: Verify Connection

```bash
# Check tools are available
claude -p "List all mcp__serena-shared__ tools available" --max-turns 1
```

---

## Production Setup

### Systemd Service (Linux)

Create `/etc/systemd/system/mcp-serena.service`:

```ini
[Unit]
Description=Serena MCP Daemon Server
After=network.target

[Service]
Type=simple
User=your-username
Environment="HOME=/home/your-username"
Environment="PATH=/home/your-username/.local/bin:/usr/local/bin:/usr/bin:/bin"
WorkingDirectory=/home/your-username/projects/default-project
ExecStart=/home/your-username/.local/bin/uvx --from git+https://github.com/oraios/serena serena start-mcp-server --transport sse --host 127.0.0.1 --port 8765 --project-root /home/your-username/projects/default-project
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-serena
sudo systemctl start mcp-serena

# Check status
systemctl status mcp-serena
journalctl -u mcp-serena -f
```

### Launchd (macOS)

Create `~/Library/LaunchAgents/com.serena.mcp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.serena.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/uvx</string>
        <string>--from</string>
        <string>git+https://github.com/oraios/serena</string>
        <string>serena</string>
        <string>start-mcp-server</string>
        <string>--transport</string>
        <string>sse</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8765</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/mcp-serena.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mcp-serena.err</string>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.serena.mcp.plist
launchctl list | grep serena
```

---

## Project Switching

The daemon is bound to one project root. Options for multi-project:

### Option A: Multiple Ports

```bash
# Project A on port 8765
serena start-mcp-server --transport sse --port 8765 --project-root ~/projects/A

# Project B on port 8766
serena start-mcp-server --transport sse --port 8766 --project-root ~/projects/B

# Register both
claude mcp add --transport sse --scope user serena-project-a http://127.0.0.1:8765
claude mcp add --transport sse --scope user serena-project-b http://127.0.0.1:8766
```

### Option B: Dynamic Restart Script

```bash
#!/bin/bash
# switch-mcp-project.sh

PROJECT_ROOT="$1"
PORT=8765

# Stop existing
pkill -f "serena.*--port $PORT"

# Start for new project
uvx --from git+https://github.com/oraios/serena \
  serena start-mcp-server \
  --transport sse \
  --port $PORT \
  --project-root "$PROJECT_ROOT" &

echo "MCP daemon restarted for: $PROJECT_ROOT"
echo "⚠️  Restart Claude Code to reconnect"
```

### Option C: Project-Scoped Registration

Register per-project in `.mcp.json`:

```json
{
  "mcpServers": {
    "serena-local": {
      "transport": "sse",
      "url": "http://127.0.0.1:8765"
    }
  }
}
```

Start daemon when entering project:
```bash
# In direnv .envrc or shell hook
uvx --from git+https://github.com/oraios/serena \
  serena start-mcp-server --transport sse --port 8765 --project-from-cwd &
```

---

## Subprocess with Daemon

Combine daemon with subprocess isolation for true zero-overhead:

```python
#!/usr/bin/env python3
"""Subprocess gateway using daemon MCP."""

import subprocess
import json

def call_daemon_mcp(prompt: str, timeout: int = 60) -> dict:
    """Call MCP through daemon (no server startup overhead)."""

    # MCP config pointing to daemon
    daemon_config = {
        "mcpServers": {
            "serena": {
                "transport": "sse",
                "url": "http://127.0.0.1:8765"
            }
        }
    }

    # Write temp config
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(daemon_config, f)
        config_path = f.name

    try:
        cmd = [
            "claude",
            "--mcp-config", config_path,
            "-p", prompt,
            "--output-format", "json",
            "--max-turns", "3"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return json.loads(result.stdout) if result.stdout else {"error": "No output"}

    finally:
        import os
        os.unlink(config_path)


# Usage
response = call_daemon_mcp(
    "Use mcp__serena__find_symbol to find all classes. Return JSON."
)
print(json.dumps(response, indent=2))
```

**Key difference**: Instead of `command: uvx...` (30-60s startup), use `transport: sse, url: http://...` (1-2s connection).

---

## Health Monitoring

### Simple Health Check Script

```bash
#!/bin/bash
# check-mcp-daemon.sh

PORT=${1:-8765}
URL="http://127.0.0.1:$PORT"

if curl -s --max-time 2 "$URL" > /dev/null 2>&1; then
    echo "✅ MCP daemon running on port $PORT"
    exit 0
else
    echo "❌ MCP daemon not responding on port $PORT"
    exit 1
fi
```

### Auto-Restart Wrapper

```bash
#!/bin/bash
# mcp-daemon-watchdog.sh

PORT=8765
CHECK_INTERVAL=30

while true; do
    if ! curl -s --max-time 2 "http://127.0.0.1:$PORT" > /dev/null 2>&1; then
        echo "$(date): MCP daemon down, restarting..."

        pkill -f "serena.*--port $PORT" 2>/dev/null

        uvx --from git+https://github.com/oraios/serena \
          serena start-mcp-server \
          --transport sse \
          --port $PORT \
          --project-from-cwd &

        sleep 5
    fi

    sleep $CHECK_INTERVAL
done
```

---

## Troubleshooting

### "Connection refused"

```bash
# Check if daemon is running
ps aux | grep "serena.*start-mcp-server"
netstat -tlnp | grep 8765  # Linux
lsof -i :8765              # macOS

# Check firewall
sudo ufw status  # Linux
```

### "MCP tools not appearing"

```bash
# 1. Verify registration
claude mcp list

# 2. Check transport type matches
# daemon started with: --transport sse
# registration needs: --transport sse

# 3. Restart Claude Code (required after mcp add)
```

### "Wrong project context"

Daemon serves one project root. Verify:
```bash
# What project is daemon serving?
ps aux | grep serena | grep project-root

# Restart with correct project
pkill -f serena
serena start-mcp-server --transport sse --port 8765 --project-root /correct/path &
```

### "Stale connections after daemon restart"

Claude Code caches SSE connections. Force reconnect:
```bash
# Option 1: Restart Claude Code
/exit && claude

# Option 2: Re-register MCP
claude mcp remove serena-shared
claude mcp add --transport sse --scope user serena-shared http://127.0.0.1:8765
/exit && claude
```

---

## Security Considerations

### Binding to localhost only

```bash
# SAFE: Only local access
--host 127.0.0.1

# DANGEROUS: Network-accessible (avoid!)
--host 0.0.0.0
```

### Authentication (if network exposed)

MCP SSE transport doesn't have built-in auth. If you must expose:

```bash
# Use SSH tunnel instead
ssh -L 8765:localhost:8765 remote-server

# Then connect locally
claude mcp add --transport sse --scope user serena-remote http://127.0.0.1:8765
```

---

## Summary: Pattern Selection Guide

| Need | Recommended Pattern |
|------|---------------------|
| Simple project, single session | Agent Gateway |
| Zero overhead, rare MCP use | Subprocess |
| Zero overhead, frequent MCP use | **Daemon** |
| Multiple sessions sharing state | **Daemon** |
| CI/CD with repeated MCP calls | **Daemon** |
| Air-gapped/offline environment | Subprocess |

---

## Related References

- [Agent Gateway Template](agent-gateway-template.md) - Standard inherited MCP
- [Subprocess Gateway](subprocess-gateway.md) - Per-call isolation
- [Subprocess Research Report](subprocess-research-report.md) - Empirical findings
- [Setup Automation](setup-automation.md) - Auto-configuration hooks
