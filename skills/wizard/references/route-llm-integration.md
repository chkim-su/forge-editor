# LLM Integration Route

LLM 직접 호출이 필요한 상황에서의 가이드.

## Step 1: 상황 파악

```yaml
AskUserQuestion:
  question: "LLM을 어디서 호출하려고 하나요?"
  header: "Context"
  options:
    - label: "Hook에서"
      description: "PreToolUse, PostToolUse 등에서 AI 평가"
    - label: "에이전트/스킬에서"
      description: "서브에이전트 또는 스킬 내부에서 LLM 호출"
    - label: "백그라운드 처리"
      description: "비차단 Background Agent 실행"
    - label: "MCP 격리 세션"
      description: "특정 MCP만 로드된 별도 세션"
```

## Step 2: 필수 스킬 로드

**CRITICAL**: LLM 직접 호출 시 반드시 SDK 가이드 로드

```
Skill("forge-editor:llm-sdk-guide")
```

## Step 3: 상황별 가이드

### Hook에서 LLM 호출

**추가 로드**: `Skill("forge-editor:hook-sdk-integration")`

```bash
# Background Agent 패턴 (권장)
(python3 sdk-agent.py "$INPUT" &)
echo '{"status": "started"}'
exit 0
```

| 패턴 | 장점 | 단점 |
|------|------|------|
| Background (`&`) | 비차단, 즉시 반환 | 결과 대기 불가 |
| Foreground | 결과 활용 가능 | ~30초 지연 |
| `type: "prompt"` | 빠름 | 격리 불가 |

### 에이전트/스킬에서 LLM 호출

```python
from u_llm_sdk import LLM, LLMConfig
from llm_types import Provider, ModelTier

config = LLMConfig(
    provider=Provider.CLAUDE,
    tier=ModelTier.HIGH,  # or LOW for cost savings
)

async with LLM(config) as llm:
    result = await llm.run("Your prompt")
```

### 백그라운드 처리

```python
from claude_only_sdk import ClaudeAdvanced, TaskExecutor

async with ClaudeAdvanced() as client:
    executor = TaskExecutor(client)
    # 병렬 실행
    results = await executor.run_parallel([
        "Task 1",
        "Task 2",
    ])
```

### MCP 격리 세션

```python
from claude_only_sdk import ClaudeAdvanced, ClaudeAdvancedConfig

config = ClaudeAdvancedConfig(
    mcp_config="./serena-only.mcp.json",  # 특정 MCP만 로드
    timeout=300.0,
)

async with ClaudeAdvanced(config) as client:
    result = await client.run("Use Serena MCP only")
```

## Step 4: SDK 선택 가이드

| 상황 | SDK | 이유 |
|------|-----|------|
| Multi-provider 지원 필요 | u-llm-sdk | Claude, Codex, Gemini 통합 |
| Claude 전용 고급 기능 | claude-only-sdk | 에이전트, 세션, 오케스트레이션 |
| 간단한 호출 | u-llm-sdk | 더 간단한 API |
| 복잡한 워크플로우 | claude-only-sdk | TaskExecutor, AutonomousOrchestrator |

## Step 5: 비용 구조

| 방식 | 비용 | 비고 |
|------|------|------|
| SDK → CLI | 구독 포함 | 추가 비용 없음 |
| `type: "prompt"` | 구독 포함 | 세션 내 실행 |
| 직접 API 호출 | 토큰 과금 | 피해야 함 |
| 로컬 LLM (ollama) | 무료 | 프라이버시 우선 시 |

## Step 6: 코드 템플릿 생성

사용자 상황에 맞는 코드 생성:

```python
# Template variables
CONTEXT = "hook" | "agent" | "background" | "mcp_isolated"
SDK = "u-llm-sdk" | "claude-only-sdk"
TIER = "HIGH" | "LOW"
```

생성할 파일:
- `scripts/llm-caller.py` - 메인 SDK 호출 로직
- `config/llm-config.json` - 설정 파일 (필요 시)

## References

- [U-llm-sdk 상세](../../../llm-sdk-guide/references/u-llm-sdk.md)
- [Claude-only-sdk 상세](../../../llm-sdk-guide/references/claude-only-sdk.md)
- [Hook에서 SDK 호출](../../hook-sdk-integration/references/sdk-patterns.md)
- [Background Agent 패턴](../../hook-sdk-integration/references/background-agent.md)
