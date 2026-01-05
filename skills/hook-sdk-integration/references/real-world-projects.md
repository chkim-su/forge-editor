# 실제 프로젝트 사례

## GitHub 프로젝트

### 1. claude-code-hooks-mastery
**URL**: https://github.com/disler/claude-code-hooks-mastery

**특징**:
- 8가지 Hook lifecycle 이벤트 데모
- UV 단일 파일 스크립트
- JSON payload 캡처

**구조**:
```
.claude/hooks/
├── capture_user_prompt.py
├── capture_pre_tool_use.py
├── capture_post_tool_use.py
└── capture_stop.py
```

### 2. claude-hooks (TypeScript)
**URL**: https://github.com/johnlindquist/claude-hooks

**특징**:
- TypeScript 타입 안전
- 모든 Hook 타입에 대한 typed payload
- 세션 로그 저장

### 3. claude-code-infrastructure-showcase
**URL**: https://github.com/diet103/claude-code-infrastructure-showcase

**특징**:
- 6개월 실사용 인프라
- skill-activation-prompt Hook
- 10개 전문 agent
- 3개 slash command

**구조**:
```
.claude/
├── hooks/
│   ├── skill-activation-prompt.sh
│   ├── post-tool-use-tracker.sh
│   └── tsc-check.sh
├── agents/
└── commands/
```

### 4. claude-hooks (Python)
**URL**: https://github.com/decider/claude-hooks

**특징**:
- Python 기반 validation
- 품질 검사 자동화
- 알림 통합

## 활용 패턴

### 패턴 1: Skill Auto-Activation

```bash
# skill-activation-prompt.sh
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt' | tr '[:upper:]' '[:lower:]')

if echo "$PROMPT" | grep -qE "커밋|commit"; then
    echo "💡 추천: /commit"
fi
```

### 패턴 2: TypeScript 검사

```bash
# tsc-check.sh (PostToolUse:Edit)
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE" == *.ts ]] || [[ "$FILE" == *.tsx ]]; then
    npx tsc --noEmit "$FILE" 2>&1 || exit 2
fi
```

### 패턴 3: Git Branch per Session

```bash
# session-branch.sh (SessionStart)
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

git checkout -b "claude/$SESSION_ID" 2>/dev/null || true
```

## GitButler 통합

**URL**: https://blog.gitbutler.com/automate-your-ai-workflows-with-claude-code-hooks

**접근법**:
- 세션별 Git index 분리
- PreToolUse/PostToolUse에서 파일 추적
- Stop에서 세션 브랜치로 커밋

## Anthropic 공식 Best Practice

**URL**: https://www.anthropic.com/engineering/claude-code-best-practices

**주요 내용**:
- Headless mode로 GitHub 이벤트 자동화
- /project:fix-github-issue 커맨드 패턴
- 라벨 자동 할당

## 플러그인 생태계 (2025.11~)

**URL**: https://www.anthropic.com/news/claude-code-plugins

**특징**:
- slash command, agent, MCP, hook 패키지
- 한 줄 설치
- Dan Ávila: DevOps, 문서 생성, 테스트
- Seth Hobson: 80+ 전문 sub-agent
