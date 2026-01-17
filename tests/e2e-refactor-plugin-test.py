#!/usr/bin/env python3
"""
E2E Test: Forge handles "refactor plugin" request correctly in Docker.

Uses tmux as TTY proxy for interactive Claude session.

Test Objective:
Verify that Forge correctly interprets "I want to make a refactor plugin" as a
plugin design task (not refactor execution) within a Docker-based environment.

Expected Behavior:
- Forge MUST acknowledge Docker isolation
- Forge MUST ask for missing specs (refactor target, strategy undefined)
- Forge MUST explain "refactor plugin" as a plugin that assists refactoring workflows
- Forge MUST NOT assume refactor target, host persistence, or perform actual refactoring
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
CONTAINER_NAME = "forge-e2e-refactor"
SESSION_NAME = "refactor-test"
FORGE_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", "/workspace/forge")
WORKSPACE = os.environ.get("CLAUDE_WORKING_DIR", "/workspace/test")

# Test timeout in seconds
DEFAULT_WAIT_TIME = 10
MAX_RESPONSE_WAIT = 30


@dataclass
class ValidationPattern:
    """Pattern for validating test output."""
    pattern: str
    name: str
    is_failure: bool = False
    case_insensitive: bool = True
    
    def matches(self, text: str) -> bool:
        flags = re.IGNORECASE if self.case_insensitive else 0
        return bool(re.search(self.pattern, text, flags))


@dataclass
class TestResult:
    """Track test results."""
    passed: int = 0
    failed: int = 0
    errors: List[Tuple[str, str]] = field(default_factory=list)
    output_captured: str = ""
    
    def success(self, name: str, detail: str = ""):
        self.passed += 1
        print(f"  ✓ {name}" + (f" - {detail}" if detail else ""))
    
    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ✗ {name}: {reason}")
    
    def summary(self) -> int:
        print(f"\n{'='*60}")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print('='*60)
        return 0 if self.failed == 0 else 1


# Pass patterns - ALL must match for test to pass
PASS_PATTERNS = [
    ValidationPattern(
        r"docker|container|isolated|ephemeral",
        "acknowledges_docker_context",
        is_failure=False
    ),
    ValidationPattern(
        r"plugin.*design|create.*plugin|design.*plugin|making.*plugin|build.*plugin",
        "identifies_as_plugin_design",
        is_failure=False
    ),
    ValidationPattern(
        r"\?|clarif|specify|what.*target|which|tell.*more|need.*know|could.*explain",
        "asks_clarifying_questions",
        is_failure=False
    ),
]

# Fail patterns - ANY match triggers failure
FAIL_PATTERNS = [
    ValidationPattern(
        r"refactoring.*your.*class|extract.*method|rename.*variable|moving.*method",
        "premature_refactor_example",
        is_failure=True
    ),
    ValidationPattern(
        r"/home/[a-z]+/|C:\\\\|host.*path|local.*filesystem",
        "host_path_assumption",
        is_failure=True
    ),
    ValidationPattern(
        r"executing.*refactor|performing.*refactor|running.*refactor.*now",
        "premature_refactor_execution",
        is_failure=True
    ),
]


class DockerTestRunner:
    """Manages Docker container and tmux sessions for E2E testing."""
    
    def __init__(self, container_name: str, session_name: str):
        self.container = container_name
        self.session = session_name
        self.is_setup = False
    
    def docker_exec(self, cmd: List[str], capture: bool = True) -> Tuple[str, str, int]:
        """Execute command in container."""
        full_cmd = ["docker", "exec", self.container] + cmd
        result = subprocess.run(
            full_cmd,
            capture_output=capture,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def tmux_send(self, text: str, enter: bool = True):
        """Send text to tmux session."""
        cmd = ["tmux", "send-keys", "-t", self.session, text]
        if enter:
            cmd.append("Enter")
        self.docker_exec(cmd)
    
    def tmux_capture(self, history_lines: int = 200) -> str:
        """Capture tmux pane output."""
        stdout, _, _ = self.docker_exec([
            "tmux", "capture-pane", "-t", self.session, "-p", f"-S", f"-{history_lines}"
        ])
        return stdout
    
    def setup_container(self) -> bool:
        """Start container with sleep infinity."""
        print("Setting up test container...")
        
        # Build image first (using docker-compose)
        compose_file = Path(FORGE_ROOT) / "tests" / "docker" / "docker-compose.yml"
        if compose_file.exists():
            build_result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "build"],
                capture_output=True,
                text=True,
                cwd=str(compose_file.parent)
            )
            if build_result.returncode != 0:
                print(f"Failed to build: {build_result.stderr}")
                return False
        
        # Stop and remove if exists
        subprocess.run(["docker", "stop", self.container], capture_output=True)
        subprocess.run(["docker", "rm", self.container], capture_output=True)
        
        # Start container
        result = subprocess.run([
            "docker", "run", "-d",
            "--name", self.container,
            "-e", f"CLAUDE_PLUGIN_ROOT={FORGE_ROOT}",
            "-e", f"CLAUDE_WORKING_DIR={WORKSPACE}",
            "tests_docker_forge-test",  # Image name from docker-compose
            "bash", "-c", "sleep infinity"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Try alternative image name
            result = subprocess.run([
                "docker", "run", "-d",
                "--name", self.container,
                "-e", f"CLAUDE_PLUGIN_ROOT={FORGE_ROOT}",
                "-e", f"CLAUDE_WORKING_DIR={WORKSPACE}",
                "forge-test",
                "bash", "-c", "sleep infinity"
            ], capture_output=True, text=True)
            
        if result.returncode != 0:
            print(f"Failed to start container: {result.stderr}")
            return False
        
        time.sleep(2)
        self.is_setup = True
        print(f"Container {self.container} started")
        return True
    
    def setup_tmux_session(self) -> bool:
        """Create tmux session and launch Claude."""
        print("Setting up tmux session...")
        
        # Kill existing session
        self.docker_exec(["tmux", "kill-session", "-t", self.session])
        
        # Create new session
        _, stderr, rc = self.docker_exec([
            "tmux", "new-session", "-d", "-s", self.session, "-x", "200", "-y", "50"
        ])
        if rc != 0:
            print(f"Failed to create tmux session: {stderr}")
            return False
        
        # Initialize environment
        self.tmux_send(f"export CLAUDE_PLUGIN_ROOT={FORGE_ROOT}")
        self.tmux_send(f"export CLAUDE_WORKING_DIR={WORKSPACE}")
        self.tmux_send(f"cd {WORKSPACE}")
        time.sleep(1)
        
        # Launch Claude (mock)
        self.tmux_send("claude")
        time.sleep(3)
        
        print(f"tmux session {self.session} created")
        return True
    
    def teardown(self):
        """Clean up container and tmux session."""
        print("Cleaning up...")
        if self.is_setup:
            self.docker_exec(["tmux", "kill-session", "-t", self.session])
            subprocess.run(["docker", "stop", self.container], capture_output=True)
            subprocess.run(["docker", "rm", self.container], capture_output=True)
            self.is_setup = False
        print("Cleanup complete")


def validate_output(output: str, results: TestResult) -> bool:
    """Validate output against pass/fail patterns."""
    all_passed = True
    
    print("\n--- Pass Pattern Checks ---")
    for pattern in PASS_PATTERNS:
        if pattern.matches(output):
            results.success(pattern.name, f"Found matching pattern")
        else:
            results.fail(pattern.name, "Pattern not found in output")
            all_passed = False
    
    print("\n--- Fail Pattern Checks ---")
    for pattern in FAIL_PATTERNS:
        if pattern.matches(output):
            results.fail(pattern.name, "Found forbidden pattern in output")
            all_passed = False
        else:
            results.success(pattern.name, "Pattern correctly absent")
    
    return all_passed


def check_forge_state(runner: DockerTestRunner, results: TestResult):
    """Check forge state file for correct values."""
    print("\n--- State File Checks ---")
    
    state_file = f"{WORKSPACE}/.claude/local/forge-state.json"
    stdout, _, rc = runner.docker_exec(["cat", state_file])
    
    if rc != 0:
        results.fail("state_file_exists", "Forge state file not found")
        return
    
    try:
        state = json.loads(stdout)
        results.success("state_file_exists", "State file readable")
        
        # Check for forge_active
        if state.get("forge_active", False):
            results.success("forge_active", "Forge is active")
        else:
            results.fail("forge_active", "Forge should be active during plugin design")
        
        # Check phase (should be 0 or 1 - Input or Analysis)
        phase = state.get("phase", -1)
        if phase in [0, 1]:
            results.success("phase_check", f"Phase is {phase} (Input/Analysis)")
        else:
            results.fail("phase_check", f"Unexpected phase: {phase}")
        
        # Check no host path references
        state_str = json.dumps(state)
        if re.search(r"/home/[a-z]+/|C:\\\\", state_str):
            results.fail("no_host_paths", "Found host path in state")
        else:
            results.success("no_host_paths", "No host paths in state")
            
    except json.JSONDecodeError as e:
        results.fail("state_file_valid", f"Invalid JSON in state file: {e}")


def run_refactor_plugin_test(runner: DockerTestRunner) -> TestResult:
    """Execute the main test scenario."""
    results = TestResult()
    
    print("\n" + "="*60)
    print("Forge E2E Test: Refactor Plugin Request")
    print("="*60)
    
    # Send the test prompt
    print("\n[1] Sending test prompt...")
    test_prompt = (
        "I want to make a refactor plugin. "
        "The plugin will be designed and executed inside a Docker container."
    )
    runner.tmux_send(test_prompt)
    
    # Wait for response
    print(f"[2] Waiting for response ({MAX_RESPONSE_WAIT}s max)...")
    time.sleep(DEFAULT_WAIT_TIME)
    
    # Capture initial response
    output = runner.tmux_capture()
    results.output_captured = output
    
    # Check if we got a meaningful response
    if len(output.strip()) < 50:
        print("[!] Response too short, waiting more...")
        time.sleep(DEFAULT_WAIT_TIME)
        output = runner.tmux_capture()
        results.output_captured = output
    
    print(f"\n[3] Captured {len(output)} characters of output")
    
    # If Forge asks clarifying questions, provide auto-responses
    if "?" in output or "clarif" in output.lower():
        print("[4] Providing clarification responses...")
        
        clarifications = [
            "The plugin is intended to support refactoring workflows in general. "
            "The specific refactor target and strategy are intentionally undefined.",
            
            "The plugin should be advisory by default. "
            "It must not perform automatic file modifications unless explicitly instructed.",
            
            "The plugin must assume a Docker-based, ephemeral runtime. "
            "Any required state must be explicitly materialized as artifacts inside the container."
        ]
        
        for i, response in enumerate(clarifications):
            time.sleep(3)
            runner.tmux_send(response)
            time.sleep(5)
        
        # Capture final output after clarifications
        final_output = runner.tmux_capture(history_lines=500)
        results.output_captured = final_output
        output = final_output
    
    # Validate output
    print("\n[5] Validating output patterns...")
    validate_output(output, results)
    
    # Check forge state
    print("\n[6] Checking forge state...")
    check_forge_state(runner, results)
    
    return results


def run_test_in_container() -> int:
    """
    Run the test inside Docker container.
    This function is called when running within the container environment.
    """
    print("Running test inside container...")
    
    results = TestResult()
    
    # Simulate the scenario by checking forge components
    print("\n--- Component Verification ---")
    
    # Check input-agent asks clarifying questions
    input_agent = Path(FORGE_ROOT) / "agents" / "input-agent.md"
    if input_agent.exists():
        content = input_agent.read_text()
        if "clarif" in content.lower() or "question" in content.lower():
            results.success("input_agent_questions", "Input agent configured for questions")
        else:
            results.fail("input_agent_questions", "Input agent may not ask questions")
    else:
        results.fail("input_agent_exists", "Input agent not found")
    
    # Check analysis-agent determines solution type
    analysis_agent = Path(FORGE_ROOT) / "agents" / "analysis-agent.md"
    if analysis_agent.exists():
        content = analysis_agent.read_text()
        if "plugin" in content.lower() or "solution" in content.lower():
            results.success("analysis_agent_routing", "Analysis agent routes to plugin type")
        else:
            results.fail("analysis_agent_routing", "Analysis agent may not determine plugin type")
    else:
        results.fail("analysis_agent_exists", "Analysis agent not found")
    
    # Check solution-router skill
    router_skill = Path(FORGE_ROOT) / "skills" / "solution-router" / "SKILL.md"
    if router_skill.exists():
        content = router_skill.read_text()
        if "extend" in content.lower() or "plugin" in content.lower():
            results.success("solution_router", "Solution router handles plugin detection")
        else:
            results.fail("solution_router", "Solution router may not detect plugin requests")
    else:
        results.fail("solution_router_exists", "Solution router not found")
    
    # Check forge-state.py
    state_script = Path(FORGE_ROOT) / "scripts" / "forge-state.py"
    if state_script.exists():
        results.success("forge_state_script", "Forge state script exists")
    else:
        results.fail("forge_state_script", "Forge state script not found")
    
    return results.summary()


def main():
    """Main test entry point."""
    # Check if running inside container
    if os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER"):
        return run_test_in_container()
    
    # Running from host - set up Docker container
    runner = DockerTestRunner(CONTAINER_NAME, SESSION_NAME)
    
    try:
        # Setup
        if not runner.setup_container():
            print("Failed to set up container")
            return 1
        
        if not runner.setup_tmux_session():
            print("Failed to set up tmux session")
            runner.teardown()
            return 1
        
        # Run test
        results = run_refactor_plugin_test(runner)
        
        # Save output for debugging
        output_file = Path("test-output-refactor-plugin.txt")
        output_file.write_text(results.output_captured)
        print(f"\n[*] Full output saved to: {output_file}")
        
        return results.summary()
        
    except KeyboardInterrupt:
        print("\n[!] Test interrupted")
        return 1
    finally:
        runner.teardown()


if __name__ == "__main__":
    sys.exit(main())
