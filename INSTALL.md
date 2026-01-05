# Installation Guide

## Quick Install (Recommended)

### From GitHub (After Publishing)

```bash
# Add the marketplace
/plugin marketplace add chkim-su/forge-editor

# Install the plugin
/plugin install forge-editor@forge-editor-marketplace
```

---

## Manual Installation (Local Development)

### Option 1: Local Marketplace

```bash
# 1. Clone or copy this directory to your system
git clone https://github.com/chkim-su/forge-editor.git
# or
cp -r /path/to/forge-editor ~/.claude/plugins/forge-editor

# 2. Add as local marketplace
/plugin marketplace add ~/.claude/plugins/forge-editor

# 3. Install the plugin
/plugin install forge-editor@forge-editor-marketplace
```

### Option 2: Direct Copy

```bash
# Copy to Claude plugins directory
cp -r /path/to/forge-editor ~/.claude-plugins/forge-editor

# Restart Claude Code
```

---

## Verify Installation

After installation, verify the commands are available:

```bash
/help
```

You should see:
- `/forge-editor:wizard`
- `/forge-editor:validate-plugin`
- `/forge-editor:diagnose`

---

## Team Installation (Auto-setup)

For teams, add to `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "forge-editor": {
      "source": {
        "source": "github",
        "repo": "chkim-su/forge-editor"
      }
    }
  },
  "enabledPlugins": [
    "forge-editor@forge-editor-marketplace"
  ]
}
```

Team members will automatically get the plugin when they trust the repository.

---

## Troubleshooting

### Commands not showing

```bash
# Reload Claude Code
# or
/plugin uninstall forge-editor@forge-editor-marketplace
/plugin install forge-editor@forge-editor-marketplace
```

### Debug mode

```bash
claude --debug
```

Check for loading errors or warnings.

### Verify marketplace

```bash
/plugin marketplace list
```

Should show `forge-editor-marketplace`.

---

## Uninstallation

```bash
/plugin uninstall forge-editor@forge-editor-marketplace
/plugin marketplace remove forge-editor-marketplace
```

---

## Next Steps

After installation, read the [README.md](README.md) for usage examples.

Quick start:

```bash
# Start with wizard
/forge-editor:wizard

# Clarify vague idea
/forge-editor:wizard forge

# Create a skill
/forge-editor:wizard skill
```
