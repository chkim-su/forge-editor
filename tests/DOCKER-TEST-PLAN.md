# Forge Docker Test Plan

Comprehensive E2E test coverage for the Forge plugin in isolated Docker environment.

## Test Categories

### 1. Daemon Lifecycle Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| D-001 | `test_daemon_start` | Start daemon via CLI | Socket file created, responds to `get` |
| D-002 | `test_daemon_stop` | Stop daemon via `shutdown` command | Socket removed, process exits |
| D-003 | `test_daemon_idle_timeout` | Daemon auto-shuts down after idle | Exits after 300s of inactivity |
| D-004 | `test_daemon_multiple_clients` | Handle concurrent connections | All clients get responses |
| D-005 | `test_daemon_restart` | Restart daemon after crash | State preserved from file |
| D-006 | `test_daemon_socket_cleanup` | Stale socket handling | Removes old socket on start |

### 2. State Management Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| S-001 | `test_state_initialization` | Fresh state creation | Default values set correctly |
| S-002 | `test_state_activation` | Activate workflow | `forge_active=true`, `phase=0` |
| S-003 | `test_state_deactivation` | Deactivate workflow | `forge_active=false` |
| S-004 | `test_state_persistence` | State survives daemon restart | Same state after restart |
| S-005 | `test_state_workspace_guard` | Reject state from other workspace | Error if workspace mismatch |
| S-006 | `test_checkpoint_recording` | Record phase checkpoints | Checkpoint array updated |

### 3. Phase Progression Tests (6 Phases)

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| P-001 | `test_phase_0_to_1` | Input → Analysis | Phase advances to 1 |
| P-002 | `test_phase_1_to_2` | Analysis → Design | Phase advances to 2 |
| P-003 | `test_phase_2_to_3` | Design → Preview | Phase advances to 3 |
| P-004 | `test_phase_3_to_4` | Preview → Execute | Phase advances to 4 |
| P-005 | `test_phase_4_to_5` | Execute → Validate | Phase advances to 5 |
| P-006 | `test_phase_5_completion` | Validate → Complete | `forge_active=false` |
| P-007 | `test_wrong_agent_rejection` | Wrong agent at wrong phase | Error: does not match |
| P-008 | `test_full_workflow` | All 6 phases in sequence | Completes successfully |

### 4. Confirmation Gate Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| C-001 | `test_execute_requires_confirmation` | Checkpoint at phase 4 without confirm | Error: requires confirmation |
| C-002 | `test_confirmation_unlocks_execute` | Confirm then checkpoint | Phase advances |
| C-003 | `test_confirm_pattern_yes` | "yes" triggers confirmation | `confirmed=true` |
| C-004 | `test_confirm_pattern_proceed` | "proceed" triggers confirmation | `confirmed=true` |
| C-005 | `test_confirm_pattern_lgtm` | "lgtm" triggers confirmation | `confirmed=true` |
| C-006 | `test_confirm_wrong_phase` | Confirm at non-execute phase | Error: only valid for phase 4 |

### 5. Strict Enforcement Tests (PreToolUse Blocking)

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| E-001 | `test_phase_0_blocks_write` | Write tool at phase 0 | `decision: block` |
| E-002 | `test_phase_0_blocks_edit` | Edit tool at phase 0 | `decision: block` |
| E-003 | `test_phase_0_blocks_bash` | Bash tool at phase 0 | `decision: block` |
| E-004 | `test_phase_0_allows_read` | Read tool at phase 0 | `decision: approve` |
| E-005 | `test_phase_1_allows_all` | Any tool at phase 1 | `decision: approve` |
| E-006 | `test_phase_2_blocks_write` | Write tool at phase 2 | `decision: block` |
| E-007 | `test_phase_2_allows_bash` | Bash tool at phase 2 | `decision: approve` |
| E-008 | `test_phase_3_blocks_write` | Write tool at phase 3 | `decision: block` |
| E-009 | `test_phase_4_blocks_unconfirmed` | Write at phase 4 unconfirmed | `decision: block` |
| E-010 | `test_phase_4_allows_confirmed` | Write at phase 4 confirmed | `decision: approve` |
| E-011 | `test_phase_5_allows_all` | Any tool at phase 5 | `decision: approve` |

### 6. Design Versioning Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| V-001 | `test_set_design_hash` | Store design hash | Hash stored in state |
| V-002 | `test_design_hash_change` | Hash changes on new content | New hash, `changed=true` |
| V-003 | `test_reconfirmation_required` | Design changes after confirm | `requires_reconfirmation=true` |
| V-004 | `test_reconfirmation_blocks` | Checkpoint with reconfirm needed | Error: reconfirmation required |
| V-005 | `test_reconfirmation_clears` | Confirm clears reconfirmation | `requires_reconfirmation=false` |

### 7. Rollback Point Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| R-001 | `test_add_rollback_point` | Add rollback with description | Point added to array |
| R-002 | `test_add_rollback_with_sha` | Add rollback with git SHA | SHA included in point |
| R-003 | `test_get_rollback_points` | Retrieve all rollback points | Returns array of points |
| R-004 | `test_rollback_persists` | Rollbacks survive restart | Points still available |

### 8. Hook Event Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| H-001 | `test_session_start_inactive` | SessionStart when inactive | Silent (no message) |
| H-002 | `test_session_start_active` | SessionStart when active | Shows phase status |
| H-003 | `test_post_tool_non_task` | PostToolUse for non-Task | Silent |
| H-004 | `test_post_tool_non_forge_agent` | PostToolUse for non-forge agent | Silent |
| H-005 | `test_post_tool_forge_agent` | PostToolUse for forge agent | Records checkpoint |
| H-006 | `test_user_prompt_inactive` | UserPromptSubmit when inactive | Silent |
| H-007 | `test_user_prompt_wrong_phase` | UserPromptSubmit at phase 0 | Silent |
| H-008 | `test_user_prompt_confirmation` | UserPromptSubmit "yes" at phase 4 | Confirms execution |
| H-009 | `test_stop_inactive` | Stop when inactive | Silent |
| H-010 | `test_stop_auto_validate` | Stop at phase 4+ | Runs validation |

### 9. CLI Command Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| CLI-001 | `test_cli_get` | `forge-state.py get` | Returns state JSON |
| CLI-002 | `test_cli_get_phase` | `forge-state.py get-phase` | Returns phase number |
| CLI-003 | `test_cli_is_active_true` | `forge-state.py is-active` (active) | Exit code 0 |
| CLI-004 | `test_cli_is_active_false` | `forge-state.py is-active` (inactive) | Exit code 1 |
| CLI-005 | `test_cli_activate` | `forge-state.py activate` | Starts daemon, activates |
| CLI-006 | `test_cli_deactivate` | `forge-state.py deactivate` | Deactivates workflow |
| CLI-007 | `test_cli_confirm` | `forge-state.py confirm` | Sets confirmed |
| CLI-008 | `test_cli_checkpoint` | `forge-state.py checkpoint <agent>` | Records checkpoint |
| CLI-009 | `test_cli_set_phase` | `forge-state.py set-phase <n>` | Sets phase |
| CLI-010 | `test_cli_phases` | `forge-state.py phases` | Returns phase config |
| CLI-011 | `test_cli_set_design_hash` | `forge-state.py set-design-hash` | Stores hash |
| CLI-012 | `test_cli_add_rollback` | `forge-state.py add-rollback` | Adds rollback point |
| CLI-013 | `test_cli_get_rollbacks` | `forge-state.py get-rollbacks` | Returns rollback list |

### 10. Validation Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| VAL-001 | `test_validate_plugin_json` | Valid plugin.json | No errors |
| VAL-002 | `test_validate_missing_plugin_json` | Missing plugin.json | Error: missing |
| VAL-003 | `test_validate_invalid_json` | Malformed JSON | Error: invalid JSON |
| VAL-004 | `test_validate_missing_name` | Missing name field | Error: missing field |
| VAL-005 | `test_validate_component_paths` | All paths exist | No errors |
| VAL-006 | `test_validate_missing_path` | Non-existent path | Error: path not found |
| VAL-007 | `test_validate_hooks_json` | Valid hooks.json | No errors |
| VAL-008 | `test_validate_hook_events` | Valid event names | No warnings |
| VAL-009 | `test_validate_agent_frontmatter` | Valid agent frontmatter | No errors |
| VAL-010 | `test_validate_skill_frontmatter` | Valid skill frontmatter | No errors |
| VAL-011 | `test_validate_command_frontmatter` | Valid command frontmatter | No errors |
| VAL-012 | `test_validate_python_syntax` | All Python files valid | No errors |

### 11. Error Recovery Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| ERR-001 | `test_recover_corrupted_state` | Corrupted state file | Re-initializes state |
| ERR-002 | `test_recover_missing_state` | Missing state file | Creates new state |
| ERR-003 | `test_daemon_reconnect` | Daemon dies, reconnect | CLI starts new daemon |
| ERR-004 | `test_socket_timeout` | Daemon unresponsive | Returns timeout error |
| ERR-005 | `test_invalid_command` | Unknown daemon command | Returns error |
| ERR-006 | `test_invalid_phase_number` | set-phase with invalid number | Returns error |

### 12. Integration Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| INT-001 | `test_full_plugin_workflow` | Create plugin via all 6 phases | Valid plugin created |
| INT-002 | `test_refactor_workflow` | Refactor flow with checkpoints | Changes applied with rollback |
| INT-003 | `test_design_change_reconfirm` | Design change after confirm | Must reconfirm |
| INT-004 | `test_concurrent_sessions` | Multiple sessions (should fail) | Only one active per workspace |

---

## Test Execution Matrix

### By Priority

| Priority | Count | Test IDs |
|----------|-------|----------|
| **Critical** | 15 | P-001 to P-008, E-001 to E-004, C-001, C-002, INT-001 |
| **High** | 20 | S-001 to S-006, E-005 to E-011, V-001 to V-005 |
| **Medium** | 25 | D-001 to D-006, H-001 to H-010, CLI-001 to CLI-013 |
| **Low** | 15 | R-001 to R-004, VAL-001 to VAL-012, ERR-001 to ERR-006 |

### By Test Type

| Type | Count | Description |
|------|-------|-------------|
| Unit | 30 | Individual function tests |
| Integration | 25 | Component interaction tests |
| E2E | 20 | Full workflow tests |

---

## Docker Test Environment

### Container Setup

```dockerfile
# Already in tests/docker/Dockerfile
FROM python:3.11-slim
# + tmux, git, curl, jq
# + mock-claude CLI
# + test user isolation
```

### Volume Mounts

```yaml
# State persistence
- test-workspace:/workspace/test
- claude-state:/workspace/test/.claude
```

### Test Modes

| Mode | Command | Description |
|------|---------|-------------|
| Headless | `./scripts/run-docker-tests.sh` | CI/CD, no interaction |
| Interactive | `./scripts/run-docker-tests.sh interactive` | Debug with tmux |
| Validate | `./scripts/run-docker-tests.sh validate` | Quick plugin check |

---

## Implementation Checklist

### Phase 1: Core Tests (Existing)
- [x] Daemon connection test
- [x] Activation test
- [x] Phase progression tests
- [x] Confirmation gate tests
- [x] Wrong agent rejection
- [x] Workflow completion
- [x] CLI basic tests
- [x] State persistence

### Phase 2: Strict Enforcement Tests (To Implement)
- [ ] PreToolUse blocking tests (E-001 to E-011)
- [ ] Hook event simulation
- [ ] Block decision verification

### Phase 3: Versioning Tests (To Implement)
- [ ] Design hash tests (V-001 to V-005)
- [ ] Rollback point tests (R-001 to R-004)
- [ ] Reconfirmation flow

### Phase 4: Validation Tests (To Implement)
- [ ] Plugin structure validation (VAL-001 to VAL-012)
- [ ] Auto-validation on Stop

### Phase 5: Error Recovery Tests (To Implement)
- [ ] Corrupted state recovery (ERR-001 to ERR-006)
- [ ] Daemon crash recovery

### Phase 6: Integration Tests (To Implement)
- [ ] Full workflow tests (INT-001 to INT-004)

---

## Test Data Fixtures

### Valid Plugin Fixture
```json
{
  "name": "test-plugin",
  "version": "1.0.0",
  "description": "Test plugin for E2E tests"
}
```

### Valid Agent Fixture
```yaml
---
name: test-agent
description: "Test agent for E2E"
model: sonnet
tools: [Read, Glob]
---
# Test Agent
Content here.
```

### Valid Skill Fixture
```yaml
---
name: test-skill
description: "Test skill for E2E"
triggers: ["test", "example"]
---
# Test Skill
Content here.
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Test coverage | >90% of functions |
| All critical tests | 100% pass |
| All high priority tests | 100% pass |
| Medium/low priority | >95% pass |
| Execution time | <60 seconds headless |
