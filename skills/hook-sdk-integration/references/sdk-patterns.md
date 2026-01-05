# SDK 통합 패턴

## SDK 아키텍처 (CLI 기반)

SDK Layer (Python) → asyncio.create_subprocess_exec → Claude CLI → Anthropic API

**핵심**: SDK는 직접 API 호출하지 않고 CLI를 spawn함

## u-llm-sdk 기본 사용

```python
from u_llm_sdk import LLM, LLMConfig
from llm_types import Provider, ModelTier, AutoApproval

config = LLMConfig(
    provider=Provider.CLAUDE,
    tier=ModelTier.LOW,
    auto_approval=AutoApproval.FULL,
    timeout=60.0,
)

async with LLM(config) as llm:
    result = await llm.run("Your prompt")
```

## claude-only-sdk MCP 격리

```python
from claude_only_sdk import ClaudeAdvanced, ClaudeAdvancedConfig

config = ClaudeAdvancedConfig(
    mcp_config="./config/serena.mcp.json",
    timeout=300.0,
)

async with ClaudeAdvanced(config) as client:
    result = await client.run("Use Serena to analyze code")
```

## LLMResult 구조

| 필드 | 설명 |
|------|------|
| result.text | 응답 텍스트 |
| result.files_modified | List[FileChange] |
| result.commands_run | List[CommandRun] |
| result.session_id | 세션 ID |
| result.result_type | TEXT/CODE/FILE_EDIT/COMMAND/MIXED |

## Provider 선택

| Provider | CLI | 설명 |
|----------|-----|------|
| Provider.CLAUDE | claude | Anthropic Claude |
| Provider.CODEX | codex | OpenAI Codex |
| Provider.GEMINI | gemini | Google Gemini |

## 세션 재개

```python
llm = LLM(config).resume(session_id)
async with llm:
    result = await llm.run("Continue...")
```
