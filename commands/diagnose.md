---
description: Comprehensive plugin diagnostics - static validation + semantic analysis
argument-hint: "[--quick|--deep] [path]"
allowed-tools: ["Read", "Write", "Bash", "Grep", "Glob", "Task"]
---

# /diagnose - Comprehensive Plugin Diagnostics

Two-layer diagnostic analysis: fast static validation + deep semantic understanding.

## Modes

| Mode | Flag | What It Does | Time |
|------|------|--------------|------|
| Quick | `--quick` | Static validation only | ~1s |
| Deep | `--deep` | Static + all semantic agents | ~30s+ |
| Default | (none) | Static + targeted semantic | ~10s |

## Usage

```bash
/diagnose                    # Default: static + targeted semantic
/diagnose --quick            # Fast: static validation only
/diagnose --deep             # Thorough: all semantic agents
/diagnose /path/to/plugin    # Analyze specific path
```

---

## Workflow

### Step 1: Run Static Validation

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json
```

Parse results:
- `status`: pass/warn/fail
- `errors`: structural issues
- `warnings`: W0XX codes found

### Step 2: Determine Analysis Depth

| Mode | Static Result | Semantic Analysis |
|------|--------------|-------------------|
| `--quick` | Any | Skip semantic |
| `--deep` | Any | Run all agents |
| Default | `pass` | Minimal (content-quality) |
| Default | `warn` | Targeted based on W0XX |
| Default | `fail` | Full analysis |

### Step 3: Dispatch Semantic Agents

Based on findings, use Task tool to launch agents:

| Finding | Agent | Purpose |
|---------|-------|---------|
| W028 | `hook-reasoning-engine` | Hook placement analysis |
| W030 | `intent-analyzer` | Tools field intentionality |
| W031/W032 | `content-quality-analyzer` | Documentation review |
| Multiple similar errors | `architectural-smell-detector` | Pattern detection |
| Complex structure | `extraction-recommender` | Simplification |
| Any docs exist | `content-quality-analyzer` | Language/emoji check |

For deep mode, launch all in parallel:

```yaml
Task (parallel):
  - subagent_type: content-quality-analyzer
    prompt: "Analyze all documentation files"
  - subagent_type: hook-reasoning-engine
    prompt: "Analyze enforcement patterns"
  - subagent_type: intent-analyzer
    prompt: "Apply 6 questions to all components"
  - subagent_type: architectural-smell-detector
    prompt: "Detect architectural smells"
  - subagent_type: extraction-recommender
    prompt: "Find extraction candidates"
```

### Step 4: Synthesize Report

Collect all findings and generate unified report:

```markdown
## Diagnostic Report

**Plugin:** {name}
**Path:** {path}
**Mode:** {quick|default|deep}
**Timestamp:** {datetime}

---

### Layer 1: Static Validation

**Status:** {pass|warn|fail}

| Type | Count | Details |
|------|-------|---------|
| Errors | {n} | {list if any} |
| Warnings | {n} | {list if any} |
| Passed | {n} | {checkmark} |

{If errors, show W0XX codes with skill references}

---

### Layer 2: Semantic Analysis

{Only if not --quick mode}

#### Content Quality
{From content-quality-analyzer}
- Language: {findings}
- Emoji: {findings}
- Comments: {findings}

#### Hook Analysis
{From hook-reasoning-engine}
- Enforcement patterns found: {count}
- Hooks recommended: {count}
- Implementation complexity: {summary}

#### Intent Alignment
{From intent-analyzer}
- Components analyzed: {count}
- Alignment issues: {count}
- Unused capabilities: {list}

#### Architectural Smells
{From architectural-smell-detector}
- Smells detected: {count}
- Pattern compliance: {status}
- Deviations: {list}

#### Extraction Candidates
{From extraction-recommender}
- Script candidates: {count}
- Agent candidates: {count}
- Skill candidates: {count}

---

### Prioritized Actions

| Priority | Issue | Source | Action |
|----------|-------|--------|--------|
| BLOCKING | {issue} | {agent} | {action} |
| ADVISORY | {issue} | {agent} | {action} |
| OBSERVATION | {issue} | {agent} | {action} |

---

### Summary

{Executive summary}

**Next Steps:**
1. {action 1}
2. {action 2}
3. {action 3}
```

---

## Example Outputs

### Quick Mode Output

```
📊 Diagnostic Report (Quick Mode)

Static Validation: ✅ PASS
- Errors: 0
- Warnings: 2
- Passed: 45

Warnings:
  W028: Enforcement keywords found, hooks.json exists ✓
  W036: Unnecessary files detected

💡 Run '/diagnose --deep' for semantic analysis
```

### Deep Mode Output

```
📊 Diagnostic Report (Deep Mode)

=== Layer 1: Static Validation ===
Status: ⚠️ WARN (2 warnings)

=== Layer 2: Semantic Analysis ===

Content Quality:
  ✓ Language: English consistent
  ✓ Emoji: Appropriate usage
  ⚠ Comments: 3 TODOs found

Hook Analysis:
  Found 5 enforcement patterns
  Recommended: 2 PreToolUse, 1 PostToolUse hooks

Intent Alignment:
  12/15 components aligned (80%)
  3 unused capabilities detected

Architectural Smells:
  1 Ghost Component detected
  Pattern compliance: 85%

Extraction Candidates:
  2 script candidates
  1 agent candidate

=== Prioritized Actions ===
1. [ADVISORY] Translate Korean text in hook-capabilities
2. [ADVISORY] Add hook for MUST keyword in wizard
3. [OBSERVATION] Consider extracting validation script

Total analysis time: 28s
```

---

## Success Criteria

- Static validation always runs first
- Mode determines semantic depth
- Agents dispatched in parallel when possible
- Findings synthesized with priorities
- Actionable recommendations generated
- Time reported for transparency
