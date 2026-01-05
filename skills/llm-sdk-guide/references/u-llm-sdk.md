# U-llm-sdk Reference

Multi-provider LLM SDK providing unified interface for Claude, Codex, and Gemini.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    LLM / LLMSync                     │
│                  (Unified Client)                    │
├──────────────────────────────────────────────────────┤
│                   BaseProvider                       │
│                  (Abstract Class)                    │
├──────────────┬──────────────┬───────────────────────┤
│ ClaudeProvider│ CodexProvider │ GeminiProvider      │
│  (claude CLI) │  (codex CLI)  │  (gemini CLI)       │
└──────────────┴──────────────┴───────────────────────┘
```

---

## Configuration

### LLMConfig
```python
from u_llm_sdk import LLMConfig
from llm_types import Provider, ModelTier, AutoApproval, SandboxMode, ReasoningLevel

config = LLMConfig(
    provider=Provider.CLAUDE,           # CLAUDE | CODEX | GEMINI
    model=None,                         # Model name (None = tier-based)
    tier=ModelTier.HIGH,                # HIGH | LOW
    auto_approval=AutoApproval.EDITS_ONLY,  # NONE | EDITS_ONLY | FULL
    sandbox=SandboxMode.NONE,           # NONE | READ_ONLY | WORKSPACE_WRITE
    timeout=1200.0,                     # 20 minutes default
    reasoning_level=ReasoningLevel.MEDIUM,
    session_id=None,                    # Resume session
    intervention_hook=None,             # RAG integration
    provider_options={},                # Provider-specific
)
```

### Preset Configurations
```python
from u_llm_sdk import (
    SAFE_CONFIG,      # Read-only, requires approval
    AUTO_CONFIG,      # Auto-approve, workspace write
    CLAUDE_CONFIG,    # Claude defaults
    CODEX_CONFIG,     # Codex defaults
    GEMINI_CONFIG,    # Gemini defaults
)
```

### Builder Pattern
```python
config = (LLMConfig(provider=Provider.CLAUDE)
    .with_tier(ModelTier.HIGH)
    .with_reasoning(ReasoningLevel.XHIGH)
    .with_hook(my_hook)
    .with_web_search())
```

---

## Client Usage

### Async Client (Preferred)
```python
from u_llm_sdk import LLM, LLMConfig

async with LLM(config) as llm:
    result = await llm.run("prompt")
    print(result.text)
```

### Sync Client
```python
from u_llm_sdk import LLMSync

with LLMSync(config) as llm:
    result = llm.run("prompt")
```

### Auto Provider Selection
```python
async with LLM.auto() as llm:  # Uses Claude > Codex > Gemini
    result = await llm.run("prompt")
```

### Session Continuity
```python
# First run
result = await llm.run("Start task")
session_id = result.session_id

# Resume later
llm = LLM(config).resume(session_id)
async with llm:
    result = await llm.run("Continue...")
```

### Parallel Execution
```python
async with LLM(config) as llm:
    results = await llm.parallel_run([
        "Analyze file1.py",
        "Analyze file2.py",
        "Analyze file3.py",
    ])
```

### Streaming
```python
async with LLM(config) as llm:
    async for event in llm.stream("prompt"):
        print(event)
```

---

## Provider Details

### Model Tier Mappings
| Provider | HIGH | LOW |
|----------|------|-----|
| Claude | opus | haiku |
| Codex | gpt-5.2 + XHIGH reasoning | gpt-5.2 + LOW reasoning |
| Gemini | gemini-3-pro-preview | gemini-2.5-flash-lite |

### Provider-Specific Options
```python
# Claude
config = LLMConfig(
    provider=Provider.CLAUDE,
    provider_options={
        "allowed_tools": ["Read", "Edit", "Write"],
        "disallowed_tools": ["Bash"],
        "max_turns": 20,
        "mcp_config": "/path/to/mcp.json",
    }
)

# Codex
config = LLMConfig(
    provider=Provider.CODEX,
    provider_options={
        "instructions": "Additional instructions...",
        "context_files": ["src/main.py"],
    }
)
```

### CLI Discovery
```python
from u_llm_sdk import available_providers, get_cli_path

providers = available_providers()  # [Provider.CLAUDE, ...]
claude_path = get_cli_path(Provider.CLAUDE)  # "/usr/local/bin/claude"
```

---

## Intervention Hook Protocol

### Purpose
Enable context injection (pre-action) and feedback collection (post-action).

### Interface
```python
from u_llm_sdk import InterventionHook
from llm_types import PreActionContext

class MyHook:
    async def on_pre_action(
        self,
        prompt: str,
        provider: str,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[PreActionContext]:
        """Called BEFORE prompt. Return context to inject."""
        context = await self.fetch_relevant_context(prompt)
        return PreActionContext(
            context_chunks=[context],
            instructions="Consider this context...",
        )

    async def on_post_action(
        self,
        result: LLMResult,
        pre_action_context: Optional[PreActionContext],
        run_id: Optional[str] = None,
    ) -> None:
        """Called AFTER result. Fire-and-forget."""
        await self.record_feedback(result)
```

### Design Requirements
- **Fail-open**: Never block LLM on hook failures
- **SLO**: on_pre_action P95 < 100ms
- **Non-blocking**: Post-action is fire-and-forget

---

## Error Handling

### Exception Hierarchy
```
UnifiedLLMError (base)
├── ProviderNotFoundError      # CLI not installed
├── ProviderNotAvailableError  # Not configured
├── SessionNotFoundError       # Invalid session
├── ExecutionTimeoutError      # Exceeded timeout
├── ExecutionCancelledError    # User cancelled
├── InvalidConfigError         # Config validation
├── ParseError                 # Output parsing
├── AuthenticationError        # Auth invalid
├── RateLimitError            # API rate limited
└── ModelNotFoundError         # Model unavailable
```

### Graceful Fallback
```python
async def run_with_fallback(prompt: str) -> LLMResult:
    for provider in [Provider.CLAUDE, Provider.CODEX, Provider.GEMINI]:
        if provider not in available_providers():
            continue
        try:
            async with LLM(LLMConfig(provider=provider)) as llm:
                return await llm.run(prompt)
        except (ExecutionTimeoutError, RateLimitError):
            continue
    raise ProviderNotAvailableError("All providers failed")
```

---

## Feature Validation

```python
config = LLMConfig(
    provider=Provider.CODEX,
    reasoning_level=ReasoningLevel.XHIGH,
)

validations = config.validate_for_provider(strict=False)
for v in validations:
    if v.severity == Severity.ERROR:
        raise InvalidConfigError(v.reason)
```
