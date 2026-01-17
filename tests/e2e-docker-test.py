#!/usr/bin/env python3
"""
Forge E2E Docker Test Suite

Runs comprehensive end-to-end tests for the Forge workflow in an isolated
Docker container. Tests the full 6-phase workflow including:
- State management via daemon
- Hook execution
- Phase transitions (6 phases: Input, Analysis, Design, Preview, Execute, Validate)
- Confirmation gates
- Error recovery
- Marketplace validation
- Plugin invocation
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


# Configuration
FORGE_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", "/workspace/forge")
WORKSPACE = os.environ.get("CLAUDE_WORKING_DIR", "/workspace/test")
SOCKET_PATH = Path(WORKSPACE) / ".claude" / "local" / "forge.sock"
STATE_FILE = Path(WORKSPACE) / ".claude" / "local" / "forge-state.json"


class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def success(self, name: str):
        self.passed += 1
        print(f"  ✓ {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ✗ {name}: {reason}")

    def summary(self) -> int:
        print(f"\n{'='*50}")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print('='*50)
        return 0 if self.failed == 0 else 1


def send_command(cmd: dict, timeout: float = 2.0) -> dict:
    """Send command to forge daemon."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(str(SOCKET_PATH))
        sock.sendall((json.dumps(cmd) + "\n").encode('utf-8'))
        
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
        return {"error": str(e)}


def run_forge_cli(args: str) -> dict:
    """Run forge-state.py CLI command."""
    cmd = f"python3 {FORGE_ROOT}/scripts/forge-state.py {args}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return json.loads(result.stdout) if result.stdout else {"error": result.stderr}
    except json.JSONDecodeError:
        return {"output": result.stdout, "error": result.stderr}


def wait_for_daemon(max_attempts: int = 10) -> bool:
    """Wait for daemon to become available."""
    for _ in range(max_attempts):
        if SOCKET_PATH.exists():
            result = send_command({"cmd": "get"})
            if "error" not in result:
                return True
        time.sleep(0.5)
    return False


def test_daemon_connection(results: TestResult):
    """Test daemon is running and responsive."""
    if not wait_for_daemon():
        results.fail("daemon_connection", "Daemon not responding")
        return
    
    response = send_command({"cmd": "get"})
    if "error" in response:
        results.fail("daemon_connection", response["error"])
    else:
        results.success("daemon_connection")


def test_activation(results: TestResult):
    """Test forge activation."""
    # Ensure deactivated first
    send_command({"cmd": "deactivate"})
    
    # Activate
    response = send_command({"cmd": "activate"})
    if not response.get("success"):
        results.fail("activation", f"Failed to activate: {response}")
        return
    
    # Verify state
    state = send_command({"cmd": "get"})
    if state.get("forge_active") and state.get("phase") == 0:
        results.success("activation")
    else:
        results.fail("activation", f"Invalid state after activation: {state}")


def test_phase_progression(results: TestResult):
    """Test phase progression through workflow."""
    # Reset and activate
    send_command({"cmd": "deactivate"})
    send_command({"cmd": "activate"})
    
    # Phase 0 -> 1 (Input -> Analysis)
    response = send_command({"cmd": "checkpoint", "agent": "forge:input-agent"})
    if response.get("advanced") and response.get("to_phase") == 1:
        results.success("phase_0_to_1")
    else:
        results.fail("phase_0_to_1", f"Failed: {response}")
        return
    
    # Phase 1 -> 2 (Analysis -> Design)
    response = send_command({"cmd": "checkpoint", "agent": "forge:analysis-agent"})
    if response.get("advanced") and response.get("to_phase") == 2:
        results.success("phase_1_to_2")
    else:
        results.fail("phase_1_to_2", f"Failed: {response}")
        return
    
    # Phase 2 -> 3 (Design -> Preview)
    response = send_command({"cmd": "checkpoint", "agent": "forge:design-agent"})
    if response.get("advanced") and response.get("to_phase") == 3:
        results.success("phase_2_to_3")
    else:
        results.fail("phase_2_to_3", f"Failed: {response}")
        return
    
    # Phase 3 -> 4 (Preview -> Execute)
    response = send_command({"cmd": "checkpoint", "agent": "forge:preview-agent"})
    if response.get("advanced") and response.get("to_phase") == 4:
        results.success("phase_3_to_4")
    else:
        results.fail("phase_3_to_4", f"Failed: {response}")


def test_confirmation_gate(results: TestResult):
    """Test that Execute phase requires confirmation."""
    # Set up at phase 4 (Execute) without confirmation
    send_command({"cmd": "deactivate"})
    send_command({"cmd": "activate"})
    send_command({"cmd": "set-phase", "phase": 4})
    
    # Try checkpoint without confirmation - should fail
    response = send_command({"cmd": "checkpoint", "agent": "forge:execute-agent"})
    if not response.get("success") and "confirmation" in response.get("error", "").lower():
        results.success("confirmation_required")
    else:
        results.fail("confirmation_required", f"Should require confirmation: {response}")
        return
    
    # Confirm and retry
    send_command({"cmd": "confirm"})
    response = send_command({"cmd": "checkpoint", "agent": "forge:execute-agent"})
    if response.get("success") or response.get("advanced"):
        results.success("confirmation_unlocks")
    else:
        results.fail("confirmation_unlocks", f"Failed after confirmation: {response}")


def test_workflow_completion(results: TestResult):
    """Test full 6-phase workflow completion."""
    send_command({"cmd": "deactivate"})
    send_command({"cmd": "activate"})
    
    # Run through all 6 phases
    agents = [
        "forge:input-agent",     # Phase 0
        "forge:analysis-agent",  # Phase 1
        "forge:design-agent",    # Phase 2
        "forge:preview-agent",   # Phase 3
        "forge:execute-agent",   # Phase 4
        "forge:validate-agent"   # Phase 5
    ]
    
    for i, agent in enumerate(agents):
        # Confirm before execute phase (phase 4)
        if i == 4:
            send_command({"cmd": "confirm"})
        
        response = send_command({"cmd": "checkpoint", "agent": agent})
        if "error" in response:
            results.fail("workflow_completion", f"Failed at {agent}: {response}")
            return
    
    # Check completion
    state = send_command({"cmd": "get"})
    if not state.get("forge_active"):
        results.success("workflow_completion")
    else:
        results.fail("workflow_completion", f"Should be deactivated: {state}")


def test_wrong_agent_rejection(results: TestResult):
    """Test that wrong agent for phase is rejected."""
    send_command({"cmd": "deactivate"})
    send_command({"cmd": "activate"})  # Phase 0
    
    # Try to run analysis agent at phase 0 (should be input agent)
    response = send_command({"cmd": "checkpoint", "agent": "forge:analysis-agent"})
    if not response.get("success") and "does not match" in response.get("error", ""):
        results.success("wrong_agent_rejection")
    else:
        results.fail("wrong_agent_rejection", f"Should reject wrong agent: {response}")


def test_deactivation(results: TestResult):
    """Test forge deactivation."""
    send_command({"cmd": "activate"})
    response = send_command({"cmd": "deactivate"})
    
    if response.get("success"):
        state = send_command({"cmd": "get"})
        if not state.get("forge_active"):
            results.success("deactivation")
        else:
            results.fail("deactivation", "Still active after deactivate")
    else:
        results.fail("deactivation", f"Failed: {response}")


def test_cli_commands(results: TestResult):
    """Test forge-state.py CLI commands."""
    # Deactivate first
    run_forge_cli("deactivate")
    
    # Test get
    response = run_forge_cli("get")
    if "forge_active" in str(response):
        results.success("cli_get")
    else:
        results.fail("cli_get", f"Unexpected response: {response}")
    
    # Test activate
    response = run_forge_cli("activate")
    if response.get("success"):
        results.success("cli_activate")
    else:
        results.fail("cli_activate", f"Failed: {response}")
    
    # Clean up
    run_forge_cli("deactivate")


def test_state_persistence(results: TestResult):
    """Test that state persists to file."""
    send_command({"cmd": "deactivate"})
    send_command({"cmd": "activate"})
    send_command({"cmd": "checkpoint", "agent": "forge:input-agent"})
    
    # Check state file exists and has correct content
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
        if state.get("phase") == 1 and state.get("forge_active"):
            results.success("state_persistence")
        else:
            results.fail("state_persistence", f"Invalid state in file: {state}")
    else:
        results.fail("state_persistence", "State file not found")


def test_marketplace_validation(results: TestResult):
    """Test marketplace.json validation using schema validator."""
    validator = f"{FORGE_ROOT}/scripts/schema-validator.py"
    
    # Run schema validator on forge plugin
    cmd = f"python3 {validator} {FORGE_ROOT} --json"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    try:
        output = json.loads(result.stdout) if result.stdout else {}
        errors = output.get("errors", [])
        
        # Handle both integer (count) and list (error details) formats
        error_count = len(errors) if isinstance(errors, list) else errors
        
        if error_count == 0:
            results.success("marketplace_schema_valid")
        else:
            results.fail("marketplace_schema_valid", f"Found {error_count} errors")
    except json.JSONDecodeError:
        # Non-JSON output, check return code
        if result.returncode == 0:
            results.success("marketplace_schema_valid")
        else:
            results.fail("marketplace_schema_valid", result.stderr[:200] if result.stderr else "Unknown error")


def test_plugin_invocation(results: TestResult):
    """Test that plugin components can be invoked (paths exist and are valid)."""
    plugin_json = Path(FORGE_ROOT) / "plugin.json"
    
    if not plugin_json.exists():
        results.fail("plugin_json_exists", "plugin.json not found")
        return
    
    try:
        with open(plugin_json) as f:
            manifest = json.load(f)
        results.success("plugin_json_valid")
    except json.JSONDecodeError as e:
        results.fail("plugin_json_valid", f"Invalid JSON: {e}")
        return
    
    # Check skills exist
    skills = manifest.get("skills", [])
    skills_found = 0
    for skill in skills:
        skill_path = Path(FORGE_ROOT) / skill.get("path", "")
        if skill_path.exists():
            skills_found += 1
    
    if skills_found == len(skills) and skills:
        results.success(f"skills_discoverable ({skills_found}/{len(skills)})")
    elif skills:
        results.fail(f"skills_discoverable", f"Only {skills_found}/{len(skills)} found")
    
    # Check commands exist
    commands = manifest.get("commands", [])
    commands_found = 0
    for cmd in commands:
        cmd_path = Path(FORGE_ROOT) / cmd.get("path", "")
        if cmd_path.exists():
            commands_found += 1
    
    if commands_found == len(commands) and commands:
        results.success(f"commands_discoverable ({commands_found}/{len(commands)})")
    elif commands:
        results.fail(f"commands_discoverable", f"Only {commands_found}/{len(commands)} found")
    
    # Check agents exist
    agents = manifest.get("agents", [])
    agents_found = 0
    for agent in agents:
        agent_path = Path(FORGE_ROOT) / agent.get("path", "")
        if agent_path.exists():
            agents_found += 1
    
    if agents_found == len(agents) and agents:
        results.success(f"agents_discoverable ({agents_found}/{len(agents)})")
    elif agents:
        results.fail(f"agents_discoverable", f"Only {agents_found}/{len(agents)} found")


def test_forge_workflow_6phase(results: TestResult):
    """Test complete 6-phase Forge workflow with phase name verification."""
    EXPECTED_PHASES = [
        (0, "Input", "forge:input-agent"),
        (1, "Analysis", "forge:analysis-agent"),
        (2, "Design", "forge:design-agent"),
        (3, "Preview", "forge:preview-agent"),
        (4, "Execute", "forge:execute-agent"),
        (5, "Validate", "forge:validate-agent"),
    ]
    
    # Reset
    send_command({"cmd": "deactivate"})
    send_command({"cmd": "activate"})
    
    for phase_num, phase_name, agent in EXPECTED_PHASES:
        # Confirm before Execute phase
        if phase_num == 4:
            send_command({"cmd": "confirm"})
        
        response = send_command({"cmd": "checkpoint", "agent": agent})
        
        # Last phase completes workflow
        if phase_num == 5:
            if response.get("success") or not response.get("error"):
                results.success(f"6phase_{phase_num}_{phase_name}")
            else:
                results.fail(f"6phase_{phase_num}_{phase_name}", f"Failed: {response}")
                return
        elif response.get("advanced"):
            results.success(f"6phase_{phase_num}_{phase_name}")
        else:
            results.fail(f"6phase_{phase_num}_{phase_name}", f"Failed: {response}")
            return
    
    # Verify workflow completion (forge should be deactivated)
    state = send_command({"cmd": "get"})
    if not state.get("forge_active"):
        results.success("6phase_workflow_completes")
    else:
        results.fail("6phase_workflow_completes", "Should be deactivated after completion")


def run_all_tests():
    """Run all E2E tests."""
    print("="*50)
    print("Forge E2E Docker Test Suite")
    print("="*50)
    print(f"Workspace: {WORKSPACE}")
    print(f"Plugin root: {FORGE_ROOT}")
    print(f"Socket: {SOCKET_PATH}")
    print("="*50 + "\n")
    
    results = TestResult()
    
    print("Connection Tests:")
    test_daemon_connection(results)
    
    print("\nMarketplace & Plugin Tests:")
    test_marketplace_validation(results)
    test_plugin_invocation(results)
    
    print("\nWorkflow Tests:")
    test_activation(results)
    test_phase_progression(results)
    test_confirmation_gate(results)
    test_wrong_agent_rejection(results)
    test_workflow_completion(results)
    test_forge_workflow_6phase(results)
    test_deactivation(results)
    
    print("\nCLI Tests:")
    test_cli_commands(results)
    
    print("\nPersistence Tests:")
    test_state_persistence(results)
    
    return results.summary()


if __name__ == "__main__":
    sys.exit(run_all_tests())
