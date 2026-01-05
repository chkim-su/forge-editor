# Background Agent 구현

## 검증 결과 (2025-12-30)

| 테스트 | 결과 |
|--------|------|
| Hook 반환 시간 | 0.010초 (즉시) |
| Background LLM 호출 | 성공 |
| 메인 세션 영향 | 없음 |

## 패턴: Non-blocking SDK 호출

```bash
#!/bin/bash
# background-sdk-hook.sh

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
LOG_DIR=".claude/hooks/logs"
mkdir -p "$LOG_DIR"

# Background 프로세스 시작
(
    python3 /path/to/sdk-agent.py "$SESSION_ID" > "$LOG_DIR/bg-$SESSION_ID.json" 2>&1
) &

BACKGROUND_PID=$!

# 즉시 반환 (비차단)
jq -n --arg pid "$BACKGROUND_PID" '{"status": "started", "pid": $pid}'
exit 0
```

## Python Background Agent

```python
#!/usr/bin/env python3
# sdk-agent.py

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/path/to/u-llm-sdk/src")

async def background_agent(session_id: str):
    result = {"session_id": session_id, "completed": False}
    
    try:
        from u_llm_sdk import LLM, LLMConfig
        from llm_types import Provider, ModelTier, AutoApproval

        config = LLMConfig(
            provider=Provider.CLAUDE,
            tier=ModelTier.LOW,
            auto_approval=AutoApproval.FULL,
            timeout=60.0,
        )

        async with LLM(config) as llm:
            llm_result = await llm.run("Your evaluation prompt")
            result["response"] = llm_result.text[:500]
            result["completed"] = True

    except Exception as e:
        result["error"] = str(e)

    return result

if __name__ == "__main__":
    session_id = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    output = asyncio.run(background_agent(session_id))
    print(json.dumps(output, indent=2))
```

## 결과 수집 패턴

Background agent 결과를 다음 Hook에서 읽기:

```bash
#!/bin/bash
# stop-hook-collect-results.sh

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
RESULT_FILE=".claude/hooks/logs/bg-$SESSION_ID.json"

if [[ -f "$RESULT_FILE" ]]; then
    RESULT=$(cat "$RESULT_FILE")
    COMPLETED=$(echo "$RESULT" | jq -r '.completed')
    
    if [[ "$COMPLETED" == "true" ]]; then
        RESPONSE=$(echo "$RESULT" | jq -r '.response')
        echo "Background agent result: $RESPONSE"
    fi
fi

exit 0
```

## 설정 예시 (settings.json)

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/background-sdk-hook.sh"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/stop-hook-collect-results.sh"
      }]
    }]
  }
}
```

## 주의사항

1. **타임아웃**: Background 프로세스는 Hook 타임아웃(60초)과 무관
2. **결과 파일**: 세션 ID로 구분하여 충돌 방지
3. **정리**: SessionEnd 훅에서 임시 파일 정리 권장
