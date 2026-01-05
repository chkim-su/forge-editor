---
description: Run tests on a virtual test environment
argument-hint: <test-directory>
allowed-tools: ["Bash", "Read", "Skill"]
---

# Run Plugin Tests

Execute tests on a virtual test environment created by `/forge-editor:test-env`.

## Your Task

1. Parse arguments: `$ARGUMENTS`
   - Test directory path (required)

2. Verify the directory exists:
   ```bash
   test -d "$TEST_DIR" || echo "Directory not found"
   test -f "$TEST_DIR/run-tests.sh" || echo "Not a test environment"
   ```

3. Run the tests:
   ```bash
   cd "$TEST_DIR" && ./run-tests.sh
   ```

4. Display results:
   - Show test output
   - Read and display TEST-RESULTS.md
   - Summarize pass/fail counts

5. If tests fail, analyze and suggest fixes.

## Examples

```bash
/forge-editor:run-tests /tmp/plugin-test-123456
/forge-editor:run-tests ~/my-plugin-tests
```

## Expected Output

```
================================
  Plugin Component Tests
================================

--- Hook Tests ---
✅ PASS: Block dangerous rm
✅ PASS: Modify npm publish
✅ PASS: Auto-allow safe command
✅ PASS: Log success
✅ PASS: Detect failure
✅ PASS: Context injection

--- Plugin Validation ---
✅ PASS: plugin.json valid
✅ PASS: Commands have frontmatter
✅ PASS: Skills structured correctly

--- Agent Validation ---
✅ PASS: Agents have descriptions
✅ PASS: Agents have tool lists

================================
  Summary: 11 / 11 passed
================================
```
