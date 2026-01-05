# Event Details

각 Hook Event의 상세 스펙.

## SessionStart

**Trigger**: 세션 시작 또는 재개 시
**Block 가능**: ❌
**입력 데이터** (검증됨):
```json
{
  "session_id": "uuid",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/project/path",
  "hook_event_name": "SessionStart",
  "source": "compact"  // "compact" (재개) 또는 "new" (신규)
}
```

**활용**:
- MCP 서버 활성화 (SSE 연결, tools/call)
- 프로젝트 컨텍스트 로드
- 환경 변수 설정
- 워커 프로세스 시작

---

## UserPromptSubmit

**Trigger**: 사용자가 메시지 전송 시 (Claude 처리 전)
**Block 가능**: ✅
**입력 데이터** (검증됨):
```json
{
  "session_id": "uuid",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/project/path",
  "permission_mode": "default",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "사용자 입력 텍스트"
}
```

**★ 특별 기능: Context Injection**
- **stdout이 Claude 컨텍스트로 자동 주입됨**
- 프롬프트에 추가 정보 삽입 가능

**활용**:
- 프롬프트 검증/필터링
- 키워드 기반 스킬 제안
- 컨텍스트 자동 주입 (git status, TODO 등)
- 보안 필터링

---

## PreToolUse

**Trigger**: 도구 실행 직전
**Block 가능**: ✅ (exit 2)
**입력 데이터** (검증됨):
```json
{
  "session_id": "uuid",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/project/path",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List files"
  },
  "tool_use_id": "toolu_01..."
}
```

**Matcher 패턴**:
```
"Bash"                    # 정확한 매칭
"Edit|Write|MultiEdit"    # OR 매칭
"Bash(npm test*)"         # 인자 패턴 매칭
"mcp__memory__.*"         # MCP 도구 매칭
"*"                       # 전체 매칭
```

**활용**:
- 위험 명령 차단 (rm -rf, sudo)
- 보호 파일 수정 방지 (.env, .git)
- 워크플로우 전제조건 검사
- Subagent 타입별 분기 처리
- Secret Scanning (API 키 감지)

---

## PostToolUse

**Trigger**: 도구 실행 완료 후
**Block 가능**: ❌ (이미 실행됨)
**입력 데이터** (검증됨):
```json
{
  "session_id": "uuid",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/project/path",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PostToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "...", "description": "..." },
  "tool_response": { ... },  // 도구 실행 결과
  "tool_use_id": "toolu_01..."
}
```

> **Note**: `tool_result`가 아닌 `tool_response` 필드명 사용

**활용**:
- 상태 파일 생성/삭제
- 결과 기반 조건부 처리
- 자동 포맷팅 (prettier, black)
- 자동 커밋 (git add && commit)
- 변경 사항 추적/로깅
- 외부 서버 알림
- 세션별 브랜치 분리

---

## PermissionRequest

**Trigger**: 권한 다이얼로그 표시 시
**Block 가능**: ✅
**입력 데이터**:
```json
{
  "session_id": "uuid",
  "tool_name": "Bash",
  "tool_input": { "command": "npm install" },
  "cwd": "/project/path"
}
```

**★ 특별 기능: Input Modification**
```json
{
  "hookSpecificOutput": {
    "decision": {
      "behavior": "allow",
      "updatedInput": {
        "command": "npm install --save-dev"
      }
    }
  }
}
```

**활용**:
- 특정 작업 자동 승인
- 도구 입력 자동 수정/보강
- 정책 기반 권한 관리

---

## Stop

**Trigger**: Claude가 응답 종료하려 할 때
**Block 가능**: ✅ (exit 2로 계속 유도)
**입력 데이터** (검증됨):
```json
{
  "session_id": "uuid",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/project/path",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "Stop",
  "stop_hook_active": false  // 무한 루프 방지 플래그
}
```

> **Note**: `stop_hook_active`가 `true`면 이미 Stop 훅이 실행 중이므로 추가 블록 금지

**활용**:
- End-of-turn 품질 검사
- 의존성 설치 강제
- 미커밋 변경사항 경고
- 워크플로우 상태 요약
- 반복 횟수 제한
- Promise Detection

---

## SubagentStop

**Trigger**: Task(Subagent)가 종료하려 할 때
**Block 가능**: ✅
**입력 데이터**: Stop과 유사

**활용**:
- Subagent 결과 검증
- Subagent별 품질 기준 적용

---

## Notification

**Trigger**: Claude가 알림 발생 시
**Block 가능**: ❌
**입력 데이터** (검증됨):
```json
{
  "session_id": "uuid",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/project/path",
  "hook_event_name": "Notification",
  "message": "Claude is waiting for your input",
  "notification_type": "idle_prompt"  // 알림 유형
}
```

**활용**:
- 데스크톱 알림 (osascript, notify-send)
- TTS 음성 피드백
- 외부 로깅

---

## PreCompact

**Trigger**: Context compact 직전
**Block 가능**: ❌
**입력 데이터** (검증됨):
```json
{
  "session_id": "uuid",
  "transcript_path": "/home/user/.claude/projects/.../session.jsonl",
  "cwd": "/project/path",
  "hook_event_name": "PreCompact",
  "trigger": "auto",  // "auto" 또는 "manual"
  "custom_instructions": null  // 커스텀 지시 (있으면 문자열)
}
```

**활용**:
- 중요 컨텍스트 보존
- 상태 백업

---

## SessionEnd

**Trigger**: 세션 종료 시
**Block 가능**: ❌

**활용**:
- 정리 작업
- 메트릭 내보내기
- 세션 요약 생성

---

## Hook Type: Prompt

`type: "command"` 외에 `type: "prompt"` 지원:

```json
{
  "hooks": [{
    "type": "prompt",
    "prompt": "이 작업이 안전한지 평가해주세요: {{tool_input}}"
  }]
}
```

LLM이 평가하여 결정 (비용 발생, 느림)

---

## 공통 필드 및 환경변수

### 모든 이벤트에 공통으로 포함되는 필드
| 필드 | 설명 |
|------|------|
| `session_id` | 세션 고유 ID (UUID) |
| `transcript_path` | 세션 transcript 파일 경로 |
| `cwd` | 현재 작업 디렉토리 |
| `hook_event_name` | 이벤트 타입명 |

### 환경변수 (⚠️ 중요 수정사항)

**검증 결과**: 문서에 언급된 `CLAUDE_PROJECT_DIR`, `CLAUDE_SESSION_ID` 등은 **환경변수가 아닙니다**.

이 정보들은 **stdin JSON**을 통해 전달됩니다:
- `session_id` → stdin JSON의 필드
- `cwd` → stdin JSON의 필드 (프로젝트 디렉토리)
- `transcript_path` → stdin JSON의 필드

**실제 설정되는 환경변수** (검증됨):
```bash
CLAUDE_CODE_ENABLE_CFC="false"
CLAUDE_CODE_ENTRYPOINT="cli"
```

### 설정 리로드
- `settings.json` 변경은 **새 세션에서만 적용**됨
- 런타임 중 훅 설정 변경 → 세션 재시작 필요
