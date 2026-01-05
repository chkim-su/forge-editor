# ANALYZE Route

Two-layer analysis: static validation + semantic understanding via diagnostic agents.

## Architecture

```
Layer 1: Static Validation (fast, deterministic)
└─ validate_all.py → W0XX codes

Layer 2: Semantic Analysis (deep understanding)
└─ diagnostic-orchestrator → coordinates agents
   ├─ content-quality-analyzer → language/emoji/comments
   ├─ hook-reasoning-engine → WHERE and HOW for hooks
   ├─ intent-analyzer → 6 core questions
   ├─ architectural-smell-detector → pattern violations
   └─ extraction-recommender → script/agent/skill extraction
```

## Approach: Adaptive Analysis

Do NOT follow a fixed checklist. Adapt to project type and static findings.

### Intent Detection

When user request is unclear, use semantic understanding:

| User Says | Intent | Action |
|-----------|--------|--------|
| "전반적으로 검토해줘" | Overall verification | BOTH validation + analysis |
| "validate" / "check" | Quick validation | Layer 1 only |
| "analyze" / "review" | Deep analysis | Layer 1 + Layer 2 |
| "뭔가 이상해" | Debug/investigate | Layer 2 focus |

**If unclear**: Use `AskUserQuestion` to clarify:
```yaml
AskUserQuestion:
  question: "What type of verification do you need?"
  header: "Scope"
  options:
    - label: "Quick Validation"
      description: "Schema, paths, structure only (~1s)"
    - label: "Full Analysis (Recommended)"
      description: "Validation + semantic analysis (~30s)"
    - label: "Deep Diagnostics"
      description: "All agents + detailed recommendations"
```

---

## Step 1: Understand Context

- Project type: plugin, skill library, agent suite?
- Primary purpose?
- Complexity level: simple/standard/advanced?

## Step 2: Run Static Validation (Layer 1)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json
```

Parse results for W0XX codes to determine which semantic agents to dispatch.

## Step 3: Dispatch Semantic Agents (Layer 2)

Based on static findings, launch agents via Task tool:

| Static Finding | Agent to Dispatch |
|---------------|-------------------|
| W028 (enforcement keywords) | `hook-reasoning-engine` |
| W030 (missing tools) | `intent-analyzer` |
| W031/W032 (content issues) | `content-quality-analyzer` |
| Multiple similar errors | `architectural-smell-detector` |
| Complex structure | `extraction-recommender` |
| Any .md files | `content-quality-analyzer` (language check) |

For comprehensive analysis, dispatch `diagnostic-orchestrator`:

```yaml
Task:
  subagent_type: diagnostic-orchestrator
  prompt: "Run comprehensive analysis with all semantic agents"
```

## Step 4: Analyze Based on Project Type

| Project Type | Focus Areas | Primary Agents |
|--------------|-------------|----------------|
| **Skill library** | Skill design, SKILL.md quality | content-quality-analyzer, intent-analyzer |
| **Agent suite** | Orchestration, context isolation | architectural-smell-detector, intent-analyzer |
| **Full plugin** | All + hookify, deployment | All agents via orchestrator |
| **MCP integration** | Gateway patterns, isolation | architectural-smell-detector |

## Step 5: Load Relevant Skills

- skills/ directory → `Skill("forge-editor:skill-design")`
- agents/ directory → `Skill("forge-editor:orchestration-patterns")`
- hooks/ directory → Hookify compliance check
- MCP usage → `Skill("forge-editor:mcp-gateway-patterns")`

## Step 6: Critical Analysis (via intent-analyzer)

The `intent-analyzer` agent applies 6 core questions automatically.

### 6a: 6 Core Questions

| Question | What to Ask |
|----------|-------------|
| Existence Justification | "Why does this exist?" |
| Intent-Implementation Alignment | "Does name match role?" |
| Consistency | "Are similar things handled differently?" |
| Unused Capabilities | "Is anything declared but not used?" |
| Complexity Justification | "Is this complexity necessary?" |
| Fundamental Redesign | "Is the system itself wrong?" |

### 6b: Canonical Pattern Comparison

| Domain | Skill | Compare Against |
|--------|-------|-----------------|
| MCP | mcp-gateway-patterns | daemon-shared-server.md |
| Skill | skill-design | structure-rules.md |
| Agent | orchestration-patterns | context-isolation.md |
| Hooks | hook-templates | full-examples.md |

**Verdict**: Deficient → Recommend | Respectable → Acknowledge | Superior → Learn

## Step 7: Solution Synthesis (PROACTIVE)

> HOOKIFIED: `PostToolUse:Task → solution-synthesis-gate.py`

### 7a: Load Skills for Problems Found

| Problem | Action |
|---------|--------|
| MCP/Gateway issues | `Skill("mcp-gateway-patterns")` → Read daemon-shared-server.md |
| Skill design issues | `Skill("skill-design")` → Read structure-rules.md |
| Agent context issues | `Skill("orchestration-patterns")` → Read context-isolation.md |

### 7b: Extract and Present Solutions

**DO**: Load skill → Read references → Extract concrete solution
**DON'T**: Just say "load this skill"

### 7c: Known Solutions

| Problem | Solution | Command |
|---------|----------|---------|
| Subagent cannot access MCP | Daemon SSE | `python -m mcp_server --sse` |
| Long SKILL.md | Progressive disclosure | Create `references/` |
| Document enforcement fails | Hookify | PreToolUse hooks |

### 7d: Radical Solutions 🔥

When conservative solutions feel like band-aids:
- "Is the system structure wrong?"
- "If there's a 10x better method, what is it?"

### 7e: Execution Proposal

```yaml
AskUserQuestion:
  question: "Apply extracted solutions?"
  header: "Execute"
  multiSelect: true
  options:
    - label: "Apply All (Recommended)"
    - label: "Analysis only"
```

## Output Format

```markdown
## Project Analysis: {project-name}

### Context
- Type: {plugin|skill-library|agent-suite}
- Complexity: {simple|standard|advanced}
- Purpose: {description}

### Layer 1: Static Validation
**Status:** {pass|warn|fail}
- Errors: {count}
- Warnings: {count}
- W0XX codes: {list}

### Layer 2: Semantic Analysis

#### Content Quality
{From content-quality-analyzer}

#### Hook Analysis
{From hook-reasoning-engine}

#### Intent Alignment
{From intent-analyzer}

#### Architectural Smells
{From architectural-smell-detector}

#### Extraction Candidates
{From extraction-recommender}

### Prioritized Actions

| Priority | Issue | Source | Action |
|----------|-------|--------|--------|
| BLOCKING | {issue} | {agent} | {fix} |
| ADVISORY | {issue} | {agent} | {fix} |

### Summary
{Executive summary with next steps}
```

## Key Difference from VALIDATE

| VALIDATE | ANALYZE |
|----------|---------|
| Static script only | Static + semantic agents |
| Schema checks | Design principles + intent |
| Pass/fail binary | Confidence scores with evidence |
| Pattern matching | Contextual understanding |
| Fixed questions | Adaptive to project type |
