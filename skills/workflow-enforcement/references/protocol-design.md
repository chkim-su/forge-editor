# Protocol Design: 6 Workflow Types

Detailed explanation of each workflow type, validation requirements, and rationale.

## Workflow Type Comparison

| Workflow | validate_all | form_audit | content_quality | func_test | plugin_test |
|----------|:------------:|:----------:|:---------------:|:---------:|:-----------:|
| skill_creation | Required | Required | Optional | Required | Optional |
| agent_creation | Required | Required | Optional | Optional | - |
| command_creation | Required | - | Optional | Optional | - |
| plugin_publish | Required | Required | **Required** | Required | Required |
| quick_fix | Required | - | - | - | - |
| analyze_only | Required | Optional | Optional | - | - |

## 1. skill_creation

**Purpose**: Creating new skills (markdown-based knowledge/guides)

**Why these validations?**
- `validate_all`: Schema correctness is fundamental
- `form_selection_audit`: Prevents creating agents when skills are appropriate
- `functional_test`: Ensures skill loads correctly
- `plugin_test`: Optional - skills are static content

**DAG**:
```
validate_all ──┬──> functional_test ──> plugin_test (opt)
               │
form_audit ────┘
```

## 2. agent_creation

**Purpose**: Creating new agents (autonomous subprocess workers)

**Why these validations?**
- `validate_all`: Schema and structure
- `form_selection_audit`: Prevents over-engineering with agents
- `functional_test`: Optional - agents work with definition alone
- No plugin_test: Agent isolation tested at publish time

**DAG**:
```
validate_all ──> functional_test (opt)
form_audit
```

## 3. command_creation

**Purpose**: Creating slash commands (simple prompt expansion)

**Why these validations?**
- `validate_all`: Basic structure
- No form_audit: Commands have clear purpose (user interface)
- `functional_test`: Optional - commands are simple text

**DAG**:
```
validate_all ──> functional_test (opt)
```

## 4. plugin_publish

**Purpose**: Publishing to marketplace

**Why ALL validations required?**
- External users affected - highest risk
- Rollback is difficult
- User trust depends on quality
- `content_quality_audit` is BLOCKING (W037/W038 exit 2)

**DAG**:
```
                    ┌─> functional_test ──> plugin_test
validate_all ───────┤
                    ├─> content_quality_audit (BLOCKING)
                    └─> marketplace_schema
        │
form_audit
```

## 5. quick_fix

**Purpose**: Simple error fixes (typos, schema errors)

**Why minimal validation?**
- Fast feedback loop critical
- Agent-based analysis is overhead
- Only structural correctness matters

**DAG**:
```
validate_all
```

## 6. analyze_only

**Purpose**: Read-only analysis without modification

**Why optional validations?**
- No code changes = no risk
- Analysis depth varies
- Information gathering, not enforcement

**DAG**:
```
validate_all ──> form_audit (opt)
               │
               └─> content_quality_audit (opt)
```

## Content Quality in Publish Mode

When `--publish-mode` is used:
- W037 (Korean text) becomes BLOCKING
- W038 (emoji usage) becomes BLOCKING
- Exit code changes from 0 to 2

This ensures marketplace deployments have clean, professional content.

## Anti-Bypass Security

Protected validations require agent execution:
- `form_selection_audit`: Requires form-selection-auditor agent
- `functional_test`: Requires functional-test agent
- `plugin_test`: Requires plugin-tester agent

Manual `mark-validation passed` attempts are:
1. Recorded as "claimed" (not "passed")
2. Rejected with exit code 1
3. Logged in workflow history

Only `--from-hook` flag (set by PostToolUse hooks after agent completion) allows state updates for protected validations.
