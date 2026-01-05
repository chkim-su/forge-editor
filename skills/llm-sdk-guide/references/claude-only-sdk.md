# claude-only-sdk Reference

Advanced SDK for Claude-specific features including agents, sessions, and orchestration.

## Architecture

```
claude_only_sdk/
├── client.py           # ClaudeAdvanced, ClaudeAdvancedSync
├── config.py           # ClaudeAdvancedConfig, AgentDefinition
├── utils.py            # Quick utility functions
├── session/            # Session management
│   ├── manager.py      # SessionManager
│   ├── templates.py    # SessionTemplate enum
│   └── checkpoint.py   # CheckpointManager
├── agents/             # Agent orchestration
│   ├── executor.py     # TaskExecutor, TaskResult
│   └── orchestrator.py # AutonomousOrchestrator
├── prompt/             # Prompt handling
│   └── source.py       # PromptSource, FilePrompt, StringPrompt
└── logging/            # Stream logging
    └── stream_logger.py
```

---

## ClaudeAdvanced Client

### Basic Usage
```python
from claude_only_sdk import ClaudeAdvanced, ClaudeAdvancedConfig

config = ClaudeAdvancedConfig(
    tier=ModelTier.HIGH,
    auto_approval=AutoApproval.EDITS_ONLY,
    max_parallel_agents=3,
)

async with ClaudeAdvanced(config) as client:
    result = await client.run("Your prompt")
```

### With Template
```python
from claude_only_sdk import SessionTemplate

async with ClaudeAdvanced() as client:
    result = await client.run_with_template(
        "Review auth/login.py",
        SessionTemplate.SECURITY_ANALYST,
    )
```

### With Agents
```python
async with ClaudeAdvanced() as client:
    result = await client.run_with_agents(
        objective="Implement feature",
        agents=[planner_agent, executor_agent],
    )
```

### File-based Prompts
```python
async with ClaudeAdvanced() as client:
    result = await client.run("prompts/analyze.md")  # Reads file
    result = await client.run(
        "prompts/template.md",
        variables={"target": "src/", "focus": "security"},
    )
```

### Sync Client
```python
from claude_only_sdk import ClaudeAdvancedSync

with ClaudeAdvancedSync(config) as client:
    result = client.run("prompt")
```

---

## Quick Utilities

```python
from claude_only_sdk import (
    claude_quick_run,       # Async full result
    claude_quick_text,      # Async text only
    claude_template_run,    # Async with template
    claude_quick_run_sync,  # Sync full result
    claude_quick_text_sync, # Sync text only
    claude_template_run_sync,
)

# One-liner async
result = await claude_quick_run("Explain decorators")
text = await claude_quick_text("Explain GIL")

# One-liner sync
result = claude_quick_run_sync("Explain recursion")
text = claude_quick_text_sync("What is a closure?")

# With template
result = await claude_template_run(
    "Review auth.py",
    SessionTemplate.CODE_REVIEWER,
)
```

---

## Agent Definition

### Creating Agents
```python
from claude_only_sdk import AgentDefinition
from llm_types import ModelTier, ReasoningLevel

planner = AgentDefinition(
    name="planner",
    description="Breaks down tasks into subtasks",
    system_prompt="""You are a planning specialist.
    Break down complex tasks into clear, actionable subtasks.
    Focus on dependencies and order of execution.""",
    tier=ModelTier.HIGH,
    reasoning_level=ReasoningLevel.XHIGH,
    allowed_tools=["Read", "Grep", "Glob"],
    max_turns=10,
)

executor = AgentDefinition(
    name="executor",
    description="Implements code changes",
    system_prompt="""You are an implementation specialist.
    Execute planned changes with precision.
    Write clean, tested code.""",
    tier=ModelTier.HIGH,
    allowed_tools=["Read", "Edit", "Write", "Bash"],
)

reviewer = AgentDefinition(
    name="reviewer",
    description="Reviews code quality",
    system_prompt="You are a code review specialist...",
    tier=ModelTier.HIGH,
    allowed_tools=["Read", "Grep", "Glob"],
    disallowed_tools=["Write", "Edit"],  # Read-only
)
```

### Converting to LLMConfig
```python
# Get LLMConfig from agent
llm_config = planner.to_llm_config(base_config)

# Use with LLM
async with LLM(llm_config) as llm:
    result = await llm.run("Plan the implementation")
```

---

## Session Management

### SessionManager
```python
from claude_only_sdk import SessionManager, SessionMessage

manager = SessionManager()

# Add pre-seeded messages
manager.add_message("assistant", "I understand the codebase...")
manager.add_message("user", "Now analyze security vulnerabilities")

# Use with client
async with ClaudeAdvanced() as client:
    result = await client.run_with_session(manager, "Continue analysis")
```

### Session Templates
```python
from claude_only_sdk import SessionTemplate, get_template_prompt

# Available templates
SessionTemplate.CODE_REVIEWER
SessionTemplate.SECURITY_ANALYST
SessionTemplate.REFACTORING_EXPERT
SessionTemplate.TEST_WRITER
SessionTemplate.DOCUMENTATION_WRITER

# Get template prompt
prompt = get_template_prompt(SessionTemplate.SECURITY_ANALYST)

# Use with client
async with ClaudeAdvanced() as client:
    result = await client.run_with_template(
        "Analyze auth module",
        SessionTemplate.SECURITY_ANALYST,
    )
```

### CheckpointManager
```python
from claude_only_sdk import CheckpointManager

checkpoint_mgr = CheckpointManager(storage_path="./checkpoints")

# Save checkpoint
await checkpoint_mgr.save(
    session_id=session_id,
    state=current_state,
    metadata={"phase": "implementation"},
)

# Restore on failure
restored = await checkpoint_mgr.restore(checkpoint_id)
```

---

## Task Execution

### TaskExecutor
```python
from claude_only_sdk import TaskExecutor, TaskResult, TaskStatus

executor = TaskExecutor(config)

# Run parallel tasks
results: list[TaskResult] = await executor.run_parallel([
    ("Analyze auth module", {"focus": "security"}),
    ("Analyze data module", {"focus": "performance"}),
    ("Analyze api module", {"focus": "contracts"}),
])

for result in results:
    if result.status == TaskStatus.SUCCESS:
        print(result.output.text)
    elif result.status == TaskStatus.FAILED:
        print(f"Failed: {result.error}")
```

### AutonomousOrchestrator
```python
from claude_only_sdk import AutonomousOrchestrator, ParallelizationHint

orchestrator = AutonomousOrchestrator(config)

# Hint-based parallelization
result = await orchestrator.run(
    objective="Review and fix all security issues",
    hint=ParallelizationHint.PARALLEL_INDEPENDENT,
)

# Available hints
ParallelizationHint.SEQUENTIAL          # One at a time
ParallelizationHint.PARALLEL_INDEPENDENT # All at once
ParallelizationHint.PARALLEL_BATCHED    # Batched execution
ParallelizationHint.AUTO                # Let orchestrator decide
```

---

## Prompt Handling

### PromptSource
```python
from claude_only_sdk import (
    PromptSource,
    FilePrompt,
    StringPrompt,
    resolve_prompt,
    is_file_prompt,
)

# Auto-detection
prompt = resolve_prompt("Hello world")          # StringPrompt
prompt = resolve_prompt("prompts/review.md")    # FilePrompt

# Check type
if is_file_prompt("prompts/review.md"):
    content = FilePrompt("prompts/review.md").read()

# With variables
file_prompt = FilePrompt("prompts/template.md")
content = file_prompt.render({"target": "src/", "focus": "security"})
```

---

## Logging

### StreamLogger
```python
from claude_only_sdk import StreamLogger, LogEntry

logger = StreamLogger()

async with ClaudeAdvanced() as client:
    async for event in client.stream("prompt"):
        entry = logger.log(event)
        if entry.type == "text":
            print(entry.content, end="")
        elif entry.type == "tool_use":
            print(f"[Tool: {entry.tool_name}]")
```

---

## Configuration

### ClaudeAdvancedConfig
```python
from claude_only_sdk import ClaudeAdvancedConfig

config = ClaudeAdvancedConfig(
    # Core LLM settings
    model=None,                        # Model name (None = tier-based)
    tier=ModelTier.HIGH,
    auto_approval=AutoApproval.EDITS_ONLY,
    sandbox=SandboxMode.NONE,
    timeout=1200.0,                    # 20 minutes
    reasoning_level=ReasoningLevel.HIGH,

    # Advanced features
    max_parallel_agents=3,             # Concurrent agents
    agent_timeout_multiplier=1.5,      # Agent timeout = base * multiplier
    enable_task_tools=True,

    # Claude-specific
    mcp_config="/path/to/mcp.json",
    setting_sources=["user", "project"],
)

# Get agent timeout
agent_timeout = config.get_agent_timeout()  # 1200 * 1.5 = 1800s

# Convert to LLMConfig
llm_config = config.to_llm_config()

# Create config for specific agent
agent_config = config.with_agent(planner_agent)
```
