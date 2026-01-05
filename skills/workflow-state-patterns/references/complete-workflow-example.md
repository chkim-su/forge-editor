# Complete Workflow Example: Refactoring Pipeline

## Overview

This example shows a complete 4-phase refactoring workflow with:
- State file management
- Hook-based quality gates
- MCP Gateway integration
- Failure recovery

---

## Workflow Phases

```
┌─────────────────────────────────────────────────────────┐
│               REFACTORING WORKFLOW                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [1] ANALYZE ──→ solid-analyzer agent                   │
│      └─ Creates: .refactor-analysis-done                 │
│                                                          │
│  [2] PLAN ─────→ refactor-planner agent                 │
│      └─ Creates: .refactor-plan-approved                 │
│                                                          │
│  [USER GATE] ──→ User reviews and approves plan         │
│                                                          │
│  [3] EXECUTE ──→ refactor-executor agent                │
│      └─ Pre-check: .analysis-done + .plan-approved      │
│      └─ Creates: .refactor-execution-done               │
│                                                          │
│  [4] VERIFY ───→ refactor-auditor agent                 │
│      └─ PASS: cleanup all, create .audit-passed         │
│      └─ FAIL: preserve .execution-done for retry        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Hooks Configuration

`hooks/hooks.json` (Claude Code 1.0.40+ Schema):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/refactor-gate.py pre",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/refactor-gate.py post",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/refactor-gate.py stop",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Gate Script** (`scripts/refactor-gate.py`):

```python
#!/usr/bin/env python3
"""Workflow gate script for refactoring pipeline."""
import sys, json, os

def pre_hook(data):
    """PreToolUse: Check gates before execution."""
    subagent = data.get('tool_input', {}).get('subagent_type', '')

    if 'refactor-executor' in subagent:
        if not (os.path.exists('.refactor-analysis-done') and
                os.path.exists('.refactor-plan-approved')):
            print("❌ Workflow violation: Cannot execute without completed analysis and approved plan.")
            print("Required: .refactor-analysis-done, .refactor-plan-approved")
            sys.exit(1)  # Block

    elif 'refactor-planner' in subagent:
        if not os.path.exists('.refactor-analysis-done'):
            print("⚠️ Warning: Planning without analysis may miss issues")

    sys.exit(0)

def post_hook(data):
    """PostToolUse: Update state files after execution."""
    subagent = data.get('tool_input', {}).get('subagent_type', '')
    response = str(data.get('tool_response', ''))

    if 'solid-analyzer' in subagent:
        open('.refactor-analysis-done', 'w').close()
        print("✓ Analysis complete. State: .refactor-analysis-done created")

    elif 'refactor-planner' in subagent:
        open('.refactor-plan-approved', 'w').close()
        print("✓ Plan created. State: .refactor-plan-approved created")

    elif 'refactor-executor' in subagent:
        open('.refactor-execution-done', 'w').close()
        print("✓ Execution complete. State: .refactor-execution-done created")

    elif 'refactor-auditor' in subagent:
        if 'PASS' in response:
            open('.refactor-audit-passed', 'w').close()
            for f in ['.refactor-analysis-done', '.refactor-plan-approved', '.refactor-execution-done']:
                if os.path.exists(f): os.remove(f)
            print("✓ Audit passed. Workflow complete. All state files cleaned.")
        elif 'FAIL' in response:
            print("⚠️ Audit failed. Fix issues and re-run executor. State preserved for retry.")

def stop_hook():
    """Stop: Report workflow status."""
    if os.path.exists('.refactor-execution-done') and not os.path.exists('.refactor-audit-passed'):
        print("\\n📋 Workflow Status: Execution done, audit pending.")
        print("Next session: Run auditor to verify changes.")

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'pre'
    data = json.load(sys.stdin) if mode != 'stop' else {}

    if mode == 'pre': pre_hook(data)
    elif mode == 'post': post_hook(data)
    elif mode == 'stop': stop_hook()
```

**Note:** Subagent-specific logic is handled in the script by parsing `tool_input.subagent_type`.

---

## Agent Definitions

### 1. Solid Analyzer Agent

```yaml
---
name: solid-analyzer
description: Analyzes codebase for SOLID violations
tools: [Task, Read, Glob, Grep]
skills: solid-design-rules
model: sonnet
---
```

Calls gateway:
```json
{
  "intent": "ANALYZE",
  "action": "find_refs",
  "effect": "READ_ONLY",
  "artifact": "JSON",
  "params": { "target": "src/" }
}
```

### 2. Refactor Planner Agent

```yaml
---
name: refactor-planner
description: Creates step-by-step refactoring plans
tools: [Task, Read, Glob, Grep]
skills: solid-design-rules, refactoring-patterns
model: sonnet
---
```

### 3. Refactor Executor Agent

```yaml
---
name: refactor-executor
description: Executes refactoring operations via gateway
tools: [Task, Read, Glob, Grep, Bash]
skills: refactoring-patterns
model: sonnet
---
```

Calls gateway with MODIFY:
```json
{
  "intent": "MODIFY",
  "action": "rename_symbol",
  "effect": "MUTATING",
  "artifact": "PATCH",
  "params": { "old_name": "foo", "new_name": "bar" }
}
```

### 4. Refactor Auditor Agent

```yaml
---
name: refactor-auditor
description: Verifies refactoring quality
tools: [Task, Read, Glob, Grep, Bash]
skills: solid-design-rules
model: sonnet
---
```

---

## Command Entry Points

### Full Workflow Command

`commands/refactor.md`:
```markdown
---
name: refactor
description: Full refactoring workflow (analyze → plan → execute → verify)
---

# Refactoring Workflow

Execute complete refactoring pipeline:

1. Run solid-analyzer on target
2. Run refactor-planner to create plan
3. Present plan for user approval
4. Run refactor-executor (blocked until plan approved)
5. Run refactor-auditor to verify
6. Report results
```

### Individual Phase Commands

`commands/analyze.md`, `commands/plan.md`, etc.

---

## State File Lifecycle

```
Session 1:
  /analyze → .refactor-analysis-done created
  /plan → .refactor-plan-approved created
  (session ends)

Session 2:
  (state files persist)
  /execute → PRE HOOK checks files → PASS → executes
  .refactor-execution-done created
  /audit → runs verification
  PASS → all state files deleted
  FAIL → .refactor-execution-done preserved

Session 3 (if audit failed):
  (fix issues)
  /execute → runs again (state still valid)
  /audit → PASS → cleanup
```

---

## Debugging State

Check current workflow state:
```bash
ls -la .refactor-*
```

Reset workflow:
```bash
rm -f .refactor-*
```

Skip to specific phase (dangerous):
```bash
touch .refactor-analysis-done .refactor-plan-approved
```

---

## Integration Points

### With MCP Gateway

All MODIFY operations go through gateway with workflow state checks.

### With Git

Recommend:
1. Stash before workflow: `git stash`
2. After audit pass: `git commit`
3. On failure: `git checkout .` to reset

Add to `.gitignore`:
```
.refactor-*
```
