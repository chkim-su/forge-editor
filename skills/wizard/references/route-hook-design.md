# Hook Design Route

Hook 설계 시 적합한 스킬 선택과 구현 가이드.

## Step 1: 목적 파악

```yaml
AskUserQuestion:
  question: "Hook으로 무엇을 하려고 하나요?"
  header: "Purpose"
  options:
    - label: "차단/검증 (Gate)"
      description: "특정 조건에서 도구 사용 차단, 입력 검증"
    - label: "부작용 실행 (Side Effect)"
      description: "로깅, 알림, 메모리 저장 등 추가 작업"
    - label: "AI 평가 (LLM Evaluation)"
      description: "AI로 내용 분석/판단 후 처리"
    - label: "워크플로우 제어 (Orchestration)"
      description: "다단계 작업, 상태 기반 흐름 제어"
    - label: "컨텍스트 주입 (Context Injection)"
      description: "프롬프트에 추가 정보 자동 삽입"
```

## Step 2: 결정 트리

```
목적이 뭔가요?
│
├─ 차단/검증 필요 ─────────────────────────────────────────┐
│   │                                                       │
│   ├─ 단순 조건 (파일명, 패턴) → hook-templates (Gate)   │
│   │                                                       │
│   └─ AI 판단 필요 → hook-sdk-integration + llm-sdk-guide │
│                                                           │
├─ 부작용 실행 ───────────────────────────────────────────┐
│   │                                                       │
│   ├─ 로깅/알림 → hook-templates (Side Effect)           │
│   │                                                       │
│   └─ 메모리/DB 저장 → hook-capabilities                  │
│                                                           │
├─ 워크플로우 제어 ───────────────────────────────────────┐
│   │                                                       │
│   ├─ 다단계 (phase1→phase2→...) → workflow-state-patterns│
│   │                                                       │
│   └─ 조건부 분기 → hook-capabilities + hook-templates    │
│                                                           │
└─ 컨텍스트 주입 → hook-templates (UserPromptSubmit)       │
```

## Step 3: 스킬 로드 매트릭스

| 목적 | Primary Skill | Secondary Skill | Optional |
|------|---------------|-----------------|----------|
| **Gate (단순)** | hook-templates | - | - |
| **Gate (AI)** | hook-sdk-integration | llm-sdk-guide | hook-capabilities |
| **Side Effect** | hook-templates | hook-capabilities | - |
| **Orchestration** | workflow-state-patterns | hook-templates | hook-capabilities |
| **Context Injection** | hook-templates | - | - |
| **고급 패턴** | hook-capabilities | hook-templates | hook-sdk-integration |

## Step 4: 이벤트 선택

| 이벤트 | Can Block | 용도 | 예제 |
|--------|-----------|------|------|
| `SessionStart` | ❌ | 세션 초기화 | 환경 검증, 초기 설정 |
| `UserPromptSubmit` | ✅ | 컨텍스트 주입 | 메모리 추가, 규칙 주입 |
| `PreToolUse` | ✅ | **Gate (차단)** | 파일 보호, 검증 |
| `PostToolUse` | ❌ | **Side Effect** | 로깅, 알림, 저장 |
| `Stop` | ✅ | 종료 제어 | 완료 검증, 정리 작업 |

## Step 5: 상황별 구현 가이드

### 5a. Gate Hook (단순 조건)

**로드**: `Skill("forge-editor:hook-templates")`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": { "tool_name": "Write" },
        "command": ".claude/hooks/guard-config.sh"
      }
    ]
  }
}
```

```bash
#!/bin/bash
# guard-config.sh - 설정 파일 보호
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 보호할 패턴
if [[ "$FILE_PATH" =~ \.(env|json|yaml)$ ]]; then
    echo "❌ 설정 파일 수정 차단: $FILE_PATH" >&2
    exit 2  # Block
fi

exit 0  # Allow
```

### 5b. Gate Hook (AI 평가)

**로드**:
- `Skill("forge-editor:hook-sdk-integration")`
- `Skill("forge-editor:llm-sdk-guide")`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": { "tool_name": "Write" },
        "command": "python3 .claude/hooks/ai-review.py"
      }
    ]
  }
}
```

```python
#!/usr/bin/env python3
# ai-review.py - AI 기반 코드 리뷰
import sys
import json
import asyncio
from u_llm_sdk import LLM, LLMConfig
from llm_types import Provider, ModelTier, AutoApproval

async def review_code():
    input_data = json.loads(sys.stdin.read())
    file_path = input_data.get("tool_input", {}).get("file_path", "")
    content = input_data.get("tool_input", {}).get("content", "")

    config = LLMConfig(
        provider=Provider.CLAUDE,
        tier=ModelTier.LOW,  # 비용 절감
        auto_approval=AutoApproval.FULL,
        timeout=30.0,
    )

    async with LLM(config) as llm:
        result = await llm.run(f"""
        Review this code for security issues:
        File: {file_path}
        Content:
        {content[:2000]}

        Reply ONLY "SAFE" or "UNSAFE: <reason>"
        """)

        if result.text.startswith("UNSAFE"):
            print(f"❌ {result.text}", file=sys.stderr)
            sys.exit(2)  # Block

    sys.exit(0)  # Allow

asyncio.run(review_code())
```

### 5c. Side Effect Hook (로깅/알림)

**로드**: `Skill("forge-editor:hook-templates")`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": { "tool_name": "Bash" },
        "command": ".claude/hooks/log-commands.sh"
      }
    ]
  }
}
```

```bash
#!/bin/bash
# log-commands.sh - 명령어 로깅
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
TIMESTAMP=$(date -Iseconds)

# 로그 저장
echo "$TIMESTAMP|$SESSION_ID|$COMMAND" >> ~/.claude/logs/commands.log

exit 0  # Side effect는 항상 성공
```

### 5d. Context Injection Hook

**로드**: `Skill("forge-editor:hook-templates")`

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "command": ".claude/hooks/inject-context.sh"
      }
    ]
  }
}
```

```bash
#!/bin/bash
# inject-context.sh - 프롬프트에 컨텍스트 주입
INPUT=$(cat)
USER_PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // empty')

# 프로젝트별 규칙 로드
PROJECT_RULES=$(cat .claude/rules/project-rules.md 2>/dev/null || echo "")

# 메모리에서 관련 컨텍스트 검색 (선택적)
# MEMORY=$(python3 search-memory.py "$USER_PROMPT")

# additionalContext로 주입
cat << EOF
{
  "additionalContext": "## Project Rules\n$PROJECT_RULES"
}
EOF

exit 0
```

### 5e. Workflow Hook (다단계)

**로드**: `Skill("forge-editor:workflow-state-patterns")`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": { "tool_name": "Write" },
        "command": ".claude/hooks/phase-controller.sh"
      }
    ]
  }
}
```

```bash
#!/bin/bash
# phase-controller.sh - 다단계 워크플로우
INPUT=$(cat)
STATE_FILE=".claude/state/workflow.json"

# 현재 상태 로드
if [[ -f "$STATE_FILE" ]]; then
    CURRENT_PHASE=$(jq -r '.phase' "$STATE_FILE")
else
    CURRENT_PHASE="init"
fi

case "$CURRENT_PHASE" in
    "init")
        # Phase 1 완료 조건 검사
        if [[ -f "src/schema.ts" ]]; then
            echo '{"phase": "implementation"}' > "$STATE_FILE"
            echo "✅ Phase 1 완료 → Phase 2: Implementation" >&2
        fi
        ;;
    "implementation")
        # Phase 2 완료 조건 검사
        if grep -q "export class" src/*.ts 2>/dev/null; then
            echo '{"phase": "testing"}' > "$STATE_FILE"
            echo "✅ Phase 2 완료 → Phase 3: Testing" >&2
        fi
        ;;
    "testing")
        echo "📋 Phase 3: 테스트 실행 필요" >&2
        ;;
esac

exit 0
```

### 5f. Background AI Agent Hook

**로드**:
- `Skill("forge-editor:hook-sdk-integration")`
- `Skill("forge-editor:llm-sdk-guide")`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": { "tool_name": "Write" },
        "command": ".claude/hooks/background-review.sh"
      }
    ]
  }
}
```

```bash
#!/bin/bash
# background-review.sh - 비차단 백그라운드 리뷰
INPUT=$(cat)

# Background에서 실행 (즉시 반환)
(python3 .claude/hooks/review-agent.py "$INPUT" &)

# 즉시 성공 반환
echo '{"status": "review_started"}'
exit 0
```

## Step 6: 디버깅 체크리스트

**로드**: `Skill("forge-editor:hook-capabilities")` → `references/debugging.md`

| 문제 | 확인 사항 |
|------|-----------|
| Hook 실행 안 됨 | `chmod +x`, matcher 패턴 확인 |
| 블로킹 안 됨 | `exit 2` 사용했는지, stderr 출력 확인 |
| JSON 파싱 오류 | `jq` 설치 확인, stdin 제대로 읽는지 |
| 타임아웃 | 30초 이상 걸리면 background 패턴 사용 |

## Step 7: 최종 스킬 로드 요약

사용자 답변에 따라 로드:

```
Gate (단순)      → Skill("forge-editor:hook-templates")
Gate (AI)        → Skill("forge-editor:hook-sdk-integration")
                   Skill("forge-editor:llm-sdk-guide")
Side Effect      → Skill("forge-editor:hook-templates")
                   Skill("forge-editor:hook-capabilities")
Orchestration    → Skill("forge-editor:workflow-state-patterns")
                   Skill("forge-editor:hook-templates")
Context Inject   → Skill("forge-editor:hook-templates")
고급 패턴        → Skill("forge-editor:hook-capabilities")
```

## References

- [Hook 시스템 개요](../../hook-system/SKILL.md)
- [Hook 템플릿](../../hook-templates/SKILL.md)
- [Hook 고급 기능](../../hook-capabilities/SKILL.md)
- [Hook에서 SDK 호출](../../hook-sdk-integration/SKILL.md)
- [워크플로우 패턴](../../workflow-state-patterns/SKILL.md)
