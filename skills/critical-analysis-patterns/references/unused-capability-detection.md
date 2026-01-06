# Unused Capability Detection

"있는데 왜 안 쓰지?"를 감지하는 패턴들입니다.

## Type 1: 선언된 미사용 스킬

### 감지 방법
```bash
# 1. frontmatter에서 skills 선언 추출
grep -r "^skills:" agents/ commands/

# 2. 본문에서 Skill() 사용 추출
grep -r "Skill(" agents/ commands/

# 3. 차집합 = 미사용 스킬
```

### 질문
- "선언만 하고 왜 안 쓰는가?"
- "미래 사용을 위한 것이라면 왜 주석이 없는가?"
- "정말 필요한 스킬인가?"

### 해결 방안
| 상황 | 조치 |
|-----|-----|
| 실수로 남음 | 제거 |
| 미래 사용 예정 | TODO 주석 추가 |
| 암묵적 의존 | 명시적 사용 추가 |

---

## Type 2: 미사용 에이전트

### 감지 방법
```bash
# 1. agents/ 목록
ls agents/*.md

# 2. Task 호출에서 참조되는 에이전트
grep -r "agent:" commands/ skills/
grep -r "subagent_type" commands/ skills/

# 3. 차집합 = 미사용 에이전트
```

### 질문
- "이 에이전트를 호출하는 곳이 있는가?"
- "독립 실행용이라면 어떻게 실행하는가?"
- "다른 에이전트에 통합되어야 하는 것은 아닌가?"

---

## Type 3: 미사용 Hook

### 감지 방법
```json
// hooks.json에 20개 Hook이 있지만
// 실제로 트리거되는 상황이 없는 Hook 존재
```

### 질문
- "이 Hook이 트리거되는 상황이 실제로 발생하는가?"
- "테스트해본 적 있는가?"
- "오버엔지니어링은 아닌가?"

---

## Type 4: 선언된 미사용 도구

### 증상
```yaml
# agent frontmatter
tools: ["Read", "Write", "Bash", "Grep", "Glob", "Task", "WebFetch"]

# 실제 본문
Read와 Task만 사용됨
```

### 질문
- "7개 도구를 선언했는데 2개만 쓰는 이유는?"
- "최소 권한 원칙을 위반하고 있지 않은가?"

### 해결 방안
- 실제 사용하는 도구만 선언
- 또는 선언한 도구를 활용하는 로직 추가

---

## Type 5: 미사용 references/

### 증상
```
skills/my-skill/
├── SKILL.md
└── references/
    ├── used.md      # SKILL.md에서 Read() 참조됨
    └── orphan.md    # 아무도 참조 안 함
```

### 감지 방법
```bash
# references/ 파일 목록
ls skills/*/references/

# SKILL.md에서 Read() 참조 추출
grep -r "Read(" skills/*/SKILL.md
```

### 질문
- "이 참조 문서는 누가 읽는가?"
- "더 이상 필요 없는 것은 아닌가?"

---

## Type 6: Design-Implementation Gap (설계-구현 불일치)

The most insidious type: documented patterns that aren't actually applied.

### Symptoms
```
skills/workflow-enforcement/references/gate-design.md:
  "Use require-gate for enforcement"

scripts/forge-state.py:
  def cmd_require_gate(name): ...  # CLI exists!

hooks/hooks.json:
  # ... but require-gate is never called!
```

### Detection Method

**Static Analysis (grep-based):**
```bash
# 1. Extract patterns from design docs
grep -rh "require-gate\|pass-gate\|check-gate" skills/*/references/*.md

# 2. Check actual usage in hooks
grep "require-gate\|pass-gate\|check-gate" hooks/hooks.json

# 3. Gap = designed but not applied
```

**Deep Analysis (Serena MCP):**
```python
# Use serena-query for symbol-level analysis
serena-query find_symbol "cmd_require_gate" --path scripts/
serena-query find_referencing_symbols "cmd_require_gate" --path .

# If referencing_symbols returns empty → unused CLI function
```

### Detection Script

```bash
python3 scripts/design-implementation-gap.py
```

### Questions
- "This pattern is documented but where is it actually used?"
- "Is this a planned feature or forgotten implementation?"
- "Why document a capability that isn't wired up?"

### Resolution

| Situation | Action |
|-----------|--------|
| Forgotten implementation | Wire it up to hooks.json |
| Planned future feature | Add "PLANNED:" prefix in docs |
| Obsolete design | Remove from documentation |
| Intentionally unused | Document why in design doc |

### Gap Categories

| Category | Example | Severity |
|----------|---------|----------|
| CLI-to-Hook gap | `require-gate` exists but not in hooks | High |
| Doc-to-Code gap | Pattern described but no implementation | Medium |
| Config-to-Runtime gap | Setting exists but never read | Medium |
| Test-to-Feature gap | Test for feature that doesn't exist | Low |

---

## Summary Table

| Type | Detection Method | Action |
|------|------------------|--------|
| Unused skill declaration | frontmatter vs Skill() comparison | Remove or use |
| Unused agent | agents/ vs Task call comparison | Remove or merge |
| Unused Hook | hooks.json analysis | Remove or test |
| Unused tool declaration | tools vs body comparison | Minimize |
| Unused references | Read() reference tracking | Remove or connect |
| Design-Implementation gap | Design docs vs actual wiring | Wire up or document why |
