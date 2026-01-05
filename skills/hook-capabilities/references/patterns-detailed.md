# Hook 범용 접근법 상세

30가지 패턴의 역할, 사용법, 예시.

> **Note**: 2025-12-30 검증 결과 반영. `tool_response` (not `tool_result`), stdin JSON 기반 데이터 전달.

---

## 1. 제어 패턴 (Control)

### 1.1 Iteration Control

**역할**: 반복 횟수를 추적하고 최대 제한을 강제하여 무한 루프 방지

**사용법**:
- Stop Hook에서 반복 횟수 파일 관리
- 임계값 도달 시 exit 0으로 종료 허용

**예시**:
```bash
#!/bin/bash
# .claude/hooks/iteration-control.sh
COUNTER_FILE="/tmp/claude-iterations-$SESSION_ID"

# 카운터 증가
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

MAX_ITERATIONS=10
if [ "$COUNT" -ge "$MAX_ITERATIONS" ]; then
    echo "⚠️ Maximum iterations ($MAX_ITERATIONS) reached" >&2
    rm -f "$COUNTER_FILE"
    exit 0  # 종료 허용
fi

exit 0
```

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": ".claude/hooks/iteration-control.sh"}]}]}}
```

---

### 1.2 Force Continuation

**역할**: Claude가 종료하려 할 때 작업 계속하도록 강제

**사용법**:
- Stop Hook에서 조건 검사 후 exit 2 반환
- stderr로 이유 전달 → Claude가 읽고 계속 작업

**예시**:
```bash
#!/bin/bash
# 테스트 통과 전까지 종료 불가
if ! npm test --silent 2>/dev/null; then
    echo "❌ Tests failing - continue fixing" >&2
    exit 2  # Claude 계속 작업
fi
exit 0
```

```python
#!/usr/bin/env python3
# TODO 남아있으면 계속
import subprocess
result = subprocess.run(['grep', '-rn', 'TODO', 'src/'], capture_output=True)
if result.stdout:
    print("❌ TODOs remain - please complete them", file=sys.stderr)
    sys.exit(2)
```

**⚠️ 주의**: 무한 루프 위험. Iteration Control과 함께 사용 권장.

---

### 1.3 Promise Detection

**역할**: Claude 응답에서 특정 패턴 감지하여 조건부 종료/계속

**사용법**:
- Stop Hook에서 최근 트랜스크립트 파싱
- "DONE", "COMPLETE" 등 패턴 감지

**예시**:
```bash
#!/bin/bash
# 최근 응답에서 완료 패턴 확인
TRANSCRIPT="$HOME/.claude/projects/$(basename $PWD)/transcript.jsonl"
LAST_RESPONSE=$(tail -1 "$TRANSCRIPT" | jq -r '.content // ""')

if echo "$LAST_RESPONSE" | grep -qiE 'TASK COMPLETE|DONE|FINISHED'; then
    echo "✓ Task completion detected"
    exit 0
fi

# 미완료 패턴 감지
if echo "$LAST_RESPONSE" | grep -qiE 'TODO|FIXME|WIP'; then
    echo "❌ Incomplete work detected" >&2
    exit 2
fi
exit 0
```

---

### 1.4 Infinite Loop Prevention

**역할**: Subagent 재귀 호출로 인한 무한 루프 방지

**사용법**:
- UserPromptSubmit에서 parent_tool_use_id 확인
- Subagent 컨텍스트면 Hook 스킵

**예시**:
```python
#!/usr/bin/env python3
import json, sys

input_data = json.load(sys.stdin)

# Subagent 컨텍스트 확인
if input_data.get('parent_tool_use_id'):
    # 이미 Subagent 내부 → Hook 스킵
    sys.exit(0)

# 메인 에이전트만 처리
# ... 로직 ...
```

---

### 1.5 Threshold Branching

**역할**: 에러/경고 수에 따라 다른 동작 수행

**사용법**:
- PostToolUse에서 에러 카운트 누적
- Stop에서 임계값 기반 분기

**예시**:
```bash
#!/bin/bash
# PostToolUse: 에러 카운트 누적
ERROR_FILE="/tmp/claude-errors-$SESSION_ID"
INPUT=$(cat)
RESULT=$(echo "$INPUT" | jq -r '.tool_response // ""')

if echo "$RESULT" | grep -qiE 'error|failed|exception'; then
    COUNT=$(cat "$ERROR_FILE" 2>/dev/null || echo 0)
    echo $((COUNT + 1)) > "$ERROR_FILE"
fi
```

```bash
#!/bin/bash
# Stop: 임계값 분기
ERROR_FILE="/tmp/claude-errors-$SESSION_ID"
COUNT=$(cat "$ERROR_FILE" 2>/dev/null || echo 0)

if [ "$COUNT" -ge 5 ]; then
    echo "❌ Too many errors ($COUNT) - stopping for review" >&2
    rm -f "$ERROR_FILE"
    exit 0  # 강제 종료
elif [ "$COUNT" -ge 3 ]; then
    echo "⚠️ Multiple errors ($COUNT) - please review" >&2
fi
```

---

## 2. 입력 조작 패턴 (Input Manipulation)

### 2.1 Input Modification

**역할**: 도구 실행 전 입력 파라미터 자동 수정

**사용법**:
- PreToolUse 또는 PermissionRequest에서 JSON 응답
- `updatedInput` 필드로 수정된 입력 전달

**예시**:
```python
#!/usr/bin/env python3
# npm install에 --save-dev 자동 추가
import json, sys

input_data = json.load(sys.stdin)
tool_input = input_data.get('tool_input', {})
command = tool_input.get('command', '')

if command.startswith('npm install') and '--save-dev' not in command:
    modified_command = command + ' --save-dev'
    print(json.dumps({
        "hookSpecificOutput": {
            "decision": {"behavior": "allow", "updatedInput": {"command": modified_command}}
        }
    }))
else:
    print(json.dumps({}))
```

---

### 2.2 Path Normalization

**역할**: 상대 경로를 절대 경로로 자동 변환

**사용법**:
- PreToolUse에서 file_path 검사
- 상대 경로면 절대 경로로 변환하여 updatedInput

**예시**:
```python
#!/usr/bin/env python3
import json, sys, os

input_data = json.load(sys.stdin)
tool_input = input_data.get('tool_input', {})
file_path = tool_input.get('file_path', '')

if file_path and not file_path.startswith('/'):
    # cwd는 stdin JSON에서 가져옴 (환경변수 아님!)
    project_dir = input_data.get('cwd', os.getcwd())
    absolute_path = os.path.join(project_dir, file_path)
    
    updated_input = tool_input.copy()
    updated_input['file_path'] = absolute_path
    
    print(json.dumps({
        "hookSpecificOutput": {
            "permissionDecision": "allow",
            "updatedInput": updated_input
        }
    }))
else:
    print(json.dumps({}))
```

---

### 2.3 Environment Injection

**역할**: 명령 실행 전 필요한 환경 변수 자동 주입

**사용법**:
- PreToolUse에서 Bash 명령 감지
- 환경 변수 prefix 추가

**예시**:
```python
#!/usr/bin/env python3
import json, sys

input_data = json.load(sys.stdin)
tool_input = input_data.get('tool_input', {})
command = tool_input.get('command', '')

# Node.js 명령에 NODE_ENV 주입
if 'npm' in command or 'node' in command:
    env_prefix = 'NODE_ENV=development'
    if not command.startswith(env_prefix):
        modified = f"{env_prefix} {command}"
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "allow",
                "updatedInput": {"command": modified}
            }
        }))
        sys.exit(0)

print(json.dumps({}))
```

---

### 2.4 Dry-run Enforcement

**역할**: 위험한 명령에 --dry-run 플래그 자동 추가

**사용법**:
- PreToolUse에서 위험 명령 감지
- --dry-run 또는 유사 플래그 추가

**예시**:
```python
#!/usr/bin/env python3
import json, sys, re

input_data = json.load(sys.stdin)
command = input_data.get('tool_input', {}).get('command', '')

# 위험 명령 패턴
dangerous_patterns = [
    (r'^rm\s+-rf', '--dry-run'),  # rm -rf → 불가 (dry-run 없음)
    (r'^git push', '--dry-run'),
    (r'^npm publish', '--dry-run'),
    (r'^docker rm', '--dry-run'),
]

for pattern, flag in dangerous_patterns:
    if re.search(pattern, command) and flag not in command:
        if flag == '--dry-run' and 'rm -rf' in command:
            # rm은 dry-run 없으므로 차단
            print(f"❌ Blocked: {command}", file=sys.stderr)
            sys.exit(2)
        
        modified = f"{command} {flag}"
        print(json.dumps({
            "hookSpecificOutput": {
                "permissionDecision": "allow",
                "updatedInput": {"command": modified}
            }
        }))
        sys.exit(0)

print(json.dumps({}))
```

---

## 3. 컨텍스트 관리 패턴 (Context)

### 3.1 Context Injection

**역할**: UserPromptSubmit stdout이 Claude 컨텍스트로 자동 주입

**사용법**:
- UserPromptSubmit Hook에서 stdout 출력
- Claude가 사용자 프롬프트와 함께 받음

**예시**:
```bash
#!/bin/bash
# 현재 git 상태와 TODO를 컨텍스트로 주입
echo "=== Current Context ==="
echo "Git Status:"
git status --short 2>/dev/null | head -10

echo ""
echo "Recent TODOs:"
grep -rn "TODO" src/ 2>/dev/null | head -5

echo ""
echo "Last 3 commits:"
git log --oneline -3 2>/dev/null
echo "===================="
```

**결과**: 사용자 프롬프트에 위 정보가 자동으로 추가됨

---

### 3.2 Progressive Loading

**역할**: 필요할 때만 컨텍스트/스킬 로드하여 토큰 절약

**사용법**:
- UserPromptSubmit에서 키워드 감지
- 관련 컨텍스트만 stdout으로 출력

**예시**:
```python
#!/usr/bin/env python3
import json, sys

input_data = json.load(sys.stdin)
prompt = input_data.get('prompt', '').lower()

# 키워드 기반 컨텍스트 로딩
if 'database' in prompt or 'db' in prompt:
    print("=== Database Context ===")
    print(open('.claude/context/database.md').read())

if 'api' in prompt or 'endpoint' in prompt:
    print("=== API Context ===")
    print(open('.claude/context/api.md').read())

if 'test' in prompt:
    print("=== Testing Context ===")
    print(open('.claude/context/testing.md').read())
```

---

### 3.3 Skill Auto-Activation

**역할**: 프롬프트 키워드 분석하여 관련 스킬 자동 제안

**사용법**:
- UserPromptSubmit에서 키워드 매칭
- 스킬 사용 권장 메시지 출력

**예시**:
```python
#!/usr/bin/env python3
import json, sys

input_data = json.load(sys.stdin)
prompt = input_data.get('prompt', '').lower()

skill_mapping = {
    ('refactor', 'clean', 'solid'): 'serena-refactor',
    ('test', 'coverage', 'jest'): 'testing-patterns',
    ('api', 'endpoint', 'rest'): 'api-design',
    ('hook', 'automation'): 'hook-capabilities',
}

for keywords, skill in skill_mapping.items():
    if any(kw in prompt for kw in keywords):
        print(f"📚 Recommended: Use Skill('{skill}')")
        break
```

---

### 3.4 Transcript Parsing

**역할**: Claude의 이전 응답을 읽고 분석

**사용법**:
- Stop Hook에서 트랜스크립트 파일 읽기
- 패턴 분석 후 조건부 동작

**예시**:
```python
#!/usr/bin/env python3
import json, sys, os
from pathlib import Path

# 트랜스크립트 위치
project = os.path.basename(os.getcwd())
transcript_path = Path.home() / '.claude' / 'projects' / project / 'transcript.jsonl'

if transcript_path.exists():
    with open(transcript_path) as f:
        lines = f.readlines()
    
    # 최근 5개 메시지 분석
    recent = [json.loads(line) for line in lines[-5:]]
    
    # 에러 패턴 감지
    error_count = sum(1 for msg in recent if 'error' in str(msg).lower())
    
    if error_count >= 3:
        print("⚠️ Multiple errors detected in recent messages", file=sys.stderr)
```

---

### 3.5 Transcript Backup

**역할**: Compact 전에 트랜스크립트 백업

**사용법**:
- PreCompact Hook에서 현재 트랜스크립트 복사
- 타임스탬프로 백업 파일 생성

**예시**:
```bash
#!/bin/bash
# PreCompact: 트랜스크립트 백업
PROJECT=$(basename "$PWD")
TRANSCRIPT="$HOME/.claude/projects/$PROJECT/transcript.jsonl"
BACKUP_DIR="$HOME/.claude/backups"

mkdir -p "$BACKUP_DIR"

if [ -f "$TRANSCRIPT" ]; then
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    cp "$TRANSCRIPT" "$BACKUP_DIR/${PROJECT}-${TIMESTAMP}.jsonl"
    echo "✓ Transcript backed up"
fi
```

---

## 4. 상태 관리 패턴 (State)

### 4.1 Session Cache

**역할**: 세션 내 상태 누적 및 도구 결과 집계

**사용법**:
- PostToolUse에서 결과를 캐시 파일에 누적
- Stop에서 집계 데이터 활용

**예시**:
```bash
#!/bin/bash
# PostToolUse: 변경된 파일 추적
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

CACHE_DIR="/tmp/claude-cache-$SESSION_ID"
mkdir -p "$CACHE_DIR"

if [ -n "$FILE_PATH" ]; then
    echo "$FILE_PATH" >> "$CACHE_DIR/modified-files.txt"
fi
```

```bash
#!/bin/bash
# Stop: 세션 요약
CACHE_DIR="/tmp/claude-cache-$SESSION_ID"

if [ -d "$CACHE_DIR" ]; then
    echo "=== Session Summary ==="
    echo "Modified files:"
    sort -u "$CACHE_DIR/modified-files.txt" 2>/dev/null
    
    # 정리
    rm -rf "$CACHE_DIR"
fi
```

---

### 4.2 Session Lifecycle

**역할**: 세션 시작/종료 시 상태 초기화/정리

**사용법**:
- SessionStart: 초기 상태 설정
- SessionEnd: 정리 작업

**예시**:
```bash
#!/bin/bash
# SessionStart: 초기화
SESSION_DIR="/tmp/claude-session-$(date +%s)"
mkdir -p "$SESSION_DIR"
echo "$SESSION_DIR" > /tmp/claude-current-session

echo "✓ Session initialized: $SESSION_DIR"
```

```bash
#!/bin/bash
# SessionEnd: 정리
SESSION_DIR=$(cat /tmp/claude-current-session 2>/dev/null)

if [ -d "$SESSION_DIR" ]; then
    # 메트릭 내보내기
    echo "$(date -Iseconds) Session ended" >> ~/.claude/session-log.txt
    rm -rf "$SESSION_DIR"
fi
```

---

### 4.3 Checkpoint Commit

**역할**: 모든 파일 변경마다 checkpoint 커밋 생성

**사용법**:
- PostToolUse에서 매 변경마다 커밋
- Stop에서 squash 또는 정리

**예시**:
```bash
#!/bin/bash
# PostToolUse: checkpoint 커밋
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [ -n "$FILE_PATH" ] && [ -f "$FILE_PATH" ]; then
    git add "$FILE_PATH"
    git commit -m "checkpoint: $(basename $FILE_PATH)" --no-verify 2>/dev/null
fi
```

```bash
#!/bin/bash
# Stop: checkpoint squash
CHECKPOINT_COUNT=$(git log --oneline | grep -c "^checkpoint:")

if [ "$CHECKPOINT_COUNT" -gt 1 ]; then
    echo "💡 $CHECKPOINT_COUNT checkpoints created"
    echo "Run 'git rebase -i HEAD~$CHECKPOINT_COUNT' to squash"
fi
```

---

### 4.4 Session Branching

**역할**: 세션별로 Git 브랜치 자동 격리 (GitButler 패턴)

**사용법**:
- PreToolUse: 세션별 인덱스 생성
- PostToolUse: 세션 인덱스에 파일 추가
- Stop: 세션 브랜치에 커밋

**예시**:
```bash
#!/bin/bash
# PreToolUse: 세션 인덱스 초기화
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

INDEX_FILE="/tmp/git-index-$SESSION_ID"
if [ ! -f "$INDEX_FILE" ]; then
    # HEAD 기준으로 새 인덱스 생성
    GIT_INDEX_FILE="$INDEX_FILE" git read-tree HEAD
fi
```

```bash
#!/bin/bash
# PostToolUse: 세션 인덱스에 추가
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [ -n "$FILE_PATH" ]; then
    INDEX_FILE="/tmp/git-index-$SESSION_ID"
    GIT_INDEX_FILE="$INDEX_FILE" git add "$FILE_PATH"
fi
```

```bash
#!/bin/bash
# Stop: 세션 브랜치에 커밋
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

INDEX_FILE="/tmp/git-index-$SESSION_ID"
if [ -f "$INDEX_FILE" ]; then
    TREE=$(GIT_INDEX_FILE="$INDEX_FILE" git write-tree)
    COMMIT=$(git commit-tree "$TREE" -p HEAD -m "Session $SESSION_ID")
    git update-ref "refs/heads/claude/$SESSION_ID" "$COMMIT"
    
    echo "✓ Changes committed to branch: claude/$SESSION_ID"
    rm -f "$INDEX_FILE"
fi
```

---

## 5. 외부 연동 패턴 (Integration)

### 5.1 Notification Forwarding

**역할**: Claude 알림을 외부 서비스로 전달

**사용법**:
- Notification Hook에서 메시지 파싱
- HTTP POST로 Slack/Discord 등에 전달

**예시**:
```python
#!/usr/bin/env python3
import json, sys, os
import urllib.request

input_data = json.load(sys.stdin)
message = input_data.get('message', '')

# Slack Webhook
webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
if webhook_url:
    payload = json.dumps({"text": f"🤖 Claude: {message}"})
    req = urllib.request.Request(webhook_url, 
                                  data=payload.encode(),
                                  headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req)
```

---

### 5.2 Desktop/Audio Alert

**역할**: 데스크톱 알림 또는 TTS 음성 피드백

**사용법**:
- Notification Hook에서 OS별 알림 명령 실행
- TTS 라이브러리로 음성 출력

**예시**:
```bash
#!/bin/bash
# 플랫폼별 데스크톱 알림
INPUT=$(cat)
MESSAGE=$(echo "$INPUT" | jq -r '.message // "Claude needs attention"')

case "$(uname)" in
    Darwin)
        osascript -e "display notification \"$MESSAGE\" with title \"Claude Code\""
        # TTS
        say "Claude needs your input"
        ;;
    Linux)
        notify-send "Claude Code" "$MESSAGE"
        # TTS (espeak)
        espeak "Claude needs your input" 2>/dev/null
        ;;
esac
```

---

### 5.3 Subagent Correlation

**역할**: tool_use_id로 부모-자식 Subagent 관계 추적

**사용법**:
- SubagentStop에서 tool_use_id 기록
- 부모 에이전트와 상관관계 분석

**예시**:
```python
#!/usr/bin/env python3
import json, sys
from datetime import datetime

input_data = json.load(sys.stdin)
tool_use_id = input_data.get('tool_use_id', 'unknown')
parent_id = input_data.get('parent_tool_use_id', 'root')

# 상관관계 로깅
log_entry = {
    "timestamp": datetime.now().isoformat(),
    "tool_use_id": tool_use_id,
    "parent_id": parent_id,
    "type": "subagent_stop"
}

with open('/tmp/claude-subagent-trace.jsonl', 'a') as f:
    f.write(json.dumps(log_entry) + '\n')

print(f"✓ Subagent {tool_use_id[:8]} completed (parent: {parent_id[:8]})")
```

---

## 6. 보안/규정 패턴 (Security)

### 6.1 Auto-Approval

**역할**: 특정 도구/명령 자동 승인하여 반복 권한 요청 제거

**사용법**:
- PermissionRequest Hook에서 패턴 매칭
- "allow" 결정 반환

**예시**:
```python
#!/usr/bin/env python3
import json, sys, re

input_data = json.load(sys.stdin)
tool_name = input_data.get('tool_name', '')
tool_input = input_data.get('tool_input', {})
command = tool_input.get('command', '')

# 자동 승인 패턴
auto_approve_patterns = [
    r'^npm (test|run|install)',
    r'^git (status|log|diff|branch)',
    r'^ls\b',
    r'^cat\b',
    r'^grep\b',
]

for pattern in auto_approve_patterns:
    if re.search(pattern, command):
        print(json.dumps({
            "hookSpecificOutput": {
                "decision": {"behavior": "allow"}
            }
        }))
        sys.exit(0)

# 기본: 사용자 확인 요청
print(json.dumps({}))
```

---

### 6.2 Secret Scanning

**역할**: API 키, 비밀번호 등 민감 정보 감지 및 차단

**사용법**:
- PreToolUse에서 파일 내용/명령 검사
- 민감 정보 패턴 발견 시 차단

**예시**:
```python
#!/usr/bin/env python3
import json, sys, re

input_data = json.load(sys.stdin)
tool_input = input_data.get('tool_input', {})

# 검사 대상: 파일 내용 또는 명령
content = tool_input.get('content', '') + tool_input.get('command', '')

# 민감 정보 패턴
secret_patterns = [
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Token'),
    (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----', 'Private Key'),
    (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded Password'),
]

for pattern, name in secret_patterns:
    if re.search(pattern, content):
        print(f"🚫 BLOCKED: Potential {name} detected", file=sys.stderr)
        sys.exit(2)
```

---

### 6.3 Compliance Audit

**역할**: 규정 준수 로깅 및 위반 감지

**사용법**:
- PostToolUse에서 모든 작업 로깅
- 정책 위반 시 경고

**예시**:
```python
#!/usr/bin/env python3
import json, sys
from datetime import datetime

input_data = json.load(sys.stdin)

# 감사 로그 생성
audit_entry = {
    "timestamp": datetime.now().isoformat(),
    "tool": input_data.get('tool_name'),
    "input": input_data.get('tool_input'),
    "user": os.environ.get('USER'),
    "cwd": input_data.get('cwd')
}

# 로깅
with open('/var/log/claude-audit.jsonl', 'a') as f:
    f.write(json.dumps(audit_entry) + '\n')

# 정책 위반 검사
file_path = input_data.get('tool_input', {}).get('file_path', '')
if '/production/' in file_path or '/prod/' in file_path:
    print("⚠️ WARNING: Production file modified - logged for review", file=sys.stderr)
```

---

## 7. 구현 기법 패턴 (Implementation)

### 7.1 TypeScript Delegation

**역할**: 복잡한 로직을 TypeScript 파일로 위임

**사용법**:
- Bun 또는 tsx로 TypeScript 직접 실행
- 타입 안전한 Hook 로직 구현

**예시**:
```json
{"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "bun run .claude/hooks/validator.ts"}]}]}}
```

```typescript
// .claude/hooks/validator.ts
import { stdin } from 'process';

interface HookInput {
  session_id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

let data = '';
stdin.on('data', chunk => data += chunk);
stdin.on('end', () => {
  const input: HookInput = JSON.parse(data);
  
  // 타입 안전한 검증 로직
  if (input.tool_name === 'Bash') {
    const command = input.tool_input.command as string;
    if (command.includes('rm -rf /')) {
      console.error('❌ Blocked dangerous command');
      process.exit(2);
    }
  }
});
```

---

### 7.2 Hook Chaining

**역할**: 여러 Hook을 순서대로 실행

**사용법**:
- hooks 배열에 여러 Hook 정의
- 순서대로 실행, 하나라도 실패 시 중단

**예시**:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [
        {"type": "command", "command": ".claude/hooks/format.sh"},
        {"type": "command", "command": ".claude/hooks/lint.sh"},
        {"type": "command", "command": ".claude/hooks/track.sh"}
      ]
    }]
  }
}
```

---

### 7.3 Background Execution

**역할**: 비동기로 Hook 실행하여 Claude 응답 차단 안함

**사용법**:
- 명령 끝에 `&` 추가
- 또는 설정에서 `run_in_background: true`

**예시**:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/slow-analysis.sh &"
      }]
    }]
  }
}
```

---

### 7.4 Argument Pattern Matching

**역할**: 특정 인자 패턴에만 Hook 적용

**사용법**:
- Matcher에 `Tool(pattern*)` 형식 사용
- 인자 기반 필터링

**예시**:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(npm test*)",
        "hooks": [{"type": "command", "command": "echo '🧪 Running tests...'"}]
      },
      {
        "matcher": "Bash(git push*)",
        "hooks": [{"type": "command", "command": ".claude/hooks/pre-push-check.sh"}]
      }
    ]
  }
}
```

---

### 7.5 MCP Tool Matching

**역할**: MCP 서버 도구에 Hook 적용

**사용법**:
- Matcher에 `mcp__servername__toolname` 패턴
- 와일드카드 `.*` 지원

**예시**:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__memory__.*",
        "hooks": [{"type": "command", "command": "echo '💾 Memory operation'"}]
      },
      {
        "matcher": "mcp__github__create_pull_request",
        "hooks": [{"type": "command", "command": ".claude/hooks/pr-check.sh"}]
      }
    ]
  }
}
```

---

### 7.6 Prompt-Type Hook

**역할**: LLM이 Hook 결정을 평가 (비용 발생)

**사용법**:
- `type: "prompt"` 설정
- LLM이 평가하여 결정

**예시**:
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "prompt",
        "prompt": "Review whether the task is complete. If all requirements are met, respond with 'complete'. If work remains, respond with 'continue' and specify what needs to be done."
      }]
    }]
  }
}
```

**⚠️ 주의**: API 비용 발생, 느림. 단순 규칙은 command 타입 권장.

---

## 빠른 참조표

| # | 패턴 | Event | 핵심 메커니즘 |
|---|------|-------|--------------|
| 1 | Iteration Control | Stop | 카운터 파일 + exit 2/0 |
| 2 | Force Continuation | Stop | exit 2 → Claude 계속 |
| 3 | Promise Detection | Stop | transcript 분석 |
| 4 | Infinite Loop Prevention | Stop | stop_hook_active 확인 |
| 5 | Threshold Branching | Stop | 에러 카운트 임계값 |
| 6 | Input Modification | PreToolUse | updatedInput JSON |
| 7 | Path Normalization | PreToolUse | cwd + 상대경로 |
| 8 | Environment Injection | PreToolUse | 명령 프리픽스 |
| 9 | Dry-run Enforcement | PreToolUse | 플래그 자동 추가 |
| 10 | Context Injection | UserPromptSubmit | stdout → 컨텍스트 |
| 11 | Progressive Loading | UserPromptSubmit | 키워드 조건부 로드 |
| 12 | Skill Auto-Activation | UserPromptSubmit | 패턴 → 스킬 제안 |
| 13 | Transcript Parsing | Stop | jsonl 파일 분석 |
| 14 | Transcript Backup | PreCompact | 파일 복사 |
| 15 | Session Cache | PostToolUse | JSON 파일 누적 |
| 16 | Session Lifecycle | Start/End | 초기화/정리 |
| 17 | Checkpoint Commit | PostToolUse | git commit |
| 18 | Session Branching | SessionStart | git branch 격리 |
| 19 | Notification Forwarding | Notification | HTTP webhook |
| 20 | Desktop/Audio Alert | Notification | osascript/notify-send |
| 21 | Subagent Correlation | SubagentStop | tool_use_id 추적 |
| 22 | Auto-Approval | PermissionRequest | permissionDecision: allow |
| 23 | Secret Scanning | PreToolUse | regex 패턴 차단 |
| 24 | Compliance Audit | PostToolUse | 감사 로그 기록 |
| 25 | TypeScript Delegation | Any | bun/tsx 실행 |
| 26 | Hook Chaining | Any | hooks 배열 순차 실행 |
| 27 | Background Execution | Any | & 또는 background 옵션 |
| 28 | Argument Pattern | PreToolUse | Bash(npm test*) |
| 29 | MCP Tool Matching | PreToolUse | mcp__*__.* |
| 30 | Prompt-Type Hook | Any | type: "prompt" |

---

## 검증 상태 (2025-12-30)

| 항목 | 상태 | 참고 |
|------|------|------|
| stdin JSON 전달 | ✅ 검증됨 | session_id, cwd, transcript_path |
| tool_response (PostToolUse) | ✅ 검증됨 | tool_result 아님 |
| stop_hook_active | ✅ 검증됨 | Stop 이벤트 전용 |
| tool_use_id | ✅ 검증됨 | Pre/PostToolUse |
| updatedInput | 미검증 | 새 세션 필요 |
| permissionDecision | 미검증 | PermissionRequest 필요 |
| prompt-type hook | 미검증 | 별도 테스트 필요 |
