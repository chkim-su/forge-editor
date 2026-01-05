# SKILL / SKILL_FROM_CODE Routes

## SKILL Route

Create a new skill from scratch.

### Step 1: Load skill-design

```
Skill("forge-editor:skill-design")
```

### Step 2: Ask type

```yaml
AskUserQuestion:
  question: "Skill type?"
  header: "Type"
  options:
    - label: "Knowledge"
      description: "Guidelines, high freedom"
    - label: "Hybrid"
      description: "Guidance + scripts"
    - label: "Tool"
      description: "Script-driven, low freedom"
    - label: "Unsure"
```

If "Unsure": ask freedom level (High→Knowledge, Medium→Hybrid, Low→Tool)

### Step 3: Launch Agent

```
Task: skill-architect
Pass: description, skill_type
```

### Step 4: Validation (MANDATORY)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json
```

**CRITICAL: MUST pass before proceeding. DO NOT skip.**

- **status="fail"**: Show errors → Ask "자동 수정?" → If yes: `--fix` → Re-validate → LOOP until pass
- **status="warn"**: Show warnings, allow proceed
- **status="pass"**: Continue

### Step 5: Next Steps

```markdown
1. **로컬 등록**: `/wizard register`
2. **테스트**: Claude Code 재시작 → 기능 테스트
3. **배포**: `/wizard publish`
```

---

## SKILL_FROM_CODE Route

Convert existing code into a reusable skill.

### Step 1: Identify Target

```yaml
AskUserQuestion:
  question: "Target type?"
  header: "Target"
  options:
    - label: "File"
    - label: "Directory"
    - label: "Pattern"
```

Then ask for path.

### Step 2: Load skill-design

```
Skill("forge-editor:skill-design")
```

### Step 3: Launch Agent

```
Task: skill-converter
Pass: target_path, description
```

### Step 4-5: Same as SKILL Route

Validation → Next Steps
