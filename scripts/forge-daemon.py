#!/usr/bin/env python3
"""
Forge Daemon - Socket-based state server for Forge plugin workflow.

Manages project-scoped state via Unix socket for fast access.
Socket location: <workspace>/.claude/local/forge.sock

Enhanced with:
- 6-phase workflow (added Preview phase)
- Design versioning with hash
- Reconfirmation on design change
- Rollback capability
"""

import hashlib
import json
import os
import socket
import sys
import time
import threading
from pathlib import Path
from typing import Optional

# Phase configuration (6 phases with Preview)
PHASES = {
    0: {
        "name": "Input",
        "agent": "forge:input-agent",
        "guidance": "Normalize user intent into clear problem statement",
        "next": "Run phase 1 (Analysis)"
    },
    1: {
        "name": "Analysis",
        "agent": "forge:analysis-agent",
        "guidance": "Analyze codebase and describe reality",
        "next": "Run phase 2 (Design)"
    },
    2: {
        "name": "Design",
        "agent": "forge:design-agent",
        "guidance": "Propose design options with trade-offs",
        "next": "Run phase 3 (Preview) - review changes before execution"
    },
    3: {
        "name": "Preview",
        "agent": "forge:preview-agent",
        "guidance": "Preview changes that will be made (dry-run)",
        "next": "Run phase 4 (Execute) - requires user confirmation"
    },
    4: {
        "name": "Execute",
        "agent": "forge:execute-agent",
        "guidance": "Implement the confirmed design",
        "next": "Run phase 5 (Validate)"
    },
    5: {
        "name": "Validate",
        "agent": "forge:validate-agent",
        "guidance": "Validate plugin structure and schema",
        "next": "Complete - workflow finished"
    }
}

MAX_PHASE = 5
IDLE_TIMEOUT = 300  # 5 minutes idle timeout


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class ForgeState:
    """Manages forge workflow state with versioning."""

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.state_dir = Path(workspace_root) / ".claude" / "local"
        self.state_file = self.state_dir / "forge-state.json"
        self.socket_path = self.state_dir / "forge.sock"
        self._load_or_init()

    def _load_or_init(self):
        """Load existing state or initialize new state."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                # Validate workspace ownership
                if self.state.get("workspace_root") != self.workspace_root:
                    self._init_state()
            except (json.JSONDecodeError, IOError):
                self._init_state()
        else:
            self._init_state()

    def _init_state(self):
        """Initialize fresh state with versioning fields."""
        self.state = {
            "forge_active": False,
            "workspace_root": self.workspace_root,
            "phase": 0,
            "confirmed": False,
            "checkpoints": [],
            # Versioning fields
            "design_hash": None,
            "design_confirmed_at": None,
            "requires_reconfirmation": False,
            # Rollback tracking
            "rollback_points": []
        }
        self._save()

    def _save(self):
        """Persist state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get(self) -> dict:
        """Return full state."""
        return self.state.copy()

    def get_phase(self) -> int:
        """Return current phase number."""
        return self.state["phase"]

    def is_active(self) -> bool:
        """Return whether forge is active."""
        return self.state["forge_active"]

    def activate(self) -> dict:
        """Activate forge workflow."""
        self.state["forge_active"] = True
        self.state["phase"] = 0
        self.state["confirmed"] = False
        self.state["checkpoints"] = []
        self.state["design_hash"] = None
        self.state["design_confirmed_at"] = None
        self.state["requires_reconfirmation"] = False
        self.state["rollback_points"] = []
        self._save()
        return {"success": True, "phase": 0, "guidance": PHASES[0]["guidance"]}

    def deactivate(self) -> dict:
        """Deactivate forge workflow."""
        self.state["forge_active"] = False
        self._save()
        return {"success": True}

    def confirm(self) -> dict:
        """Set confirmed flag for Execute phase."""
        # Confirmation now happens at phase 4 (Execute) after Preview
        if self.state["phase"] != 4:
            return {"success": False, "error": "Confirmation only valid for Execute phase (4)"}
        
        # Check if reconfirmation is required
        if self.state.get("requires_reconfirmation"):
            self.state["requires_reconfirmation"] = False
        
        self.state["confirmed"] = True
        self.state["design_confirmed_at"] = int(time.time())
        self._save()
        return {"success": True, "phase": 4, "guidance": PHASES[4]["guidance"]}

    def set_design_hash(self, design_content: str) -> dict:
        """Store hash of design for version tracking."""
        new_hash = compute_hash(design_content)
        old_hash = self.state.get("design_hash")
        
        # If design changed after confirmation, require reconfirmation
        if old_hash and old_hash != new_hash and self.state.get("confirmed"):
            self.state["requires_reconfirmation"] = True
            self.state["confirmed"] = False
        
        self.state["design_hash"] = new_hash
        self._save()
        
        return {
            "success": True,
            "hash": new_hash,
            "changed": old_hash is not None and old_hash != new_hash,
            "requires_reconfirmation": self.state.get("requires_reconfirmation", False)
        }

    def add_rollback_point(self, description: str, git_sha: str = None) -> dict:
        """Add a rollback point for recovery."""
        point = {
            "phase": self.state["phase"],
            "description": description,
            "ts": int(time.time()),
            "git_sha": git_sha
        }
        self.state["rollback_points"].append(point)
        self._save()
        return {"success": True, "point": point}

    def get_rollback_points(self) -> list:
        """Get all rollback points."""
        return self.state.get("rollback_points", [])

    def checkpoint(self, agent: str) -> dict:
        """Record checkpoint and advance phase if agent matches."""
        if not self.state["forge_active"]:
            return {"success": False, "error": "Forge not active"}

        current_phase = self.state["phase"]
        expected_agent = PHASES[current_phase]["agent"]

        # Check if agent matches expected
        if agent != expected_agent:
            return {
                "success": False,
                "error": f"Agent {agent} does not match expected {expected_agent} for phase {current_phase}"
            }

        # For Execute phase (4), require confirmation
        if current_phase == 4 and not self.state["confirmed"]:
            return {
                "success": False,
                "error": "Execute phase requires user confirmation first"
            }
        
        # Check if reconfirmation is needed
        if current_phase == 4 and self.state.get("requires_reconfirmation"):
            return {
                "success": False,
                "error": "Design was modified - reconfirmation required"
            }

        # Record checkpoint
        checkpoint = {
            "phase": current_phase,
            "agent": agent,
            "ts": int(time.time())
        }
        self.state["checkpoints"].append(checkpoint)

        # Advance phase
        if current_phase < MAX_PHASE:
            self.state["phase"] = current_phase + 1
            next_phase = PHASES[current_phase + 1]
            self._save()
            return {
                "success": True,
                "advanced": True,
                "from_phase": current_phase,
                "to_phase": current_phase + 1,
                "guidance": next_phase["guidance"],
                "next": next_phase["next"]
            }
        else:
            # Final phase completed - deactivate
            self.state["forge_active"] = False
            self._save()
            return {
                "success": True,
                "advanced": False,
                "completed": True,
                "message": "Forge workflow completed"
            }

    def set_phase(self, phase: int) -> dict:
        """Manually set phase (for debugging/recovery)."""
        if phase < 0 or phase > MAX_PHASE:
            return {"success": False, "error": f"Phase must be 0-{MAX_PHASE}"}
        self.state["phase"] = phase
        self.state["confirmed"] = False  # Reset confirmation
        self._save()
        return {"success": True, "phase": phase, "guidance": PHASES[phase]["guidance"]}


class ForgeDaemon:
    """Unix socket server for forge state management."""

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.forge_state = ForgeState(workspace_root)
        self.socket_path = self.forge_state.socket_path
        self.running = False
        self.last_activity = time.time()
        self.server_socket: Optional[socket.socket] = None

    def handle_command(self, data: dict) -> dict:
        """Process incoming command and return response."""
        self.last_activity = time.time()
        cmd = data.get("cmd", "")

        if cmd == "get":
            return self.forge_state.get()
        elif cmd == "get-phase":
            return {"phase": self.forge_state.get_phase()}
        elif cmd == "is-active":
            return {"active": self.forge_state.is_active()}
        elif cmd == "activate":
            return self.forge_state.activate()
        elif cmd == "deactivate":
            return self.forge_state.deactivate()
        elif cmd == "confirm":
            return self.forge_state.confirm()
        elif cmd == "checkpoint":
            agent = data.get("agent", "")
            return self.forge_state.checkpoint(agent)
        elif cmd == "set-phase":
            phase = data.get("phase", 0)
            return self.forge_state.set_phase(phase)
        elif cmd == "set-design-hash":
            content = data.get("content", "")
            return self.forge_state.set_design_hash(content)
        elif cmd == "add-rollback":
            desc = data.get("description", "")
            sha = data.get("git_sha")
            return self.forge_state.add_rollback_point(desc, sha)
        elif cmd == "get-rollbacks":
            return {"rollback_points": self.forge_state.get_rollback_points()}
        elif cmd == "phases":
            return {"phases": PHASES}
        elif cmd == "shutdown":
            self.running = False
            return {"success": True, "message": "Daemon shutting down"}
        else:
            return {"error": f"Unknown command: {cmd}"}

    def handle_client(self, client_socket: socket.socket):
        """Handle a single client connection."""
        try:
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break

            if data:
                try:
                    request = json.loads(data.decode('utf-8').strip())
                    response = self.handle_command(request)
                except json.JSONDecodeError:
                    response = {"error": "Invalid JSON"}

                client_socket.sendall((json.dumps(response) + "\n").encode('utf-8'))
        except Exception as e:
            try:
                client_socket.sendall((json.dumps({"error": str(e)}) + "\n").encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()

    def idle_checker(self):
        """Check for idle timeout and shutdown if inactive."""
        while self.running:
            time.sleep(30)
            if not self.forge_state.is_active():
                idle_time = time.time() - self.last_activity
                if idle_time > IDLE_TIMEOUT:
                    print(f"Idle timeout ({IDLE_TIMEOUT}s) - shutting down", file=sys.stderr)
                    self.running = False
                    # Close server socket to unblock accept()
                    if self.server_socket:
                        try:
                            self.server_socket.close()
                        except:
                            pass
                    break

    def run(self):
        """Start the daemon server."""
        # Remove existing socket
        if self.socket_path.exists():
            self.socket_path.unlink()

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(str(self.socket_path))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)  # Allow periodic checks

        self.running = True

        # Start idle checker thread
        idle_thread = threading.Thread(target=self.idle_checker, daemon=True)
        idle_thread.start()

        print(f"Forge daemon started at {self.socket_path}", file=sys.stderr)

        try:
            while self.running:
                try:
                    client_socket, _ = self.server_socket.accept()
                    # Handle client in thread for non-blocking
                    thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    thread.start()
                except socket.timeout:
                    continue
                except OSError:
                    # Socket closed
                    break
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except:
                pass
        print("Forge daemon stopped", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: forge-daemon.py <workspace_root>", file=sys.stderr)
        sys.exit(1)

    workspace_root = sys.argv[1]

    if not os.path.isdir(workspace_root):
        print(f"Error: {workspace_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    daemon = ForgeDaemon(workspace_root)
    daemon.run()


if __name__ == "__main__":
    main()
