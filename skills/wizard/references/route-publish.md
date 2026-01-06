# PUBLISH / LOCAL_REGISTER Routes

## State Machine Integration

PUBLISH requires all previous gates to be passed:

```bash
# Check required gates
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py require-gate validation_passed
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py require-gate analysis_complete
```

If gates not passed → **BLOCKED**. Complete VALIDATE and ANALYZE first.

After successful deployment:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py start-phase deployment
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py complete-phase deployment
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py reset  # Workflow complete
```

---

## LOCAL_REGISTER Route

Register current project as local plugin for testing.

### Steps

1. Get current path: `pwd`

2. Check `.claude-plugin/marketplace.json` exists
   - If not: "Not a plugin project. Create marketplace.json first?"

3. Run registration:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/register_local.py --path $(pwd)
```

4. Show result:
```markdown
## 로컬 등록 완료

**다음 단계:**
1. Claude Code 재시작
2. 기능 테스트
3. 테스트 완료 후: `/wizard publish`
```

---

## PUBLISH Route

Deploy to marketplace after testing.

### Deployment Models

| Model | Source | Description |
|-------|--------|-------------|
| **Single Repo** | `"./"` | 마켓플레이스 = 플러그인 |
| **Multi Repo** | `{"source": "github", ...}` | 별도 리포지토리 |

### Step 1: Determine Type

```yaml
AskUserQuestion:
  question: "배포 방식?"
  header: "배포"
  options:
    - label: "Single Repo (Recommended)"
    - label: "Multi Repo (Advanced)"
```

### Step 2: Validation

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py
```

**If E016 (GitHub source with local files)**:
```markdown
⚠️ GitHub source 사용하지만 파일 미푸시

해결:
1. Single Repo: source를 "./"로 변경
2. 파일 푸시 후 재시도
```

### Step 3: Configure Source

#### Single Repo:
```json
"source": "./"
```

```bash
gh repo view $(git remote get-url origin) || gh repo create
git add -A && git commit -m "Prepare deployment" && git push
```

#### Multi Repo:
```bash
gh api repos/{owner}/{plugin-repo}/contents --jq '.[].name'
```

```json
"source": {"source": "github", "repo": "{owner}/{plugin-repo}"}
```

### Step 4: Content Quality Check (BLOCKING)

In publish mode, content quality warnings become BLOCKING:
- **W037**: Non-English content (Korean text) - BLOCKS
- **W038**: Emoji usage - BLOCKS

```bash
# Run with --publish-mode to enforce content quality
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --publish-mode
```

For content guidelines, see: `Skill("forge-editor:comprehensive-validation")`

### Step 5: Final Validation

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --publish-mode
```

**MUST pass with status="pass"**

### Step 6: Test Installation

```bash
# 다른 터미널에서
claude marketplace add {owner}/{repo}
claude /plugin  # 플러그인 표시 확인
```

### Step 7: Success

```markdown
## 배포 완료!

**설치 방법:**
```bash
claude marketplace add {owner}/{repo}
```

**활성화:**
```bash
claude /plugin
# → {plugin-name}@{marketplace-name} 선택
```
```
