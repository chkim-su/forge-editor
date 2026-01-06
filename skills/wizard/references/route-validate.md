# VALIDATE Route

**MANDATORY: Use /validate-full command. NO exceptions.**

## State Machine Integration

Before running validation, initialize state if wizard workflow is active:

```bash
# Start validation phase (if workflow active)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py start-phase validation
```

For detailed state machine patterns, see: `Skill("forge-editor:workflow-enforcement")`

## Execution

```
Skill("forge-editor:validate-full")
```

With arguments:
```
Skill("forge-editor:validate-full", args="--fix")
```

## Validation Checks

| Layer | Check | Description |
|-------|-------|-------------|
| Schema | Required fields | name, owner, plugins |
| Schema | Source format | `{"source": "github"}` NOT `{"type": "github"}` |
| Path | E016 | Path mismatch |
| Path | E017 | marketplace.json location |
| Source | E018 | Git remote ≠ source |
| Remote | E019 | Repo not accessible |
| Remote | E020 | Missing files |
| Hookify | W028 | MUST/CRITICAL without hooks |
| Skill | W029 | Missing frontmatter |
| Skill | W031 | Content > 500 words |
| Skill | W032 | No references/ directory |
| Agent | W030 | Missing frontmatter |
| Agent | W033 | Declared skills, no Skill() usage |
| Workflow | W034 | Multi-stage without per-stage loading |

## Critical Errors (E016-E020)

### E016: Path Resolution Mismatch

**증상**: 플러그인 로드 안됨

**해결**:
- marketplace.json을 `.claude-plugin/`으로 이동
- 또는 source를 `"./"` 로 변경
- 또는 GitHub에 파일 푸시

### E017-E020: Remote Issues

```bash
# 자동 수정
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --fix

# GitHub CLI로 확인
gh repo view owner/repo
```

## Warnings (W028-W034)

### W028: Hookify Required

MUST/CRITICAL 키워드 있지만 hooks 없음 → hookify 필요

### W029-W032: Skill Design

- Frontmatter 누락 → YAML frontmatter 추가
- 500+ words → references/ 분리
- No references/ → 디렉토리 생성

### W033-W034: Skill Usage

- skills 선언했지만 Skill() 없음 → frontmatter 자동로딩이면 무시 가능
- Multi-stage without per-stage loading → 단계별 Skill() 추가

## Result Handling

1. **status="block"**:
   - Blocking errors/warnings found
   - Mark gate failed: `forge-state.py fail-gate validation_passed`
   - Show errors → Ask auto-fix → `--fix` → Re-validate
   - Loop until pass

2. **status="warn"**:
   - Advisory warnings only (not blocking)
   - Mark gate passed: `forge-state.py pass-gate validation_passed`
   - Show warnings → Allow proceed

3. **status="pass"**:
   - No issues found
   - Mark gate passed: `forge-state.py pass-gate validation_passed`
   - Complete phase: `forge-state.py complete-phase validation`
   - "[PASS] 검증 통과 - 배포 준비 완료"

## Auto-Fix

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --fix
```

자동 수정 항목:
- source 형식 변환
- 누락된 .md 확장자 추가
- 잘못된 .md 확장자 제거 (skills)
- 금지된 필드 제거

## Forbidden Behaviors

- ❌ Reading files manually
- ❌ "based on previous analysis"
- ❌ Skipping script execution
- ✅ ALWAYS run the script
