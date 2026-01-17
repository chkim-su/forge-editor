#!/usr/bin/env python3
"""
Forge State CLI - Client for forge daemon.

Commands:
  get                    Print current state JSON
  get-phase              Print current phase number
  set-phase <n>          Set phase (with validation)
  activate               Set forge_active=true, phase=0
  deactivate             Set forge_active=false
  checkpoint <agent>     Record checkpoint and advance phase
  confirm                Confirm Execute phase
  is-active              Exit 0 if active, 1 if not
  phases                 Print phase configuration
  set-design-hash        Set design content hash for versioning
  add-rollback <desc>    Add rollback point
  get-rollbacks          List rollback points
  start-daemon           Start daemon if not running
  stop-daemon            Stop daemon
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Phase configuration (6 phases with Preview)
PHASES = {
    0: {"name": "Input", "agent": "forge:input-agent"},
    1: {"name": "Analysis", "agent": "forge:analysis-agent"},
    2: {"name": "Design", "agent": "forge:design-agent"},
    3: {"name": "Preview", "agent": "forge:preview-agent"},
    4: {"name": "Execute", "agent": "forge:execute-agent"},
    5: {"name": "Validate", "agent": "forge:validate-agent"}
}


def get_workspace_root() -> str:
    """Get workspace root from environment or current directory."""
    return os.environ.get("FORGE_WORKSPACE", os.getcwd())


def get_socket_path(workspace_root: str) -> Path:
    """Get socket path for workspace."""
    return Path(workspace_root) / ".claude" / "local" / "forge.sock"


def get_state_file(workspace_root: str) -> Path:
    """Get state file path for workspace."""
    return Path(workspace_root) / ".claude" / "local" / "forge-state.json"


def daemon_running(workspace_root: str) -> bool:
    """Check if daemon is running."""
    socket_path = get_socket_path(workspace_root)
    if not socket_path.exists():
        return False

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect(str(socket_path))
        sock.close()
        return True
    except (socket.error, OSError):
        return False


def send_command(workspace_root: str, command: dict) -> dict:
    """Send command to daemon and return response."""
    socket_path = get_socket_path(workspace_root)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(str(socket_path))

        sock.sendall((json.dumps(command) + "\n").encode('utf-8'))

        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        sock.close()
        return json.loads(data.decode('utf-8').strip())
    except Exception as e:
        return {"error": f"Daemon communication failed: {e}"}


def fallback_read_state(workspace_root: str) -> dict:
    """Read state directly from file (fallback when daemon not running)."""
    state_file = get_state_file(workspace_root)
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "forge_active": False,
        "workspace_root": workspace_root,
        "phase": 0,
        "confirmed": False,
        "checkpoints": [],
        "design_hash": None,
        "requires_reconfirmation": False,
        "rollback_points": []
    }


def start_daemon(workspace_root: str) -> bool:
    """Start the forge daemon."""
    if daemon_running(workspace_root):
        return True

    # Find daemon script
    script_dir = Path(__file__).parent
    daemon_script = script_dir / "forge-daemon.py"

    if not daemon_script.exists():
        print(f"Error: Daemon script not found at {daemon_script}", file=sys.stderr)
        return False

    # Start daemon in background
    try:
        subprocess.Popen(
            [sys.executable, str(daemon_script), workspace_root],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Wait for daemon to start
        for _ in range(10):
            time.sleep(0.2)
            if daemon_running(workspace_root):
                return True

        print("Warning: Daemon may not have started properly", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error starting daemon: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    workspace_root = get_workspace_root()

    # Commands that don't need daemon
    if cmd == "start-daemon":
        if start_daemon(workspace_root):
            print("Daemon started")
            sys.exit(0)
        else:
            print("Failed to start daemon")
            sys.exit(1)

    if cmd == "stop-daemon":
        if daemon_running(workspace_root):
            result = send_command(workspace_root, {"cmd": "shutdown"})
            print(json.dumps(result, indent=2))
        else:
            print("Daemon not running")
        sys.exit(0)

    # Try daemon first, fall back to file-based
    use_daemon = daemon_running(workspace_root)

    if cmd == "get":
        if use_daemon:
            result = send_command(workspace_root, {"cmd": "get"})
        else:
            result = fallback_read_state(workspace_root)
        print(json.dumps(result, indent=2))

    elif cmd == "get-phase":
        if use_daemon:
            result = send_command(workspace_root, {"cmd": "get-phase"})
            print(result.get("phase", 0))
        else:
            state = fallback_read_state(workspace_root)
            print(state.get("phase", 0))

    elif cmd == "is-active":
        if use_daemon:
            result = send_command(workspace_root, {"cmd": "is-active"})
            active = result.get("active", False)
        else:
            state = fallback_read_state(workspace_root)
            active = state.get("forge_active", False)

        sys.exit(0 if active else 1)

    elif cmd == "phases":
        if use_daemon:
            result = send_command(workspace_root, {"cmd": "phases"})
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps({"phases": PHASES}, indent=2))

    elif cmd == "activate":
        if not use_daemon:
            if not start_daemon(workspace_root):
                print("Error: Could not start daemon", file=sys.stderr)
                sys.exit(1)
        result = send_command(workspace_root, {"cmd": "activate"})
        print(json.dumps(result, indent=2))

    elif cmd == "deactivate":
        if use_daemon:
            result = send_command(workspace_root, {"cmd": "deactivate"})
            print(json.dumps(result, indent=2))
        else:
            print("Daemon not running - nothing to deactivate")

    elif cmd == "confirm":
        if not use_daemon:
            print("Error: Daemon not running", file=sys.stderr)
            sys.exit(1)
        result = send_command(workspace_root, {"cmd": "confirm"})
        print(json.dumps(result, indent=2))

    elif cmd == "checkpoint":
        if len(sys.argv) < 3:
            print("Usage: forge-state.py checkpoint <agent>", file=sys.stderr)
            sys.exit(1)
        agent = sys.argv[2]

        if not use_daemon:
            print("Error: Daemon not running", file=sys.stderr)
            sys.exit(1)

        result = send_command(workspace_root, {"cmd": "checkpoint", "agent": agent})
        print(json.dumps(result, indent=2))

    elif cmd == "set-phase":
        if len(sys.argv) < 3:
            print("Usage: forge-state.py set-phase <n>", file=sys.stderr)
            sys.exit(1)

        try:
            phase = int(sys.argv[2])
        except ValueError:
            print("Error: Phase must be an integer", file=sys.stderr)
            sys.exit(1)

        if not use_daemon:
            print("Error: Daemon not running", file=sys.stderr)
            sys.exit(1)

        result = send_command(workspace_root, {"cmd": "set-phase", "phase": phase})
        print(json.dumps(result, indent=2))

    elif cmd == "set-design-hash":
        if len(sys.argv) < 3:
            print("Usage: forge-state.py set-design-hash <content>", file=sys.stderr)
            sys.exit(1)
        content = sys.argv[2]

        if not use_daemon:
            print("Error: Daemon not running", file=sys.stderr)
            sys.exit(1)

        result = send_command(workspace_root, {"cmd": "set-design-hash", "content": content})
        print(json.dumps(result, indent=2))

    elif cmd == "add-rollback":
        if len(sys.argv) < 3:
            print("Usage: forge-state.py add-rollback <description> [git_sha]", file=sys.stderr)
            sys.exit(1)
        desc = sys.argv[2]
        sha = sys.argv[3] if len(sys.argv) > 3 else None

        if not use_daemon:
            print("Error: Daemon not running", file=sys.stderr)
            sys.exit(1)

        result = send_command(workspace_root, {"cmd": "add-rollback", "description": desc, "git_sha": sha})
        print(json.dumps(result, indent=2))

    elif cmd == "get-rollbacks":
        if use_daemon:
            result = send_command(workspace_root, {"cmd": "get-rollbacks"})
        else:
            state = fallback_read_state(workspace_root)
            result = {"rollback_points": state.get("rollback_points", [])}
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
