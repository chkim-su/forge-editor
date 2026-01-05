---
description: Validate plugin structure and run tests before deployment
argument-hint: [plugin-directory]
allowed-tools: ["Bash", "Read", "Glob", "Skill", "TodoWrite"]
---

# Validate Plugin

**MANDATORY** validation before plugin deployment. This command:
1. Validates plugin structure
2. Runs all tests (hook, plugin, agent)
3. Generates test report
4. Blocks deployment if tests fail

## Your Task

1. Parse arguments: `$ARGUMENTS`
   - Plugin directory (default: current directory)

2. Load the test framework skill:
   ```
   Skill("forge-editor:plugin-test-framework")
   ```

3. Check plugin structure exists:
   ```bash
   test -f "$PLUGIN_DIR/.claude-plugin/plugin.json" || \
   test -d "$PLUGIN_DIR/commands" || \
   test -d "$PLUGIN_DIR/skills" || \
   test -d "$PLUGIN_DIR/hooks"
   ```

4. Create test environment if needed:
   ```bash
   # If no tests exist, generate them
   if [ ! -f "$PLUGIN_DIR/tests/hook-tests.yaml" ]; then
       # Copy from template or generate
   fi
   ```

5. Run validation:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/plugin-test-framework/templates/test-runner.py "$PLUGIN_DIR"
   ```

6. Report results:
   - If ALL PASS: Show green status, allow deployment
   - If ANY FAIL: Show red status, **BLOCK deployment**

7. For failed tests, provide fix suggestions.

## Validation Checklist

### Required Structure
- [ ] `.claude-plugin/plugin.json` exists
- [ ] `plugin.json` has `name` and `description`
- [ ] All commands have frontmatter with `description`
- [ ] All skills have `SKILL.md`
- [ ] All agents have `description` and `allowed-tools`

### Hook Validation
- [ ] All hooks execute without error (exit 0 or 2)
- [ ] PreToolUse hooks return valid JSON
- [ ] PostToolUse hooks handle responses correctly
- [ ] Stop hooks check `stop_hook_active`

### Security Checks
- [ ] No hardcoded secrets
- [ ] No dangerous commands in hooks
- [ ] Proper input validation

## Output Format

```
═══════════════════════════════════════════
  Plugin Validation: my-plugin
═══════════════════════════════════════════

## Structure Validation
✅ plugin.json valid
✅ Commands have frontmatter
✅ Skills structured correctly
✅ Agents have descriptions

## Hook Tests
✅ Block dangerous rm
✅ Modify npm publish
✅ Auto-allow safe command
✅ Log tool usage

## Summary
Passed: 8 / 8
Status: READY FOR DEPLOYMENT ✅

═══════════════════════════════════════════
```

## Integration with /wizard publish

This validation is **automatically called** by `/forge-editor:wizard publish`.
Deployment is blocked if validation fails.
