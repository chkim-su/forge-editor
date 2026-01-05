# Advanced Hook Patterns

고급 Hook 패턴의 일반론적 접근법과 구현 예제.

---

## 1. Iteration Control (반복 제어)

### 일반론적 접근

**목적**: Claude가 작업을 반복 수행하도록 강제하고, 최대 반복 횟수를 제한

**핵심 원리**:
1. 상태 파일에 현재 iteration 저장
2. Stop hook에서 iteration 체크
3. 최대 도달 전 → exit 2로 종료 차단 + 프롬프트 재전송
4. 최대 도달 후 → exit 0으로 종료 허용

**적용 시나리오**:
- 자율 에이전트 루프 (무한 반복 방지)
- 자동 리팩토링 사이클
- 테스트-수정 반복 루프

### 구현 예제

**상태 파일 형식** (`.claude/loop-state.md`):
```markdown
---
iteration: 3
max_iterations: 10
task: "버그 수정 완료까지 반복"
---
[Claude에게 전달할 프롬프트]
```

**Stop Hook** (`iteration-control.sh`):
```bash
#!/bin/bash
set -euo pipefail

STATE_FILE=".claude/loop-state.md"
HOOK_INPUT=$(cat)

# 상태 파일 없으면 종료 허용
[[ ! -f "$STATE_FILE" ]] && exit 0

# YAML frontmatter 파싱
ITERATION=$(sed -n '/^---$/,/^---$/p' "$STATE_FILE" | grep '^iteration:' | sed 's/iteration: *//')
MAX_ITER=$(sed -n '/^---$/,/^---$/p' "$STATE_FILE" | grep '^max_iterations:' | sed 's/max_iterations: *//')

# 최대 반복 도달 시 종료 허용
if [[ $ITERATION -ge $MAX_ITER ]]; then
    echo "🛑 최대 반복($MAX_ITER) 도달"
    rm "$STATE_FILE"
    exit 0
fi

# iteration 증가
NEXT=$((ITERATION + 1))
sed -i "s/^iteration: .*/iteration: $NEXT/" "$STATE_FILE"

# 프롬프트 추출 (frontmatter 이후)
PROMPT=$(awk '/^---$/{i++; next} i>=2' "$STATE_FILE")

# 종료 차단 + 프롬프트 재전송
jq -n --arg p "$PROMPT" --arg m "🔄 Iteration $NEXT/$MAX_ITER" \
  '{"decision":"block", "reason":$p, "systemMessage":$m}'
```

### 작동 시나리오

```
사용자: "모든 테스트가 통과할 때까지 버그를 수정해"

[Iteration 1] Claude: 첫 번째 버그 수정
→ Stop hook: iteration=1 < max=5, 종료 차단
→ "버그 수정 완료까지 반복" 프롬프트 재전송

[Iteration 2] Claude: 두 번째 버그 수정
→ Stop hook: iteration=2 < max=5, 종료 차단

[Iteration 3] Claude: 테스트 모두 통과!
→ 사용자가 /cancel-loop 실행 또는 max 도달까지 계속
```

---

## 2. Promise Detection (약속 패턴 감지)

### 일반론적 접근

**목적**: Claude가 특정 문구를 출력하면 조기에 루프 종료

**핵심 원리**:
1. 상태 파일에 `completion_promise` 정의
2. Stop hook에서 transcript 파싱
3. Claude 응답에 `<promise>...</promise>` 태그 감지
4. promise 내용이 일치하면 종료 허용

**적용 시나리오**:
- 목표 달성 시 자동 종료
- 조건부 완료 (테스트 통과, 빌드 성공 등)
- 에이전트 자율 판단 종료

### 구현 예제

**상태 파일** (`.claude/promise-loop.md`):
```markdown
---
iteration: 0
max_iterations: 20
completion_promise: "모든 테스트 통과"
---
테스트를 실행하고 실패하면 수정하세요.
완료되면 <promise>모든 테스트 통과</promise>를 출력하세요.
```

**Stop Hook** (`promise-detection.sh`):
```bash
#!/bin/bash
set -euo pipefail

STATE_FILE=".claude/promise-loop.md"
HOOK_INPUT=$(cat)

[[ ! -f "$STATE_FILE" ]] && exit 0

# completion_promise 추출
PROMISE=$(sed -n '/^---$/,/^---$/p' "$STATE_FILE" | \
  grep '^completion_promise:' | sed 's/completion_promise: *//' | \
  sed 's/^"\(.*\)"$/\1/')

# transcript에서 마지막 assistant 응답 추출
TRANSCRIPT=$(echo "$HOOK_INPUT" | jq -r '.transcript_path')
LAST_OUTPUT=$(grep '"role":"assistant"' "$TRANSCRIPT" | tail -1 | \
  jq -r '.message.content | map(select(.type=="text")) | map(.text) | join("\n")')

# <promise>...</promise> 태그 추출
PROMISE_TEXT=$(echo "$LAST_OUTPUT" | \
  perl -0777 -pe 's/.*?<promise>(.*?)<\/promise>.*/$1/s' 2>/dev/null || echo "")

# promise 일치 시 종료 허용
if [[ -n "$PROMISE_TEXT" ]] && [[ "$PROMISE_TEXT" = "$PROMISE" ]]; then
    echo "✅ Promise 달성: $PROMISE"
    rm "$STATE_FILE"
    exit 0
fi

# promise 미달성 → 계속
# (iteration control과 결합 가능)
exit 0  # 또는 iteration 로직
```

### 작동 시나리오

```
사용자: 테스트 통과까지 수정 반복 설정

[Iteration 1] Claude: 테스트 실행 → 3개 실패, 수정 시도
[Iteration 2] Claude: 재실행 → 1개 실패, 추가 수정
[Iteration 3] Claude: 재실행 → 모두 통과!
             출력: "<promise>모든 테스트 통과</promise>"
→ Stop hook: promise 감지! 루프 종료
```

---

## 3. Transcript Parsing (응답 분석)

### 일반론적 접근

**목적**: Claude의 이전 응답을 읽고 분석하여 조건부 처리

**핵심 원리**:
1. Stop hook의 입력에서 `transcript_path` 획득
2. JSONL 형식 transcript 파일 파싱
3. `role: assistant` 메시지 필터링
4. 텍스트 내용 추출 및 패턴 매칭

**적용 시나리오**:
- 응답 품질 검사
- 특정 패턴/키워드 감지
- 에러 메시지 자동 처리

### 구현 예제

```bash
#!/bin/bash
# transcript-analyzer.sh

HOOK_INPUT=$(cat)
TRANSCRIPT=$(echo "$HOOK_INPUT" | jq -r '.transcript_path')

# 모든 assistant 응답 추출
RESPONSES=$(grep '"role":"assistant"' "$TRANSCRIPT")

# 마지막 응답만
LAST=$(echo "$RESPONSES" | tail -1)

# 텍스트 추출
TEXT=$(echo "$LAST" | jq -r '
  .message.content |
  map(select(.type == "text")) |
  map(.text) |
  join("\n")
')

# 패턴 분석 예시
if echo "$TEXT" | grep -q "ERROR:"; then
    echo "❌ 에러 감지됨 - 수정 필요" >&2
    exit 2
fi

if echo "$TEXT" | grep -q "TODO:"; then
    echo "⚠️ 미완료 작업 존재" >&2
    exit 2
fi

exit 0
```

---

## 4. Session Cache (세션 캐시)

### 일반론적 접근

**목적**: 세션 동안 발생한 이벤트/결과를 누적 저장

**핵심 원리**:
1. PostToolUse에서 도구 실행 결과 캐시
2. 세션 ID 기반 디렉토리 분리
3. Stop hook에서 누적 데이터 분석
4. 세션 종료 시 캐시 정리

**적용 시나리오**:
- 편집된 파일 목록 추적
- 영향받은 repository 관리
- 빌드 명령 자동 수집

### 구현 예제

**PostToolUse Hook** (`session-cache.sh`):
```bash
#!/bin/bash
set -euo pipefail

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

CACHE_DIR=".claude/session-cache/$SESSION_ID"
mkdir -p "$CACHE_DIR"

# Edit/Write 도구면 파일 경로 기록
if [[ "$TOOL_NAME" =~ ^(Edit|Write|MultiEdit)$ ]]; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
    if [[ -n "$FILE_PATH" ]]; then
        echo "$FILE_PATH" >> "$CACHE_DIR/edited-files.txt"

        # 중복 제거
        sort -u "$CACHE_DIR/edited-files.txt" -o "$CACHE_DIR/edited-files.txt"
    fi
fi

# Bash 도구면 명령어 기록
if [[ "$TOOL_NAME" == "Bash" ]]; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    echo "$COMMAND" >> "$CACHE_DIR/commands.txt"
fi

exit 0
```

**Stop Hook에서 활용** (`session-summary.sh`):
```bash
#!/bin/bash

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
CACHE_DIR=".claude/session-cache/$SESSION_ID"

if [[ -f "$CACHE_DIR/edited-files.txt" ]]; then
    FILE_COUNT=$(wc -l < "$CACHE_DIR/edited-files.txt")
    echo "📝 이 세션에서 $FILE_COUNT 개 파일 수정됨"

    # TypeScript 파일이 있으면 tsc 실행
    if grep -q "\.tsx\?$" "$CACHE_DIR/edited-files.txt"; then
        if ! npx tsc --noEmit 2>&1; then
            echo "❌ TypeScript 에러 발견" >&2
            exit 2
        fi
    fi
fi

exit 0
```

### 작동 시나리오

```
[PostToolUse] Edit src/auth.ts → 캐시에 기록
[PostToolUse] Edit src/login.tsx → 캐시에 기록
[PostToolUse] Write tests/auth.test.ts → 캐시에 기록

[Stop] 세션 캐시 분석:
→ 3개 파일 수정됨
→ .ts/.tsx 파일 존재 → tsc 실행
→ 에러 발견 → exit 2 → Claude 계속 작업
```

---

## 5. Threshold Branching (임계값 분기)

### 일반론적 접근

**목적**: 에러/경고 수에 따라 다른 처리 전략 적용

**핵심 원리**:
1. 도구 실행 결과에서 에러 수 카운트
2. 임계값에 따른 분기 처리
3. 소량 에러 → 직접 수정 요청
4. 대량 에러 → 전문 에이전트 위임

**적용 시나리오**:
- TypeScript 컴파일 에러 처리
- 린트 경고 처리
- 테스트 실패 처리

### 구현 예제

```bash
#!/bin/bash
# threshold-handler.sh (Stop hook)

# TSC 실행 및 에러 카운트
TSC_OUTPUT=$(npx tsc --noEmit 2>&1 || true)
ERROR_COUNT=$(echo "$TSC_OUTPUT" | grep -cE "\.tsx?.*error TS[0-9]+" || echo 0)

if [[ $ERROR_COUNT -eq 0 ]]; then
    echo "✅ TypeScript 컴파일 성공"
    exit 0

elif [[ $ERROR_COUNT -le 3 ]]; then
    # 소량 에러 → 직접 수정 요청
    echo "⚠️ $ERROR_COUNT 개 에러 발견 - 직접 수정하세요:" >&2
    echo "$TSC_OUTPUT" >&2
    exit 2

elif [[ $ERROR_COUNT -le 10 ]]; then
    # 중간 에러 → 상세 정보 제공
    echo "🔶 $ERROR_COUNT 개 에러 발견" >&2
    echo "가장 심각한 에러들:" >&2
    echo "$TSC_OUTPUT" | head -20 >&2
    exit 2

else
    # 대량 에러 → 에이전트 위임 제안
    echo "🔴 $ERROR_COUNT 개 에러 - auto-error-resolver 사용 권장" >&2
    echo "에러 요약: 타입 불일치, 누락된 import 등" >&2
    exit 2
fi
```

### 작동 시나리오

```
[시나리오 1: 에러 0개]
→ "✅ TypeScript 컴파일 성공"
→ exit 0 → 종료 허용

[시나리오 2: 에러 2개]
→ "⚠️ 2개 에러 발견" + 상세 에러
→ exit 2 → Claude가 직접 수정

[시나리오 3: 에러 15개]
→ "🔴 15개 에러 - auto-error-resolver 사용 권장"
→ exit 2 → Claude가 에이전트 호출 결정
```

---

## 6. TypeScript Delegation (TS 위임)

### 일반론적 접근

**목적**: 복잡한 로직을 TypeScript로 구현하여 유지보수성 향상

**핵심 원리**:
1. Bash wrapper가 stdin을 TypeScript로 전달
2. TypeScript에서 복잡한 파싱/분석 수행
3. JSON 출력으로 결과 반환
4. npx tsx로 즉시 실행 (컴파일 불필요)

**적용 시나리오**:
- 복잡한 JSON 파싱
- 파일 분석 로직
- 외부 API 호출

### 구현 예제

**Bash Wrapper** (`skill-activation.sh`):
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cat | npx tsx skill-activation.ts
```

**TypeScript Handler** (`skill-activation.ts`):
```typescript
import { readFileSync } from 'fs';

interface HookInput {
  session_id: string;
  prompt: string;
  cwd: string;
}

interface SkillRule {
  keywords: string[];
  skill: string;
  description: string;
}

async function main() {
  // stdin 읽기
  const input: HookInput = JSON.parse(
    readFileSync('/dev/stdin', 'utf-8')
  );

  // skill-rules.json 로드
  const rules: SkillRule[] = JSON.parse(
    readFileSync('.claude/skill-rules.json', 'utf-8')
  );

  // 프롬프트 분석
  const prompt = input.prompt.toLowerCase();
  const suggestions: string[] = [];

  for (const rule of rules) {
    if (rule.keywords.some(kw => prompt.includes(kw))) {
      suggestions.push(`/${rule.skill} - ${rule.description}`);
    }
  }

  // 제안 출력 (stdout → 사용자에게 표시)
  if (suggestions.length > 0) {
    console.log('💡 추천 스킬:');
    suggestions.forEach(s => console.log(`  ${s}`));
  }
}

main().catch(console.error);
```

---

## 7. Skill Auto-Activation (스킬 자동 활성화)

### 일반론적 접근

**목적**: 사용자 프롬프트나 파일 컨텍스트 분석하여 관련 스킬 자동 제안

**핵심 원리**:
1. UserPromptSubmit hook에서 프롬프트 분석
2. `skill-rules.json`에 키워드-스킬 매핑 정의
3. 매칭되는 스킬 stdout으로 제안
4. 사용자가 선택적으로 사용

**적용 시나리오**:
- "커밋" 언급 시 /commit 스킬 제안
- TypeScript 파일 수정 시 타입 체크 스킬 제안
- 테스트 관련 질문 시 테스트 스킬 제안

### 구현 예제

**skill-rules.json**:
```json
[
  {
    "keywords": ["커밋", "commit", "git add"],
    "skill": "commit",
    "description": "변경사항 커밋"
  },
  {
    "keywords": ["리뷰", "review", "PR", "pull request"],
    "skill": "review-pr",
    "description": "코드 리뷰"
  },
  {
    "keywords": ["테스트", "test", "jest", "vitest"],
    "skill": "run-tests",
    "description": "테스트 실행"
  }
]
```

**UserPromptSubmit Hook**:
```bash
#!/bin/bash

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt' | tr '[:upper:]' '[:lower:]')

# 간단한 키워드 매칭 (복잡하면 TS 위임)
if echo "$PROMPT" | grep -qE "커밋|commit"; then
    echo "💡 추천: /commit - 변경사항 커밋하기"
fi

if echo "$PROMPT" | grep -qE "리뷰|review|pr"; then
    echo "💡 추천: /review-pr - 코드 리뷰하기"
fi

exit 0
```

---

## 8. Progressive Loading (점진적 로딩)

### 일반론적 접근

**목적**: 필요할 때만 컨텍스트나 스킬을 로드하여 효율성 향상

**핵심 원리**:
1. 초기 로드는 최소화
2. 특정 조건 충족 시 추가 컨텍스트 로드
3. PreToolUse에서 도구별 컨텍스트 주입
4. 불필요한 정보 로드 방지

**적용 시나리오**:
- 대규모 프로젝트 가이드라인 선택적 로드
- 도구별 전문 지침 주입
- 파일 타입별 규칙 로드

### 구현 예제

**PreToolUse Hook** (`progressive-context.sh`):
```bash
#!/bin/bash

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

# 도구별 컨텍스트 로드
case "$TOOL_NAME" in
    "Edit"|"Write")
        FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

        # TypeScript 파일이면 TS 가이드라인 로드
        if [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.tsx ]]; then
            if [[ -f ".claude/guides/typescript.md" ]]; then
                echo "📘 TypeScript 가이드라인:"
                cat ".claude/guides/typescript.md"
            fi
        fi

        # 테스트 파일이면 테스트 가이드라인 로드
        if [[ "$FILE_PATH" == *.test.* ]] || [[ "$FILE_PATH" == *.spec.* ]]; then
            if [[ -f ".claude/guides/testing.md" ]]; then
                echo "📘 테스트 작성 가이드라인:"
                cat ".claude/guides/testing.md"
            fi
        fi
        ;;

    "Bash")
        COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

        # git 명령이면 git 가이드라인 로드
        if echo "$COMMAND" | grep -q "^git "; then
            if [[ -f ".claude/guides/git-conventions.md" ]]; then
                echo "📘 Git 컨벤션:"
                cat ".claude/guides/git-conventions.md"
            fi
        fi
        ;;
esac

exit 0
```

### 작동 시나리오

```
[Claude가 src/auth.ts 수정 시도]
→ PreToolUse: Edit 도구, .ts 파일 감지
→ typescript.md 가이드라인 stdout으로 출력
→ Claude가 가이드라인 참고하여 수정

[Claude가 auth.test.ts 작성 시도]
→ PreToolUse: Write 도구, .test.ts 파일 감지
→ testing.md 가이드라인 stdout으로 출력
→ Claude가 테스트 규칙 따라 작성
```

---

## 패턴 조합 예시

### 자율 에이전트 루프

**Iteration Control + Promise Detection + Threshold Branching** 조합:

```bash
#!/bin/bash
# autonomous-agent.sh (Stop hook)

STATE_FILE=".claude/agent-state.md"
HOOK_INPUT=$(cat)

[[ ! -f "$STATE_FILE" ]] && exit 0

# 1. Promise Detection
TRANSCRIPT=$(echo "$HOOK_INPUT" | jq -r '.transcript_path')
LAST=$(grep '"role":"assistant"' "$TRANSCRIPT" | tail -1 | jq -r '...')
if echo "$LAST" | grep -q "<promise>TASK_COMPLETE</promise>"; then
    echo "✅ 작업 완료!"
    rm "$STATE_FILE"
    exit 0
fi

# 2. Threshold Branching
ERROR_COUNT=$(npx tsc --noEmit 2>&1 | grep -c "error TS" || echo 0)
if [[ $ERROR_COUNT -gt 10 ]]; then
    echo "🔴 에러 과다 - 전략 재검토 필요" >&2
fi

# 3. Iteration Control
ITER=$(grep '^iteration:' "$STATE_FILE" | sed 's/iteration: *//')
MAX=$(grep '^max_iterations:' "$STATE_FILE" | sed 's/max_iterations: *//')

if [[ $ITER -ge $MAX ]]; then
    echo "🛑 최대 반복 도달"
    rm "$STATE_FILE"
    exit 0
fi

# 계속 진행
sed -i "s/^iteration: .*/iteration: $((ITER + 1))/" "$STATE_FILE"
PROMPT=$(awk '/^---$/{i++; next} i>=2' "$STATE_FILE")

jq -n --arg p "$PROMPT" --arg m "🔄 Iteration $((ITER+1))/$MAX | Errors: $ERROR_COUNT" \
  '{"decision":"block", "reason":$p, "systemMessage":$m}'
```

---

## 9. Input Modification (입력 수정)

### 일반론적 접근

**목적**: PermissionRequest에서 도구 입력을 자동으로 수정/보강

**핵심 원리**:
1. PermissionRequest hook에서 tool_input 분석
2. `updatedInput` 필드로 수정된 입력 반환
3. Claude가 수정된 입력으로 도구 실행

**적용 시나리오**:
- npm 명령에 자동으로 플래그 추가
- 파일 경로 자동 보정
- 명령어 보안 강화

### 구현 예제

```bash
#!/bin/bash
# input-modifier.sh (PermissionRequest hook)

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# npm install에 자동으로 --save-dev 추가
if [[ "$TOOL_NAME" == "Bash" ]] && echo "$COMMAND" | grep -q "^npm install"; then
    MODIFIED=$(echo "$COMMAND" | sed 's/npm install/npm install --save-dev/')

    jq -n --arg cmd "$MODIFIED" '{
      "hookSpecificOutput": {
        "decision": {
          "behavior": "allow",
          "updatedInput": {"command": $cmd}
        }
      }
    }'
    exit 0
fi

# 기본: 그대로 허용
echo '{"hookSpecificOutput":{"decision":{"behavior":"allow"}}}'
```

### 작동 시나리오

```
[Claude가 실행하려는 명령]
npm install lodash

[PermissionRequest hook]
→ npm install 감지
→ --save-dev 플래그 추가

[실제 실행되는 명령]
npm install --save-dev lodash
```

---

## 10. Context Injection (컨텍스트 주입)

### 일반론적 접근

**목적**: UserPromptSubmit에서 자동으로 추가 컨텍스트를 Claude에게 주입

**핵심 원리**:
1. UserPromptSubmit hook에서 stdout 출력
2. 출력 내용이 Claude 컨텍스트에 자동 추가
3. Claude가 추가 정보를 참고하여 응답

**적용 시나리오**:
- git status 자동 주입
- TODO 목록 자동 표시
- 최근 에러 로그 주입

### 구현 예제

```bash
#!/bin/bash
# context-injector.sh (UserPromptSubmit hook)

# 현재 git 상태 주입
echo "📋 현재 Git 상태:"
git status --short 2>/dev/null || echo "(git 저장소 아님)"
echo ""

# 미완료 TODO 주입
if [[ -f "TODO.md" ]]; then
    echo "📝 미완료 TODO:"
    grep -E "^\s*-\s*\[ \]" TODO.md | head -5
    echo ""
fi

# 최근 에러 로그 주입
if [[ -f ".claude/last-error.log" ]]; then
    echo "⚠️ 마지막 에러:"
    tail -5 ".claude/last-error.log"
    echo ""
fi

exit 0
```

### 작동 시나리오

```
[사용자 입력]
"버그 수정해줘"

[UserPromptSubmit hook 실행]
stdout 출력:
📋 현재 Git 상태:
 M src/auth.ts
 M src/login.tsx

📝 미완료 TODO:
- [ ] 로그인 에러 핸들링

⚠️ 마지막 에러:
TypeError: Cannot read property 'user' of undefined

[Claude가 받는 컨텍스트]
사용자 입력 + 위 정보 자동 포함
→ Claude가 맥락을 파악하고 정확한 수정
```

---

## 11. Secret Scanning (비밀 정보 감지)

### 일반론적 접근

**목적**: API 키, 비밀번호 등이 코드에 포함되면 차단

**핵심 원리**:
1. PreToolUse에서 Edit/Write 도구 입력 검사
2. 정규식으로 비밀 정보 패턴 감지
3. 감지 시 exit 2로 차단 + 경고

**적용 시나리오**:
- API 키 하드코딩 방지
- 비밀번호 노출 방지
- 개인정보 보호

### 구현 예제

```bash
#!/bin/bash
# secret-scanner.sh (PreToolUse hook, matcher: "Edit|Write")

INPUT=$(cat)
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')

# 비밀 정보 패턴
PATTERNS=(
    'AKIA[0-9A-Z]{16}'                    # AWS Access Key
    'sk-[a-zA-Z0-9]{48}'                  # OpenAI API Key
    'ghp_[a-zA-Z0-9]{36}'                 # GitHub Personal Token
    'password\s*[:=]\s*["\x27][^"\x27]+'  # password = "..."
    'api[_-]?key\s*[:=]\s*["\x27][^"\x27]+' # api_key = "..."
)

for PATTERN in "${PATTERNS[@]}"; do
    if echo "$CONTENT" | grep -qiE "$PATTERN"; then
        echo "🔴 비밀 정보 감지됨!" >&2
        echo "패턴: $PATTERN" >&2
        echo "환경변수나 .env 파일을 사용하세요." >&2
        exit 2
    fi
done

exit 0
```

### 작동 시나리오

```
[Claude가 시도하는 코드]
const apiKey = "sk-abc123...";  // OpenAI API Key

[PreToolUse hook]
→ 패턴 매칭: sk-[a-zA-Z0-9]{48}
→ "🔴 비밀 정보 감지됨!"
→ exit 2 → 쓰기 차단

[Claude 응답]
"비밀 정보가 감지되어 차단되었습니다.
환경변수를 사용하도록 수정하겠습니다:
const apiKey = process.env.OPENAI_API_KEY;"
```

---

## 12. Desktop/Audio Alert (데스크톱 알림)

### 일반론적 접근

**목적**: Notification 이벤트를 데스크톱 알림이나 음성으로 전달

**핵심 원리**:
1. Notification hook에서 메시지 추출
2. OS별 알림 도구 호출
3. 선택적으로 TTS(Text-to-Speech) 사용

**적용 시나리오**:
- 장시간 작업 완료 알림
- 에러 발생 즉시 알림
- 중요 이벤트 음성 안내

### 구현 예제

```bash
#!/bin/bash
# desktop-alert.sh (Notification hook)

INPUT=$(cat)
MESSAGE=$(echo "$INPUT" | jq -r '.message')

# macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "display notification \"$MESSAGE\" with title \"Claude Code\""
    # TTS (선택)
    say "$MESSAGE" &

# Linux
elif command -v notify-send &>/dev/null; then
    notify-send "Claude Code" "$MESSAGE"
    # TTS (선택)
    if command -v espeak &>/dev/null; then
        espeak "$MESSAGE" &
    fi

# Windows (WSL)
elif command -v powershell.exe &>/dev/null; then
    powershell.exe -Command "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null; \$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText01); \$template.GetElementsByTagName('text')[0].AppendChild(\$template.CreateTextNode('$MESSAGE')) | Out-Null; [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude').Show([Windows.UI.Notifications.ToastNotification]::new(\$template))"
fi

exit 0
```

---

## 13. Prompt-Type Hook (LLM 기반 평가)

### 일반론적 접근

**목적**: 복잡한 판단이 필요한 경우 LLM으로 평가

**핵심 원리**:
1. `type: "prompt"` 훅 정의
2. 템플릿에 도구 입력 삽입
3. LLM이 평가하여 허용/차단 결정

**주의사항**:
- API 비용 발생
- 응답 지연 있음
- 복잡한 판단에만 사용

### 구현 예제

**settings.json**:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "prompt",
        "prompt": "다음 bash 명령이 안전한지 평가하세요:\n\n명령: {{tool_input.command}}\n\n위험한 경우 'BLOCK: [이유]'로 시작하고,\n안전한 경우 'ALLOW'로 시작하세요."
      }]
    }]
  }
}
```

### 작동 시나리오

```
[Claude가 실행하려는 명령]
rm -rf /tmp/cache/*

[Prompt-Type Hook]
LLM에게 질문:
"다음 bash 명령이 안전한지 평가하세요:
명령: rm -rf /tmp/cache/*"

[LLM 응답]
"ALLOW - /tmp/cache 디렉토리 정리는 안전합니다."

[결과]
→ 명령 실행 허용
```

---

## 패턴 조합 예시

### 보안 강화 파이프라인

**Secret Scanning + Input Modification + Threshold Branching** 조합:

```bash
#!/bin/bash
# security-pipeline.sh

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

# 1. Secret Scanning
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')
if echo "$CONTENT" | grep -qiE 'sk-[a-zA-Z0-9]{48}'; then
    echo "🔴 API 키 감지 - 차단" >&2
    exit 2
fi

# 2. Input Modification (Bash 명령 안전화)
if [[ "$TOOL" == "Bash" ]]; then
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command')
    # rm 명령에 -i 플래그 강제
    if echo "$CMD" | grep -q "^rm "; then
        SAFE_CMD=$(echo "$CMD" | sed 's/^rm /rm -i /')
        jq -n --arg c "$SAFE_CMD" '{
          "hookSpecificOutput": {
            "decision": {"behavior":"allow", "updatedInput":{"command":$c}}
          }
        }'
        exit 0
    fi
fi

# 3. 기본 허용
exit 0
```

---

## 요약

| 패턴 | 핵심 기술 | 주요 용도 |
|------|----------|----------|
| Iteration Control | 상태 파일 + sed | 반복 제한 |
| Promise Detection | Transcript + perl | 조건부 종료 |
| Transcript Parsing | jq + grep | 응답 분석 |
| Session Cache | 세션별 디렉토리 | 결과 누적 |
| Threshold Branching | 에러 카운트 + 조건문 | 분기 처리 |
| TS Delegation | npx tsx | 복잡 로직 |
| Skill Auto-Activation | 키워드 매칭 | 스킬 제안 |
| Progressive Loading | 조건부 cat | 선택적 컨텍스트 |
| **Input Modification** | updatedInput JSON | 입력 자동 수정 |
| **Context Injection** | stdout → 컨텍스트 | 자동 정보 주입 |
| **Secret Scanning** | 정규식 패턴 매칭 | 비밀 정보 차단 |
| **Desktop Alert** | osascript/notify-send | 알림 연동 |
| **Prompt-Type Hook** | type: "prompt" | LLM 기반 평가 |

---

## 14. Hook에서 LLM 호출

Hook에서 Claude CLI나 SDK를 통해 LLM을 호출하는 패턴은 별도 스킬로 분리되었습니다.

**→ [hook-sdk-integration](../../hook-sdk-integration/SKILL.md) 스킬 참조**

포함 내용:
- CLI 직접 호출 패턴
- u-llm-sdk / claude-only-sdk 사용법
- Background Agent (비차단 실행)
- 비용 최적화 전략
- 실제 GitHub 프로젝트 사례
