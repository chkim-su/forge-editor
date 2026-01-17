---
name: validate
description: "Validate plugin schema, structure, and run auto-fixes"
---

# /validate - Schema Validation

You are running Forge schema validation. This validates a plugin's structure, schema compliance, and can auto-fix safe issues.

## Quick Validation

Run the schema validator to check the current plugin:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/schema-validator.py ${CLAUDE_WORKING_DIR}
```

## With Auto-Fix

To automatically fix safe issues (missing names, versions, etc.):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/schema-validator.py ${CLAUDE_WORKING_DIR} --fix
```

## JSON Output

For programmatic use:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/schema-validator.py ${CLAUDE_WORKING_DIR} --json
```

## What Gets Validated

### plugin.json
- Required fields: name, version, description
- Semver format for version
- Component paths exist

### Agent Frontmatter
- Required: name, description
- Valid model (sonnet, opus, haiku)
- Valid tools list

### Skill Frontmatter
- Required: name, description
- Triggers array present

### Command Frontmatter
- Required: name, description

### hooks.json
- Valid event names
- Hook type and command fields

### marketplace.json (if exists)
- Required: name, owner, plugins
- Plugin source paths exist

## Auto-Fix Capabilities

The validator can automatically fix these issues:

| Issue | Fix Strategy |
|-------|--------------|
| Missing plugin name | Infer from directory |
| Missing plugin version | Default to "1.0.0" |
| Invalid semver | Normalize to X.Y.Z |
| Missing agent name | Infer from filename |
| Invalid model | Default to "sonnet" |
| Invalid tools | Remove invalid, keep valid |
| Missing skill name | Infer from directory |
| Missing triggers | Add empty array |
| Missing command name | Infer from filename |

## Issues Requiring Manual Intervention

- Missing description (needs content decision)
- Invalid JSON/YAML syntax (needs manual fix)
- Missing referenced files (need creation)
- Duplicate names (need renaming decision)

## Usage Examples

### Validate Forge itself
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/schema-validator.py ${CLAUDE_PLUGIN_ROOT}
```

### Validate a specific plugin
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/schema-validator.py /path/to/plugin
```

### Validate and fix
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/schema-validator.py /path/to/plugin --fix
```

## After Running

1. Review any ERRORS - these must be fixed
2. Consider WARNINGS - recommended fixes
3. Check AUTO-FIXED items - verify they're correct
4. If issues remain, use the guidance provided

## Integration with Forge Workflow

This command can be run:
- Standalone at any time
- Automatically at end of Forge workflow (Phase 5)
- On session end when Forge is active (via Stop hook)
