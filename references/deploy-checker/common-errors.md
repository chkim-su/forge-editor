# Common Deployment Errors and Fixes

## Registration Errors

### Error: File NOT FOUND
```
❌ ./commands/foo -> commands/foo.md NOT FOUND
```
**Cause:** marketplace.json references a file that doesn't exist
**Fix:** Create the file or remove from marketplace.json commands array

### Error: NOT REGISTERED
```
❌ commands/bar.md exists but NOT REGISTERED
```
**Cause:** File exists but not in marketplace.json
**Fix:** Add `"./commands/bar"` to marketplace.json commands array

### Error: Source path format
```
❌ source "my-plugin" must start with "./"
```
**Cause:** Local plugin path missing `./` prefix
**Fix:** Change `"source": "my-plugin"` to `"source": "./my-plugin"`

## Content Quality Errors

### Error: TODO in description
```
❌ commands/foo.md: description contains TODO
```
**Fix:** Replace TODO with actual description explaining what the command does

### Error: Description too short
```
❌ skills/bar/SKILL.md: description too short (15 chars)
```
**Fix:** Expand description to clearly explain:
- What the skill does
- When to use it (trigger phrases)
- Key capabilities

## Expert Skill Errors

### Error: Missing troubleshooting.md
```
❌ skills/pptx-builder: missing references/troubleshooting.md
```
**Fix:** Create `skills/pptx-builder/references/troubleshooting.md` with:
- Known issues
- Workarounds
- Common pitfalls

### Error: Missing validation scripts
```
❌ skills/pdf-processor: missing scripts/validation/
```
**Fix:** Create validation scripts to verify output correctness

## Cross-Reference Errors

### Error: Broken link
```
❌ skills/foo/SKILL.md: broken reference to references/missing.md
```
**Fix:** Either:
- Create the referenced file
- Remove or update the link

### Error: Invalid skill reference
```
❌ agents/bar.md: skills "nonexistent" not found
```
**Fix:** Either:
- Create the skill directory with SKILL.md
- Update the agent to reference an existing skill

## Structure Errors

### Error: Missing SKILL.md
```
❌ skills/my-skill/: directory exists but no SKILL.md
```
**Fix:** Create `skills/my-skill/SKILL.md` with proper frontmatter

### Error: Empty directory
```
⚠️ skills/my-skill/scripts/: empty directory
```
**Fix:** Either add files or remove the empty directory
