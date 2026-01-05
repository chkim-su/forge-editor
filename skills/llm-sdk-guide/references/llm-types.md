# llm-types Reference

Pure type definitions shared across the LLM SDK ecosystem. Zero external dependencies.

---

## Configuration Enums

### Provider
```python
from llm_types import Provider

Provider.CLAUDE   # Claude CLI
Provider.CODEX    # Codex CLI
Provider.GEMINI   # Gemini CLI
```

### ModelTier
```python
from llm_types import ModelTier

ModelTier.HIGH    # Best quality (opus, gpt-5.2, gemini-3-pro)
ModelTier.LOW     # Fast/cheap (haiku, flash-lite)
```

### AutoApproval
```python
from llm_types import AutoApproval

AutoApproval.NONE        # Require approval for everything
AutoApproval.EDITS_ONLY  # Auto-approve edits only
AutoApproval.FULL        # Auto-approve everything
```

### SandboxMode
```python
from llm_types import SandboxMode

SandboxMode.NONE            # No sandbox
SandboxMode.READ_ONLY       # Read-only access
SandboxMode.WORKSPACE_WRITE # Write within workspace
SandboxMode.FULL_ACCESS     # Full access
```

### ReasoningLevel
```python
from llm_types import ReasoningLevel

ReasoningLevel.NONE    # No explicit reasoning
ReasoningLevel.LOW     # Minimal reasoning
ReasoningLevel.MEDIUM  # Balanced (default)
ReasoningLevel.HIGH    # Detailed reasoning
ReasoningLevel.XHIGH   # Maximum reasoning (expensive)
```

---

## Data Models

### LLMResult
```python
from llm_types import LLMResult, ResultType

@dataclass
class LLMResult:
    success: bool
    result_type: ResultType      # TEXT | CODE | FILE_EDIT | COMMAND | ERROR | MIXED
    provider: str                # "claude" | "codex" | "gemini"
    model: str
    text: str                    # Response text (may be empty for FILE_EDIT!)
    summary: str                 # Quick summary
    files_modified: list[FileChange]
    commands_run: list[CommandRun]
    code_blocks: list[CodeBlock]
    structured_output: Optional[dict]
    error: Optional[str]
    token_usage: TokenUsage
    session_id: Optional[str]
    duration_ms: int
```

### FileChange
```python
@dataclass
class FileChange:
    path: str           # File path
    operation: str      # "create" | "modify" | "delete"
    diff: Optional[str] # Unified diff
    content: Optional[str]
```

### CommandRun
```python
@dataclass
class CommandRun:
    command: str
    exit_code: int
    stdout: str
    stderr: str
```

### CodeBlock
```python
@dataclass
class CodeBlock:
    language: str
    code: str
    filename: Optional[str]
```

### TokenUsage
```python
@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Optional[float]
```

---

## Hook Data

### PreActionContext
```python
from llm_types import PreActionContext

@dataclass
class PreActionContext:
    context_chunks: list[str]    # Context to inject
    instructions: Optional[str]  # Additional instructions
    metadata: dict[str, Any]     # Extra metadata
```

### PostActionFeedback
```python
from llm_types import PostActionFeedback

@dataclass
class PostActionFeedback:
    run_id: str
    success: bool
    quality_score: Optional[float]
    feedback_text: Optional[str]
```

---

## Exceptions

### Hierarchy
```python
from llm_types import (
    UnifiedLLMError,           # Base exception
    ProviderNotFoundError,     # CLI not installed
    ProviderNotAvailableError, # Not configured
    SessionNotFoundError,      # Invalid session
    ExecutionTimeoutError,     # Timeout exceeded
    ExecutionCancelledError,   # User cancelled
    InvalidConfigError,        # Config validation
    ParseError,                # Output parsing
    AuthenticationError,       # Auth invalid
    RateLimitError,           # API rate limited
    ModelNotSpecifiedError,    # No model selected
    ModelNotFoundError,        # Model unavailable
)
```

### Usage
```python
try:
    async with LLM(config) as llm:
        result = await llm.run("prompt")
except ProviderNotFoundError as e:
    print(f"Install CLI: {e.provider}")
except ExecutionTimeoutError:
    print("Timeout - try shorter prompt or longer timeout")
except RateLimitError:
    print("Rate limited - wait and retry")
```

---

## Orchestration Types

### Roles
```python
from llm_types.orchestration import OrchestratorRole, WorkerRole

OrchestratorRole.COORDINATOR
OrchestratorRole.REVIEWER
OrchestratorRole.ESCALATOR

WorkerRole.ANALYZER
WorkerRole.IMPLEMENTER
WorkerRole.TESTER
WorkerRole.DOCUMENTER
```

### Clarity
```python
from llm_types.orchestration import ClarityLevel, ClarityGate

ClarityLevel.LOW      # Unclear, needs clarification
ClarityLevel.MEDIUM   # Partially clear
ClarityLevel.HIGH     # Clear enough to proceed
ClarityLevel.PERFECT  # Fully specified
```

### Delegation
```python
from llm_types.orchestration import ClaudeCodeDelegation, BoundaryConstraints

delegation = ClaudeCodeDelegation(
    task="Implement feature",
    boundaries=BoundaryConstraints(
        allowed_tools=["Read", "Edit", "Write"],
        allowed_paths=["src/"],
        max_file_changes=5,
        require_tests=True,
    ),
)
```

---

## Chronicle Types (Immutable Audit)

```python
from llm_types.chronicle import (
    DecisionRecord,    # LLM decision/request
    ExecutionRecord,   # Actual execution
    FailureRecord,     # Failure tracking
    EvidenceRecord,    # Supporting evidence
    AmendRecord,       # Record corrections
)

# Record IDs
# DECN_abc123 - Decision
# EXEC_def456 - Execution
# FAIL_ghi789 - Failure
# EVID_jkl012 - Evidence
```

---

## Feature Validation

```python
from llm_types import Feature, FeatureValidationResult, Severity

@dataclass
class FeatureValidationResult:
    feature: str
    provider: str
    severity: Severity      # ERROR | WARNING | INFO
    supported: bool
    reason: str
    suggestion: Optional[str]
```

---

## Stage & Budgets

```python
from llm_types import Stage, STAGE_TOKEN_BUDGETS

Stage.PLANNING
Stage.IMPLEMENTATION
Stage.TESTING
Stage.REVIEW

STAGE_TOKEN_BUDGETS = {
    Stage.PLANNING: 10000,
    Stage.IMPLEMENTATION: 50000,
    Stage.TESTING: 20000,
}
```
