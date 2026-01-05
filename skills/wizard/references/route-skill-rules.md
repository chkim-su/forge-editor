# SKILL_RULES Route

Configure automatic skill activation via skill-rules.json.

## Step 1: Check Existing Skills

```bash
ls -la .claude/skills/*/SKILL.md 2>/dev/null || echo "No skills found"
```

If no skills: "Create skills first?" → Yes: goto SKILL route

## Step 2: Load skill-activation-patterns

```
Skill("forge-editor:skill-activation-patterns")
```

## Step 3: Ask Configuration Type

```yaml
AskUserQuestion:
  question: "What do you want to configure?"
  header: "Config"
  options:
    - label: "New skill-rules.json"
      description: "Create from scratch"
    - label: "Add skill triggers"
      description: "Add triggers to existing rules"
    - label: "Review current rules"
      description: "Analyze and optimize"
```

## Step 4: Launch Agent

```
Task: skill-rules-designer
Pass: existing_skills, configuration_type
```

The agent will:
1. Analyze existing skills in `.claude/skills/`
2. Generate appropriate trigger patterns (keywords, intentPatterns)
3. Set priority and enforcement levels
4. Create/update `.claude/skills/skill-rules.json`

## Step 5: Validation (MANDATORY)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json
```

Same handling as SKILL route.

## Step 6: Test Activation

After creating skill-rules.json, test with:

```
# Type a prompt that should trigger the skill
# Check if skill-activation-hook.py suggests it
```

## Step 7: Next Steps

```markdown
1. **Test triggers**: Type prompts matching keywords
2. **Adjust priorities**: critical > high > medium > low
3. **Add more skills**: Repeat for each skill needing auto-activation
```

---

## skill-rules.json Structure

```json
{
  "version": "1.0",
  "skills": {
    "skill-name": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "promptTriggers": {
        "keywords": ["keyword1", "keyword2"],
        "intentPatterns": ["regex.*pattern"]
      }
    }
  },
  "complexity_levels": {
    "simple": { "keywords": ["simple"], "auto_skills": ["skill-a"] },
    "standard": { "keywords": ["standard"], "auto_skills": ["skill-a", "skill-b"] },
    "advanced": { "keywords": ["advanced"], "auto_skills": ["skill-a", "skill-b", "skill-c"] }
  }
}
```

## References

- [Skill Activation Patterns](../../skill-activation-patterns/SKILL.md)
- [Skill Catalog](../../skill-catalog/SKILL.md)
