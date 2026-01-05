---
description: Run comprehensive plugin validation with optional auto-fix
argument-hint: "[--fix] [--json] [--dry-run] [plugin-path]"
allowed-tools: ["Read", "Bash", "Grep", "Glob"]
---

# Validate Full

Run comprehensive validation on the current plugin or a specified plugin path. This command gives you explicit control over when to run full validation, as opposed to the automatic partial checks that run via hooks.

## Validation Checks (106 total)

- **Structure**: Directory layout, required files, naming conventions
- **Frontmatter**: YAML syntax, required fields, field validation
- **Registration**: marketplace.json integrity, file existence
- **Content**: Language consistency (W037), emoji usage (W038)
- **Architecture**: Form selection (W040), test coverage (W045)

## Your Task

1. **Parse arguments** from `$ARGUMENTS`:
   - `--fix`: Enable auto-fix mode (fixes frontmatter, registration issues)
   - `--json`: Output results as JSON
   - `--dry-run`: Preview fixes without applying (use with --fix)
   - `[plugin-path]`: Optional path to validate (defaults to forge-editor plugin)

2. **Run validation**:
   ```bash
   # Default (current plugin)
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py

   # With flags
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --fix --dry-run

   # Specific path
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py /path/to/plugin
   ```

3. **Interpret exit codes**:
   - `0`: All checks passed
   - `1`: Errors found (blocks deployment)
   - `2`: Warnings found (deployment may have issues)

4. **Display results**:
   - Show summary: errors, warnings, passed checks
   - For each warning, show the skill reference that can help resolve it
   - If `--fix` was used, show what was fixed

5. **Suggest next steps** based on results:
   - If errors: List specific fixes needed
   - If warnings: Reference appropriate skills
   - If passed: Ready for commit/deployment

## Examples

```bash
# Basic validation
/forge-editor:validate-full

# Preview auto-fixes
/forge-editor:validate-full --fix --dry-run

# Apply auto-fixes
/forge-editor:validate-full --fix

# JSON output for scripting
/forge-editor:validate-full --json

# Validate specific plugin
/forge-editor:validate-full ~/.claude/plugins/cache/my-plugin/my-plugin/1.0.0
```

## Warning Code Reference

When warnings appear, use these skill references:

| Code | Issue | Solution Skill |
|------|-------|----------------|
| W028-W034 | Structure issues | `skill-design` |
| W035 | References issues | `skill-design` |
| W036 | Unnecessary files | `plugin-architecture` |
| W037 | Language mixing | `critical-analysis-patterns` |
| W038 | Emoji usage | `critical-analysis-patterns` |
| W040 | Form selection | `orchestration-patterns` |
| W045 | Test coverage | `plugin-test-framework` |

## Difference from /validate-plugin

| Command | Purpose | Script |
|---------|---------|--------|
| `/validate-full` | Comprehensive static validation | `validate_all.py` |
| `/validate-plugin` | E2E tests and structure tests | `test-runner.py` |

Use `/validate-full` for quick static checks. Use `/validate-plugin` for full test suite execution.
