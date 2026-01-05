---
description: "Create virtual test environment for hooks, plugins, or agents"
argument-hint: "[hook|plugin|agent|full] [output-dir]"
allowed-tools: ["Bash", "Write", "Read", "Skill"]
---

# Create Test Environment

Create a virtual test environment for validating Claude Code plugin components.

## Your Task

1. Parse arguments: `$ARGUMENTS`
   - Type: hook, plugin, agent, or full (default: full)
   - Output directory (optional, default: /tmp/plugin-test-{timestamp})

2. Load the skill for reference:
   ```
   Skill("forge-editor:plugin-test-framework")
   ```

3. Run the environment generator:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/skills/plugin-test-framework/templates/create-test-env.sh [type] [output-dir]
   ```

4. Show the created structure:
   ```
   Created: /tmp/plugin-test-xxxxx/
   ├── .claude/hooks/     (4 hook scripts)
   ├── .claude-plugin/    (plugin.json)
   ├── commands/          (1 command)
   ├── skills/            (1 skill)
   ├── agents/            (1 agent)
   └── run-tests.sh       (test runner)
   ```

5. Provide next steps:
   ```
   To run tests:
   cd /tmp/plugin-test-xxxxx && ./run-tests.sh

   Or use:
   /forge-editor:run-tests /tmp/plugin-test-xxxxx
   ```

## Examples

```bash
/forge-editor:test-env              # Full test environment
/forge-editor:test-env hook         # Hook tests only
/forge-editor:test-env plugin       # Plugin validation only
/forge-editor:test-env full ~/test  # Full tests in custom directory
```
