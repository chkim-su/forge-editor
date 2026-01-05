# Real-World Examples

검증된 실제 구현 사례 분석.

---

## 1. serena-refactor: State Machine Pattern

**출처**: `~/.claude/plugins/cache/serena-refactor-marketplace/serena-refactor/`

### 구조
```
워크플로우 Phase:
analyze → plan → execute → audit → complete

상태 파일:
.refactor-analysis-done
.refactor-plan-approved
.refactor-execution-done
.refactor-audit-passed
```

### PreToolUse: Phase Gate
```bash
# executor 실행 전 검사
SUBAGENT=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // ""')
[[ "$SUBAGENT" != *"executor"* ]] && exit 0

BLOCKED=0
if [ ! -f .refactor-analysis-done ]; then
    echo "❌ BLOCKED: Analysis not completed"
    BLOCKED=1
fi
if [ ! -f .refactor-plan-approved ]; then
    echo "❌ BLOCKED: Plan not approved"
    BLOCKED=1
fi

[ $BLOCKED -eq 1 ] && exit 1
```

### PostToolUse: State Creation
```bash
# analyzer 완료 후
SUBAGENT=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // ""')
[[ "$SUBAGENT" != *"analyzer"* ]] && exit 0

touch .refactor-analysis-done
echo "✓ Analysis Complete - [.refactor-analysis-done] created"
```

### PostToolUse: Conditional State (Result-Based)
```bash
# auditor 결과 검사
OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // ""')

# PASS면 상태 정리
if echo "$OUTPUT" | grep -qE 'VERDICT: PASS'; then
    touch .refactor-audit-passed
    rm -f .refactor-analysis-done .refactor-plan-approved .refactor-execution-done
fi
```

### Stop: Workflow Summary
```bash
# 세션 종료 시 상태 요약
if ls .refactor-* 2>/dev/null | grep -q .; then
    echo "⚠️ In-progress workflow:"
    ls -la .refactor-* | awk '{print "  " $NF}'
fi
```

**핵심 인사이트**:
- Hook이 State를 직접 관리 (파일 기반)
- tool_result 파싱으로 조건부 상태 변경
- PreToolUse로 phase transition 강제

---

## 2. serena-project-sync: MCP Integration

**출처**: `~/.claude/scripts/serena-project-sync.py`

### SessionStart에서 MCP 호출
```python
async def activate_project(project: str):
    base_url = "http://localhost:8765"
    
    async with httpx.AsyncClient() as client:
        # 1. SSE 연결
        async with client.stream("GET", f"{base_url}/sse") as sse:
            async for line in sse.aiter_lines():
                # 2. session_id 획득
                if "session_id=" in line:
                    session_id = line.split("session_id=")[1]
                    
                    # 3. MCP initialize
                    await client.post(
                        f"{base_url}/messages/?session_id={session_id}",
                        json={"jsonrpc": "2.0", "method": "initialize", ...}
                    )
                    
                    # 4. tools/call
                    await client.post(
                        f"{base_url}/messages/?session_id={session_id}",
                        json={
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "params": {"name": "activate_project", "arguments": {...}}
                        }
                    )
```

**핵심 인사이트**:
- Hook에서 MCP 서버와 직접 통신 가능
- SSE 프로토콜로 양방향 통신
- 세션 시작 시 자동 프로젝트 활성화

---

## 3. GitButler: Branch Management

**출처**: GitButler Docs

### 구조
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit|MultiEdit|Write",
      "hooks": [{ "command": "but claude pre-tool" }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|MultiEdit|Write",
      "hooks": [{ "command": "but claude post-tool" }]
    }],
    "Stop": [{
      "hooks": [{ "command": "but claude stop" }]
    }]
  }
}
```

**핵심 인사이트**:
- 파일 변경마다 GitButler에 알림
- 세션별 브랜치 자동 분리
- 병렬 Claude 세션도 브랜치 격리

---

## 4. claude-code-hooks-observability: Dashboard

**출처**: disler/claude-code-hooks-multi-agent-observability

### PostToolUse: 외부 서버 전송
```bash
uv run .claude/hooks/send_event.py \
    --source-app PROJECT_NAME \
    --event-type PostToolUse \
    --summarize
```

### 서버 처리
```
Event → HTTP POST → SQLite 저장 → WebSocket broadcast → Vue 대시보드
```

**핵심 인사이트**:
- Hook → HTTP → 실시간 대시보드
- 멀티 에이전트 모니터링
- 이벤트 기반 아키텍처

---

## 5. 공식 문서: Auto-formatting

**출처**: Claude Code Docs

### PostToolUse: Prettier
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "command": "jq -r '.tool_input.file_path' | xargs -I {} prettier --write {}"
      }]
    }]
  }
}
```

### Stop: Quality Gate
```bash
#!/bin/bash
pnpm install
pnpm check  # biome format + lint

if ! pnpm test:e2e; then
    echo "e2e failed" >&2
    exit 2  # Claude 계속 작업하게
fi
```

**핵심 인사이트**:
- PostToolUse로 자동 포맷팅
- Stop으로 품질 강제
- exit 2로 작업 계속 유도

---

## 6. claude-mem: Observation Storage

**출처**: `~/.claude/plugins/cache/thedotmack/claude-mem/`

### PostToolUse: 자동 저장
```javascript
// save-hook.js
// 모든 도구 결과를 자동으로 claude-mem에 저장
POST http://127.0.0.1:37777/api/sessions/observations
{
  "claudeSessionId": "...",
  "tool_name": "...",
  "tool_input": "...",
  "tool_response": "..."
}
```

### SessionStart: 컨텍스트 로드
```javascript
// context-hook.js
// 최근 observation 로드하여 Claude 컨텍스트에 주입
```

**핵심 인사이트**:
- Hook으로 모든 작업 자동 기록
- Worker HTTP API로 구조화 저장
- 세션 간 지속성 확보

---

## 패턴 요약

| 사례 | Hook 역할 | 핵심 기술 |
|------|-----------|-----------|
| serena-refactor | State Manager | 파일 기반 state machine |
| serena-project-sync | External Integrator | MCP SSE 프로토콜 |
| GitButler | Side Effect + Integrator | 외부 CLI 호출 |
| observability | External Integrator | HTTP + WebSocket |
| 공식 포맷팅 | Side Effect | 자동 도구 실행 |
| claude-mem | State + Integrator | HTTP API + 자동 저장 |
