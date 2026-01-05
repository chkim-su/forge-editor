# Plugin Directory Structure Schema

## Required Structure

```
plugin-root/                      # [DIR] Plugin root directory
|
+-- .claude-plugin/               # [DIR] REQUIRED: Plugin manifest directory
|   +-- plugin.json               # [FILE] REQUIRED: Plugin metadata
|   +-- marketplace.json          # [FILE] OPTIONAL: If this is a marketplace
|
+-- commands/                     # [DIR] OPTIONAL: At ROOT level, NOT in .claude-plugin
|   +-- {command-name}.md         # [FILE] Command files MUST have .md extension
|
+-- agents/                       # [DIR] OPTIONAL: At ROOT level, NOT in .claude-plugin
|   +-- {agent-name}.md           # [FILE] Agent files MUST have .md extension
|
+-- skills/                       # [DIR] OPTIONAL: At ROOT level, NOT in .claude-plugin
|   +-- {skill-name}/             # [DIR] Skills are DIRECTORIES, not .md files
|       +-- SKILL.md              # [FILE] REQUIRED: Must be named exactly "SKILL.md"
|       +-- references/           # [DIR] OPTIONAL: Supporting documents
|       +-- scripts/              # [DIR] OPTIONAL: Helper scripts
|
+-- hooks/                        # [DIR] OPTIONAL: At ROOT level, NOT in .claude-plugin
|   +-- hooks.json                # [FILE] Hook configuration
|   +-- scripts/                  # [DIR] OPTIONAL: Hook scripts
|
+-- .mcp.json                     # [FILE] OPTIONAL: MCP server configuration
```

## Validation Rules

### Rule 1: Component Location (CRITICAL)

```
[X] WRONG: Components inside .claude-plugin/
    plugin-root/.claude-plugin/commands/
    plugin-root/.claude-plugin/agents/
    plugin-root/.claude-plugin/skills/

[PASS] CORRECT: Components at plugin ROOT
    plugin-root/commands/
    plugin-root/agents/
    plugin-root/skills/
```

### Rule 2: Skill Format (CRITICAL)

```
[X] WRONG: Skills as .md files
    skills/my-skill.md

[PASS] CORRECT: Skills as directories with SKILL.md
    skills/my-skill/
        SKILL.md
```

### Rule 3: Command/Agent Format

```
[X] WRONG: Commands without .md extension
    commands/migrate

[PASS] CORRECT: Commands with .md extension
    commands/migrate.md
```

### Rule 4: Path Format in marketplace.json

```json
// [X] WRONG: Skills with .md extension
"skills": ["./skills/my-skill.md"]

// [PASS] CORRECT: Skills as directory path
"skills": ["./skills/my-skill"]

// [X] WRONG: Commands without .md
"commands": ["./commands/migrate"]

// [PASS] CORRECT: Commands with .md
"commands": ["./commands/migrate.md"]
```

### Rule 5: Source Format

```json
// [X] WRONG: source as string "github"
"source": "github",
"repo": "owner/repo"

// [PASS] CORRECT: source as object
"source": {"source": "github", "repo": "owner/repo"}

// [X] WRONG: using "type" instead of "source"
"source": {"type": "github", "repo": "owner/repo"}

// [PASS] CORRECT: using "source" key
"source": {"source": "github", "repo": "owner/repo"}
```

## File Validation Rules

### plugin.json Schema

```json
{
  "name": "string (required, kebab-case)",
  "version": "string (semver)",
  "description": "string",
  "author": {
    "name": "string (required)",
    "email": "string"
  },
  "repository": "string URL (NOT object)",
  "homepage": "string URL",
  "license": "string",
  "keywords": ["array", "of", "strings"]
}
```

**Forbidden fields in plugin.json:**
- `components` - Use skills/agents/commands arrays in marketplace.json
- `repo` - Use repository field with string URL
- `type` - Not a valid field

### marketplace.json Schema

```json
{
  "name": "string (required, kebab-case)",
  "owner": {
    "name": "string (required)"
  },
  "plugins": [
    {
      "name": "string (required, kebab-case)",
      "source": "'./' | {source: 'github', repo: 'owner/repo'}",
      "description": "string",
      "commands": ["./commands/*.md"],
      "agents": ["./agents/*.md"],
      "skills": ["./skills/*"],
      "hooks": ["./hooks/*.json"]
    }
  ]
}
```

## Frontmatter Requirements

### Command Frontmatter (commands/*.md)

```yaml
---
description: "Required: What this command does"
argument-hint: "Optional: Usage hint"
allowed-tools: ["Read", "Write", "Bash"]  # Optional
---
```

### Agent Frontmatter (agents/*.md)

```yaml
---
name: agent-name                          # Required
description: "What this agent does"       # Required
tools: ["Read", "Write", "Bash"]          # REQUIRED - will fail without this
model: sonnet                             # Optional: sonnet, opus, haiku
---
```

### Skill Frontmatter (skills/*/SKILL.md)

```yaml
---
name: skill-name                          # Required
description: "When to use this skill"     # Required
allowed-tools: ["Read", "Grep", "Glob"]   # Optional
---
```

## Error Messages Reference

| Error Code | Message | Fix |
|------------|---------|-----|
| E001 | Components inside .claude-plugin | Move to plugin root |
| E002 | Skill has .md extension | Remove .md, create directory |
| E003 | Command missing .md | Add .md extension |
| E004 | Agent missing .md | Add .md extension |
| E005 | source is string "github" | Convert to object format |
| E006 | source uses "type" key | Change "type" to "source" |
| E007 | repo at plugin level | Move into source object |
| E008 | repository is object | Convert to string URL |
| E009 | Missing SKILL.md | Create SKILL.md in skill directory |
| E010 | Agent missing tools field | Add tools array to frontmatter |
