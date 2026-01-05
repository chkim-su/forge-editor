# Skill Structure Types

Skills follow one of four structural patterns based on their purpose. Choose the right structure to optimize readability and context efficiency.

## 1. Workflow-Based (단계 기반)

**Purpose:** Sequential multi-step tasks with clear progression

**Structure:**
```markdown
## Step 1: [Action]
Instructions for first step

## Step 2: [Action]
Instructions for second step
→ If condition: Go to Step 3a
→ Otherwise: Go to Step 3b

## Step 3a: [Branch A]
...

## Step 3b: [Branch B]
...
```

**Characteristics:**
- Numbered steps with clear transitions
- Conditional branching with explicit jumps
- State tracking between steps
- Often delegates to scripts/subagents per step

**Examples:**
- deploy-checker (validate → analyze → report)
- skill-creator (design → implement → validate)
- feature-dev (plan → code → test → review)

**When to Use:**
- Multi-phase operations
- Tasks with decision points
- Operations requiring rollback capability


## 2. Task-Based (작업 기반)

**Purpose:** Single-purpose processing with clear input/output

**Structure:**
```markdown
## Input
- Required: [parameter1], [parameter2]
- Optional: [parameter3]

## Process
1. Validate input
2. Execute transformation
3. Generate output

## Output
- Format: [output format]
- Location: [where output goes]

## Scripts
| Script | Purpose |
|--------|---------|
| process.py | Main processing |
```

**Characteristics:**
- Clear input → output transformation
- Single responsibility
- Minimal branching
- Script-heavy implementation

**Examples:**
- pdf-processor (PDF → text/images)
- xlsx-converter (data → spreadsheet)
- image-optimizer (images → optimized images)

**When to Use:**
- File transformations
- Data processing
- Single-operation tools


## 3. Reference/Guidelines (참조 기반)

**Purpose:** Provide rules, standards, or best practices

**Structure:**
```markdown
## Overview
Brief description of what these guidelines cover

## Core Rules
### Rule 1: [Name]
- Do: [correct approach]
- Don't: [incorrect approach]

### Rule 2: [Name]
...

## Examples
### Good Example
[code/content]

### Bad Example
[code/content]

## Quick Reference
| Scenario | Recommendation |
|----------|---------------|
| A | Do X |
| B | Do Y |
```

**Characteristics:**
- No sequential flow
- Rule-based organization
- Heavy use of examples
- Reference tables for quick lookup

**Examples:**
- brand-guidelines (colors, fonts, spacing)
- code-style (formatting rules)
- security-checklist (requirements)

**When to Use:**
- Style guides
- Quality standards
- Compliance requirements
- Best practices documentation


## 4. Capabilities-Based (기능 기반)

**Purpose:** Provide a toolkit of related functions/features

**Structure:**
```markdown
## Available Capabilities
| Capability | Description | Script/Tool |
|-----------|-------------|-------------|
| Feature A | Does X | script_a.py |
| Feature B | Does Y | script_b.py |

## Feature A
### Usage
```bash
python script_a.py [args]
```

### Options
- `--option1`: Description
- `--option2`: Description

## Feature B
...

## Combining Features
### Common Workflows
1. A → B → C
2. A → D
```

**Characteristics:**
- Menu of independent features
- Each feature documented separately
- Combination patterns
- Tool/script inventory

**Examples:**
- webapp-testing (screenshot, interact, validate)
- mcp-builder (create, configure, deploy)
- git-toolkit (commit, branch, merge helpers)

**When to Use:**
- Toolkits with multiple features
- Libraries with many functions
- Feature-rich integrations


## Choosing the Right Type

```
Is there a sequential flow?
├── Yes → Are there decision points?
│   ├── Yes → Workflow-Based
│   └── No → Task-Based
└── No → Is it providing rules/standards?
    ├── Yes → Reference/Guidelines
    └── No → Capabilities-Based
```

## Hybrid Approaches

Some skills combine types:

**Workflow + Capabilities:**
```markdown
## Step 1: Choose Operation
Select from available capabilities:
- [Capability A]
- [Capability B]

## Step 2: Execute
[Capability-specific instructions]

## Available Capabilities
[Detailed capability documentation]
```

**Reference + Task:**
```markdown
## Guidelines
[Rules to follow]

## Applying Guidelines
Input: [what to analyze]
Output: [compliance report]
Process: [how to check]
```
