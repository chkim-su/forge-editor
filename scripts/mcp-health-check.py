#!/usr/bin/env python3
"""
MCP Health Check Script

Verifies MCP daemon is running and healthy before tool execution.
Exit codes:
  0 = Healthy (allow)
  1 = Warning (MCP not configured, non-blocking)
  2 = Unhealthy (block if MCP required)

Usage:
  python3 mcp-health-check.py [--require]

Options:
  --require    Exit 2 if MCP not running (blocks PreToolUse)
  (default)    Exit 1 if MCP not running (warning only)
"""

import json
import subprocess
import sys
from pathlib import Path


def get_mcp_config() -> dict:
    """Get MCP configuration from .mcp.json or ~/.claude.json."""
    # Check project-level config first
    project_mcp = Path.cwd()
    while project_mcp != project_mcp.parent:
        mcp_json = project_mcp / ".mcp.json"
        if mcp_json.exists():
            try:
                with open(mcp_json) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        project_mcp = project_mcp.parent

    # Check user-level config
    user_config = Path.home() / ".claude.json"
    if user_config.exists():
        try:
            with open(user_config) as f:
                data = json.load(f)
                return data.get("mcpServers", {})
        except (json.JSONDecodeError, IOError):
            pass

    return {}


def check_daemon_health(server_name: str, config: dict) -> bool:
    """Check if a specific MCP server is healthy."""
    server_config = config.get(server_name, {})
    command = server_config.get("command", "")

    # For daemon-style servers, check if process is running
    if "daemon" in server_name.lower() or "serena" in server_name.lower():
        try:
            result = subprocess.run(
                ["pgrep", "-f", command],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    # For stdio servers, they're spawned on-demand (assume OK)
    return True


def main():
    require_mode = "--require" in sys.argv

    config = get_mcp_config()

    if not config:
        # No MCP configured
        if require_mode:
            print("MCP_HEALTH: No MCP servers configured")
            print("Configure with: claude mcp add <server-name>")
            sys.exit(2)
        else:
            # Silent pass if MCP not configured (optional)
            sys.exit(0)

    # Check health of each configured server
    unhealthy = []
    for server_name in config:
        if not check_daemon_health(server_name, config):
            unhealthy.append(server_name)

    if unhealthy:
        print(f"MCP_HEALTH: Unhealthy servers: {', '.join(unhealthy)}")
        if require_mode:
            print("Start servers before proceeding")
            sys.exit(2)
        else:
            # Warning only
            sys.exit(1)

    # All healthy
    sys.exit(0)


if __name__ == "__main__":
    main()
