# Enhanced Agent Template

## Overview

Enhanced agents combine:
1. **Serena Gateway** - Fast codebase exploration for smart skill discovery
2. **skill-rules.json** - Pattern matching to auto-select relevant skills
3. **claude-mem** - Cross-session memory persistence

---

## Agent Template

```yaml
---
name: {domain}-smart-agent
description: Enhanced agent with codebase exploration and memory persistence
tools: ["Read", "Write", "Bash", "Task", "Skill", "Grep", "Glob"]
skills: {base-skills}
model: sonnet
color: purple
---
```

```markdown
# {Domain} Smart Agent

## Initialization Protocol

On session start:
1. Load recent context from claude-mem
2. Activate Serena project if needed

## Request Handling Protocol

For each user request:

### Phase 1: Context Loading
```
claude-mem search:
  query: {relevant keywords from request}
  project: {project-name}
  limit: 5
```

### Phase 2: Codebase Exploration (via Serena Gateway)
```json
{
  "intent": "QUERY",
  "action": "search_for_pattern",
  "params": { "pattern": "{keywords from request}" }
}
```

Or for symbol-based exploration:
```json
{
  "intent": "QUERY",
  "action": "get_symbols_overview",
  "params": { "relative_path": "src/", "depth": 2 }
}
```

### Phase 3: Skill Discovery
Based on exploration results, match against skill-rules.json:
- File patterns found → pathPatterns match
- Code patterns found → contentPatterns match
- Domain keywords found → keywords match

### Phase 4: Skill Invocation
Auto-call matched skills using Skill tool before executing task.

### Phase 5: Execute Task
With skills loaded, execute the user's request.

### Phase 6: Memory Storage
Store observation to claude-mem:
```
claude-mem observation:
  type: decision|discovery|change
  title: {what was done}
  content: {details and rationale}
```
```

---

## Serena Gateway Integration

### Exploration Queries

**Symbol Search:**
```json
{
  "intent": "QUERY",
  "action": "find_symbol",
  "effect": "READ_ONLY",
  "artifact": "JSON",
  "params": {
    "name_path_pattern": "{keyword}",
    "depth": 1,
    "include_body": false
  }
}
```

**Pattern Search:**
```json
{
  "intent": "QUERY",
  "action": "search_for_pattern",
  "effect": "READ_ONLY",
  "artifact": "JSON",
  "params": {
    "substring_pattern": "{regex pattern}",
    "restrict_search_to_code_files": true
  }
}
```

**Structure Overview:**
```json
{
  "intent": "ANALYZE",
  "action": "get_symbols_overview",
  "effect": "READ_ONLY",
  "artifact": "JSON",
  "params": {
    "relative_path": "src/",
    "depth": 2
  }
}
```

### Calling Serena Gateway

Use Task tool to invoke serena-gateway:
```
Task(
  subagent_type: "serena-refactor:serena-gateway",
  prompt: {JSON request}
)
```

---

## claude-mem Integration

### Session Start: Load Context

```typescript
// Search for recent work on this project
const recentContext = await mcp.search({
  query: "",  // empty for recent
  project: "my-project",
  limit: 10,
  type: "observations"
});

// Get timeline around most relevant observation
if (recentContext.length > 0) {
  const timeline = await mcp.timeline({
    anchor: recentContext[0].id,
    depth_before: 3,
    depth_after: 0,
    project: "my-project"
  });
}
```

### Task Completion: Store Observation

claude-mem automatically captures observations, but agents can explicitly note:
- **Decisions**: Why a particular approach was chosen
- **Discoveries**: What was learned about the codebase
- **Changes**: What was modified and why

---

## Skill Discovery Flow

```
User: "Add authentication to the API"
         ↓
[1] Serena QUERY: search_for_pattern "auth|login|session"
         ↓
[2] Results: found auth middleware, JWT utils, user service
         ↓
[3] Match skill-rules.json:
    - "auth" keyword → security-patterns skill
    - "middleware" keyword → backend-patterns skill
    - "JWT" content pattern → auth-patterns skill
         ↓
[4] Auto-call: Skill("security-patterns"), Skill("backend-patterns")
         ↓
[5] Execute with loaded skills
         ↓
[6] claude-mem: store decision observation
```

---

## Example: Fullstack Smart Agent

```yaml
---
name: fullstack-smart-agent
description: Enhanced fullstack development with codebase awareness
tools: ["Read", "Write", "Bash", "Task", "Skill", "Grep", "Glob"]
skills: skill-catalog
model: sonnet
color: purple
---
```

```markdown
# Fullstack Smart Agent

## Capabilities
- Codebase exploration via Serena Gateway
- Auto-discovery of relevant skills
- Cross-session memory via claude-mem

## On Session Start

1. Check claude-mem for recent context:
   - What was worked on last?
   - Any pending decisions?
   - Known blockers?

2. Activate Serena project:
   ```json
   {"intent": "QUERY", "action": "activate_project"}
   ```

## On User Request

1. **Explore**: Use Serena to understand relevant code
2. **Match**: Check findings against skill-rules.json
3. **Load**: Call matched skills via Skill tool
4. **Execute**: Complete the task with skills
5. **Store**: Record observation in claude-mem

## Skill Matching Rules

| Exploration Finding | Matched Skill |
|---------------------|---------------|
| React components | frontend-patterns |
| Express routes | backend-patterns |
| Prisma models | database-patterns |
| Test files | testing-patterns |
| Auth code | security-patterns |

## Memory Integration

Project name for claude-mem: `fullstack-project`

Store observations for:
- Architecture decisions
- Pattern discoveries
- Significant changes
```

---

## Fallback: Without Serena

If Serena is not available, fallback to Glob/Grep:

```
[1] Glob: find relevant files by pattern
    Glob("src/**/*.ts")

[2] Grep: search for keywords in files
    Grep("authentication", "src/")

[3] Read: examine matched files
    Read("src/auth/middleware.ts")

[4] Match skill-rules.json based on findings
```

Less precise than Serena symbol-level search, but functional.

---

## Configuration Checklist

- [ ] Serena MCP enabled (or fallback configured)
- [ ] serena-refactor plugin installed (for gateway)
- [ ] skill-rules.json created with project patterns
- [ ] claude-mem MCP enabled
- [ ] Project name defined for claude-mem
- [ ] Base skills defined in agent frontmatter
