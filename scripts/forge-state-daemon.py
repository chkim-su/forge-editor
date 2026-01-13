#!/usr/bin/env python3
"""
Forge-Editor State Manager Daemon

Socket-based persistent state management for forge-editor hooks.
Provides thread-safe atomic operations for workflow tracking, attempt
limiting, and session/subagent isolation.

Based on hook-daemon-patterns counter_daemon.py template.

Usage:
    # Daemon control
    python3 forge-state-daemon.py start        # Start socket server
    python3 forge-state-daemon.py stop         # Stop daemon
    python3 forge-state-daemon.py status       # Check health

    # CLI mode (recommended for hooks - uses file directly)
    python3 forge-state-daemon.py get <key>
    python3 forge-state-daemon.py set <key> <value>
    python3 forge-state-daemon.py inc <key>              # Atomic increment
    python3 forge-state-daemon.py get-step <composite_key>
    python3 forge-state-daemon.py set-step <composite_key> <step>
    python3 forge-state-daemon.py check-sequence <composite_key> <required_step>
    python3 forge-state-daemon.py list
    python3 forge-state-daemon.py clear

    # Protocol validation commands
    python3 forge-state-daemon.py set-validation <session> <workflow> <name> <status>
    python3 forge-state-daemon.py get-validation <session> <workflow> <name>
    python3 forge-state-daemon.py check-validation-deps <session> <workflow> <name> <dep1,dep2>

    # Gate commands
    python3 forge-state-daemon.py set-gate <session> <gate_name> <true|false>
    python3 forge-state-daemon.py get-gate <session> <gate_name>
    python3 forge-state-daemon.py require-gate <session> <gate_name>

Socket Protocol:
    {"cmd": "status"}
    {"cmd": "get", "args": ["key"]}
    {"cmd": "set", "args": ["key", "value"]}
    {"cmd": "inc", "args": ["key"]}
    {"cmd": "get-step", "args": ["composite_key"]}
    {"cmd": "set-step", "args": ["composite_key", "step"]}
    {"cmd": "check-sequence", "args": ["composite_key", "required_step"]}
    {"cmd": "set-validation", "args": ["session", "workflow", "name", "status"]}
    {"cmd": "get-validation", "args": ["session", "workflow", "name"]}
    {"cmd": "check-validation-deps", "args": ["session", "workflow", "name", "deps"]}
    {"cmd": "set-gate", "args": ["session", "gate_name", "true|false"]}
    {"cmd": "get-gate", "args": ["session", "gate_name"]}
    {"cmd": "require-gate", "args": ["session", "gate_name"]}
"""

import json
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Configuration
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
CLAUDE_DIR = PROJECT_DIR / ".claude"
LOCAL_DIR = CLAUDE_DIR / "local"
STATE_FILE = LOCAL_DIR / "daemon-state.json"
SOCKET_PATH = CLAUDE_DIR / "forge-state.sock"
PID_FILE = CLAUDE_DIR / "forge-state-daemon.pid"
LOG_FILE = CLAUDE_DIR / "forge-state-daemon.log"


class ForgeStateDaemon:
    """Thread-safe state daemon with socket interface."""

    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.load_state()

    def load_state(self):
        """Load state from disk."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    data = json.load(f)
                    self.state = data.get("state", {})
            except (json.JSONDecodeError, IOError):
                self.state = {}

    def save_state(self):
        """Save state to disk atomically."""
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        tmp_file = STATE_FILE.with_suffix('.tmp')
        with open(tmp_file, 'w') as f:
            json.dump({
                "state": self.state,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")
            }, f, indent=2)
        tmp_file.rename(STATE_FILE)

    def process_command(self, cmd: str, args: list) -> dict:
        """Process a command and return response."""
        try:
            if cmd == "status":
                return {
                    "status": "ok",
                    "message": "pong",
                    "keys": len(self.state),
                    "pid": os.getpid()
                }

            elif cmd == "get":
                key = args[0] if args else ""
                with self.lock:
                    value = self.state.get(key)
                return {"status": "ok", "value": value}

            elif cmd == "set":
                key = args[0] if args else ""
                value = args[1] if len(args) > 1 else None
                # Try to parse as int if it looks like one
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                with self.lock:
                    self.state[key] = value
                self.save_state()
                return {"status": "ok"}

            elif cmd == "inc":
                key = args[0] if args else ""
                with self.lock:
                    current = self.state.get(key, 0)
                    if not isinstance(current, int):
                        current = 0
                    self.state[key] = current + 1
                    value = self.state[key]
                self.save_state()
                return {"status": "ok", "value": value}

            elif cmd == "dec":
                key = args[0] if args else ""
                with self.lock:
                    current = self.state.get(key, 0)
                    if not isinstance(current, int):
                        current = 0
                    self.state[key] = current - 1
                    value = self.state[key]
                self.save_state()
                return {"status": "ok", "value": value}

            elif cmd == "get-step":
                # Get workflow step for composite key
                key = args[0] if args else ""
                step_key = f"step:{key}"
                with self.lock:
                    step = self.state.get(step_key, 0)
                return {"status": "ok", "step": step}

            elif cmd == "set-step":
                # Set workflow step for composite key
                key = args[0] if args else ""
                step = int(args[1]) if len(args) > 1 else 0
                step_key = f"step:{key}"
                with self.lock:
                    self.state[step_key] = step
                self.save_state()
                return {"status": "ok", "step": step}

            elif cmd == "check-sequence":
                # Check if required step is reachable from current step
                key = args[0] if args else ""
                required_step = int(args[1]) if len(args) > 1 else 1
                step_key = f"step:{key}"

                with self.lock:
                    current_step = self.state.get(step_key, 0)

                    # Can stay at same step or advance by 1
                    if required_step <= current_step + 1:
                        # Update step if advancing
                        if required_step > current_step:
                            self.state[step_key] = required_step
                        allow = True
                    else:
                        allow = False

                if allow:
                    self.save_state()
                    return {
                        "status": "ok",
                        "allowed": True,
                        "current_step": max(current_step, required_step),
                        "required_step": required_step
                    }
                else:
                    return {
                        "status": "ok",
                        "allowed": False,
                        "current_step": current_step,
                        "required_step": required_step,
                        "message": f"Cannot skip from step {current_step} to step {required_step}"
                    }

            elif cmd == "list":
                with self.lock:
                    return {"status": "ok", "state": dict(self.state)}

            elif cmd == "clear":
                with self.lock:
                    self.state.clear()
                self.save_state()
                return {"status": "ok", "message": "cleared"}

            elif cmd == "clear-session":
                # Clear all keys for a specific session
                session_id = args[0] if args else ""
                with self.lock:
                    keys_to_remove = [k for k in self.state.keys() if session_id in k]
                    for k in keys_to_remove:
                        del self.state[k]
                self.save_state()
                return {"status": "ok", "cleared": len(keys_to_remove)}

            # =================================================================
            # PROTOCOL VALIDATION COMMANDS
            # =================================================================

            elif cmd == "set-validation":
                # Set validation status: set-validation <session> <workflow> <name> <status>
                if len(args) < 4:
                    return {"status": "error", "message": "Usage: set-validation <session> <workflow> <name> <status>"}
                session_id, workflow_type, name, status = args[0], args[1], args[2], args[3]
                key = f"protocol:{session_id}:{workflow_type}:{name}"
                with self.lock:
                    self.state[key] = {
                        "status": status,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                self.save_state()
                return {"status": "ok", "key": key, "validation_status": status}

            elif cmd == "get-validation":
                # Get validation status: get-validation <session> <workflow> <name>
                if len(args) < 3:
                    return {"status": "error", "message": "Usage: get-validation <session> <workflow> <name>"}
                session_id, workflow_type, name = args[0], args[1], args[2]
                key = f"protocol:{session_id}:{workflow_type}:{name}"
                with self.lock:
                    data = self.state.get(key)
                if data:
                    return {"status": "ok", "key": key, "validation_status": data.get("status"), "data": data}
                return {"status": "ok", "key": key, "validation_status": None}

            elif cmd == "check-validation-deps":
                # Check if dependencies are satisfied: check-validation-deps <session> <workflow> <name> <dep1,dep2,...>
                if len(args) < 4:
                    return {"status": "error", "message": "Usage: check-validation-deps <session> <workflow> <name> <deps>"}
                session_id, workflow_type, name, deps_str = args[0], args[1], args[2], args[3]
                deps = [d.strip() for d in deps_str.split(",") if d.strip()]

                if not deps:
                    return {"status": "ok", "allowed": True, "message": "No dependencies"}

                failed_deps = []
                with self.lock:
                    for dep in deps:
                        dep_key = f"protocol:{session_id}:{workflow_type}:{dep}"
                        dep_data = self.state.get(dep_key)
                        if not dep_data or dep_data.get("status") != "passed":
                            failed_deps.append({
                                "name": dep,
                                "status": dep_data.get("status") if dep_data else "pending"
                            })

                if failed_deps:
                    return {
                        "status": "ok",
                        "allowed": False,
                        "failed_deps": failed_deps,
                        "message": f"Dependencies not satisfied: {[d['name'] for d in failed_deps]}"
                    }
                return {"status": "ok", "allowed": True}

            # =================================================================
            # GATE COMMANDS
            # =================================================================

            elif cmd == "set-gate":
                # Set gate status: set-gate <session> <gate_name> <true|false>
                if len(args) < 3:
                    return {"status": "error", "message": "Usage: set-gate <session> <gate_name> <true|false>"}
                session_id, gate_name, value = args[0], args[1], args[2]
                key = f"gate:{session_id}:{gate_name}"
                passed = value.lower() == "true"
                with self.lock:
                    self.state[key] = {
                        "passed": passed,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                self.save_state()
                return {"status": "ok", "key": key, "passed": passed}

            elif cmd == "get-gate":
                # Get gate status: get-gate <session> <gate_name>
                if len(args) < 2:
                    return {"status": "error", "message": "Usage: get-gate <session> <gate_name>"}
                session_id, gate_name = args[0], args[1]
                key = f"gate:{session_id}:{gate_name}"
                with self.lock:
                    data = self.state.get(key)
                if data:
                    return {"status": "ok", "key": key, "passed": data.get("passed", False), "data": data}
                return {"status": "ok", "key": key, "passed": False}

            elif cmd == "require-gate":
                # Require gate to be passed: require-gate <session> <gate_name>
                # Returns allowed=True if passed, allowed=False if not
                if len(args) < 2:
                    return {"status": "error", "message": "Usage: require-gate <session> <gate_name>"}
                session_id, gate_name = args[0], args[1]
                key = f"gate:{session_id}:{gate_name}"
                with self.lock:
                    data = self.state.get(key)
                passed = data.get("passed", False) if data else False
                return {
                    "status": "ok",
                    "key": key,
                    "allowed": passed,
                    "passed": passed,
                    "message": f"Gate '{gate_name}' {'passed' if passed else 'not passed'}"
                }

            # =================================================================
            # WORKFLOW STACK COMMANDS (Hierarchical Nested Workflows)
            # =================================================================

            elif cmd == "push-workflow":
                # Push nested workflow onto stack
                # Usage: push-workflow <session> <workflow_type>
                if len(args) < 2:
                    return {"status": "error", "message": "Usage: push-workflow <session> <workflow_type>"}
                session_id, workflow_type = args[0], args[1]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])

                    # Suspend current top if exists
                    if stack:
                        stack[-1]["suspended"] = True
                        stack[-1]["resume_phase"] = stack[-1].get("current_phase")

                    # Push new workflow
                    new_entry = {
                        "workflow_id": f"{workflow_type}-{int(time.time())}",
                        "workflow_type": workflow_type,
                        "current_phase": "init",
                        "suspended": False,
                        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                    stack.append(new_entry)
                    self.state[stack_key] = stack

                self.save_state()
                return {
                    "status": "ok",
                    "workflow_type": workflow_type,
                    "depth": len(stack)
                }

            elif cmd == "pop-workflow":
                # Pop current workflow, resume parent
                # Usage: pop-workflow <session>
                if len(args) < 1:
                    return {"status": "error", "message": "Usage: pop-workflow <session>"}
                session_id = args[0]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])

                    if not stack:
                        return {"status": "error", "message": "Stack empty"}

                    popped = stack.pop()

                    # Resume parent if exists
                    resumed_workflow = None
                    resume_phase = None
                    if stack:
                        stack[-1]["suspended"] = False
                        resumed_workflow = stack[-1]["workflow_type"]
                        resume_phase = stack[-1].get("resume_phase")

                    self.state[stack_key] = stack

                self.save_state()
                return {
                    "status": "ok",
                    "popped": popped["workflow_type"],
                    "resumed_workflow": resumed_workflow,
                    "resume_phase": resume_phase,
                    "depth": len(stack)
                }

            elif cmd == "get-active-workflow":
                # Get top of stack (current active)
                # Usage: get-active-workflow <session>
                if len(args) < 1:
                    return {"status": "error", "message": "Usage: get-active-workflow <session>"}
                session_id = args[0]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])

                if not stack:
                    return {"status": "ok", "workflow_type": None, "depth": 0}

                top = stack[-1]
                return {
                    "status": "ok",
                    "workflow_type": top["workflow_type"],
                    "current_phase": top.get("current_phase"),
                    "depth": len(stack)
                }

            elif cmd == "get-workflow-stack":
                # Get full stack
                # Usage: get-workflow-stack <session>
                if len(args) < 1:
                    return {"status": "error", "message": "Usage: get-workflow-stack <session>"}
                session_id = args[0]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])

                return {"status": "ok", "stack": stack, "depth": len(stack)}

            elif cmd == "clear-workflow-stack":
                # Clear entire stack (reset)
                # Usage: clear-workflow-stack <session>
                if len(args) < 1:
                    return {"status": "error", "message": "Usage: clear-workflow-stack <session>"}
                session_id = args[0]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    if stack_key in self.state:
                        del self.state[stack_key]

                self.save_state()
                return {"status": "ok", "message": "Stack cleared"}

            elif cmd == "set-workflow-phase":
                # Set current phase for active workflow
                # Usage: set-workflow-phase <session> <phase>
                if len(args) < 2:
                    return {"status": "error", "message": "Usage: set-workflow-phase <session> <phase>"}
                session_id, phase = args[0], args[1]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])
                    if not stack:
                        return {"status": "error", "message": "No active workflow"}
                    stack[-1]["current_phase"] = phase
                    self.state[stack_key] = stack

                self.save_state()
                return {"status": "ok", "phase": phase}

            # =================================================================
            # COMMAND STEP TRACKING COMMANDS
            # =================================================================

            elif cmd == "get-command-step":
                # Get current step for active workflow
                # Usage: get-command-step <session>
                if len(args) < 1:
                    return {"status": "error", "message": "Usage: get-command-step <session>"}
                session_id = args[0]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])

                if not stack:
                    return {"status": "ok", "step": 0, "workflow_type": None}

                workflow_type = stack[-1].get("workflow_type")
                step_key = f"command_step:{session_id}:{workflow_type}"

                with self.lock:
                    step = self.state.get(step_key, 1)

                return {
                    "status": "ok",
                    "step": step,
                    "workflow_type": workflow_type
                }

            elif cmd == "set-command-step":
                # Set current step for active workflow
                # Usage: set-command-step <session> <step>
                if len(args) < 2:
                    return {"status": "error", "message": "Usage: set-command-step <session> <step>"}
                session_id = args[0]
                try:
                    step = int(args[1])
                except ValueError:
                    return {"status": "error", "message": "Step must be an integer"}

                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])

                if not stack:
                    return {"status": "error", "message": "No active workflow"}

                workflow_type = stack[-1].get("workflow_type")
                step_key = f"command_step:{session_id}:{workflow_type}"

                with self.lock:
                    self.state[step_key] = step

                self.save_state()
                return {"status": "ok", "step": step, "workflow_type": workflow_type}

            elif cmd == "advance-command-step":
                # Increment command step by 1
                # Usage: advance-command-step <session>
                if len(args) < 1:
                    return {"status": "error", "message": "Usage: advance-command-step <session>"}
                session_id = args[0]
                stack_key = f"workflow_stack:{session_id}"

                with self.lock:
                    stack = self.state.get(stack_key, [])

                if not stack:
                    return {"status": "error", "message": "No active workflow"}

                workflow_type = stack[-1].get("workflow_type")
                step_key = f"command_step:{session_id}:{workflow_type}"

                with self.lock:
                    current = self.state.get(step_key, 1)
                    self.state[step_key] = current + 1
                    new_step = self.state[step_key]

                self.save_state()
                return {
                    "status": "ok",
                    "previous_step": current,
                    "current_step": new_step,
                    "workflow_type": workflow_type
                }

            else:
                return {"status": "error", "message": f"Unknown command: {cmd}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_client(self, conn: socket.socket, addr):
        """Handle a single client connection."""
        try:
            data = conn.recv(8192)
            if not data:
                return

            request = json.loads(data.decode())
            cmd = request.get("cmd", "status")
            args = request.get("args", [])

            response = self.process_command(cmd, args)
            conn.sendall(json.dumps(response).encode())

        except (json.JSONDecodeError, ConnectionResetError) as e:
            error_response = {"status": "error", "message": str(e)}
            try:
                conn.sendall(json.dumps(error_response).encode())
            except:
                pass
        finally:
            conn.close()

    def start_server(self):
        """Start the socket server."""
        # Remove existing socket
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()

        CLAUDE_DIR.mkdir(parents=True, exist_ok=True)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(str(SOCKET_PATH))
        self.server_socket.listen(10)
        self.server_socket.settimeout(1.0)

        self.running = True

        # Write PID file
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

        self.log(f"Daemon started, listening on {SOCKET_PATH}")

        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.log(f"Accept error: {e}")

        self.cleanup()

    def stop(self):
        """Stop the daemon gracefully."""
        self.running = False

    def cleanup(self):
        """Clean up resources."""
        if self.server_socket:
            self.server_socket.close()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        if PID_FILE.exists():
            PID_FILE.unlink()
        self.log("Daemon stopped")

    def log(self, message: str):
        """Log message to file."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")


def is_daemon_running() -> bool:
    """Check if daemon is running."""
    if PID_FILE.exists():
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, OSError):
            pass
    return False


def send_to_daemon(cmd: str, args: list) -> dict:
    """Send command to running daemon via socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(str(SOCKET_PATH))

        request = {"cmd": cmd, "args": args}
        sock.sendall(json.dumps(request).encode())

        response = sock.recv(8192)
        sock.close()

        return json.loads(response.decode())

    except (socket.error, json.JSONDecodeError) as e:
        return {"status": "error", "message": str(e)}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"status": "ok", "message": "pong"}))
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Daemon control commands
    if cmd == "start":
        if is_daemon_running():
            print(json.dumps({"status": "ok", "message": "already running"}))
            return 0

        daemon = ForgeStateDaemon()

        def signal_handler(sig, frame):
            daemon.stop()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        daemon.start_server()
        return 0

    elif cmd == "stop":
        if PID_FILE.exists():
            try:
                with open(PID_FILE) as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                print(json.dumps({"status": "ok", "message": f"stopped {pid}"}))
            except (ValueError, ProcessLookupError):
                print(json.dumps({"status": "ok", "message": "not running"}))
        else:
            print(json.dumps({"status": "ok", "message": "not running"}))
        return 0

    # Try socket first if daemon is running
    if is_daemon_running():
        response = send_to_daemon(cmd, args)
        print(json.dumps(response))
        return 0

    # CLI mode - process directly (fallback for when daemon not running)
    daemon = ForgeStateDaemon()
    response = daemon.process_command(cmd, args)
    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main())
