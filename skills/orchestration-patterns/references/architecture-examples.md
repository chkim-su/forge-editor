# Orchestration Architecture Examples

Real-world examples of single-skill consumers vs multi-skill orchestrators.

## Single-Skill Consumer Examples

### Example 1: SQL Specialist

**Scenario**: Database query optimization

**Architecture**:
```yaml
---
name: sql-specialist
description: SQL query optimization and analysis
skills: sql-optimizer
tools: Read, Grep, Glob
model: sonnet
---

You are a SQL optimization specialist.

Use sql-optimizer skill for all database queries.
```

**Context Diagram**:
```
Main Conversation
     ↓
     /sql-specialist "Optimize SELECT * FROM users WHERE..."
     ↓
     Subagent Context (Isolated)
     └─> sql-optimizer skill loaded
         - Analyzes query
         - Suggests indexes
         - Rewrites query
         - Returns optimized version
     ↓
     Returns to Main: "Here's your optimized query..."
```

**Benefits**:
- ✅ Isolated context (query analysis doesn't pollute main)
- ✅ Specialized expertise (SQL only)
- ✅ Focused tool set (analysis tools only)
- ✅ Clear scope (optimization only)

### Example 2: Migration Manager

**Scenario**: Database migration creation

**Architecture**:
```yaml
---
name: migration-agent
description: Database migration creation and management
skills: migration-patterns
tools: Read, Write, Bash
model: sonnet
---

You manage database migrations using migration-patterns skill.

Always:
1. Check existing migrations
2. Create timestamped migration files
3. Include up and down migrations
4. Test migration locally
```

**Usage**:
```
User: /migration-agent Add user_preferences table

Agent (in isolated context):
1. Reads existing schema
2. Uses migration-patterns skill
3. Creates migration file
4. Returns: "Created migration 20231209_add_user_preferences.sql"
```

### Example 3: Deployment Specialist

**Scenario**: Application deployment

**Architecture**:
```yaml
---
name: deployment-agent
description: Application deployment automation
skills: deployment-patterns
tools: Read, Bash, Write
model: sonnet
---

You handle deployments using deployment-patterns skill.

Workflow:
1. Validate environment
2. Run pre-deployment checks
3. Execute deployment
4. Verify success
5. Rollback on failure
```

**Context Isolation Benefit**:
```
Main Conversation:
User: "Deploy to production"
      ↓
      /deployment-agent
      ↓
Subagent runs entire deployment workflow in isolation
      ↓
Returns: "✅ Deployed v1.2.3 to production"

[All deployment logs, checks, etc. stay in subagent context]
```

## Multi-Skill Orchestrator Examples

### Example 1: Full-Stack Feature Agent

**Scenario**: Complete feature development across frontend, backend, and database

**Architecture**:
```yaml
---
name: fullstack-orchestrator
description: Full-stack feature development
skills: frontend-design, api-generator, migration-patterns
tools: Read, Write, Edit, Bash, Task
model: sonnet
---

You orchestrate full-stack features across multiple domains.

## Skill Selection:

| Task Type | Skill to Use |
|-----------|--------------|
| UI/Components | frontend-design |
| API Endpoints | api-generator |
| Database Changes | migration-patterns |

## Workflow:
1. Analyze feature requirements
2. Plan across all layers
3. Coordinate skill usage
4. Ensure integration
```

**Example Interaction**:
```
User: /fullstack-orchestrator Add user profile with avatar upload

Agent orchestrates:

1. Frontend (uses frontend-design skill):
   - Creates ProfilePage component
   - Adds AvatarUpload component
   - Implements image preview

2. Backend (uses api-generator skill):
   - Creates POST /api/profile/avatar endpoint
   - Adds file upload middleware
   - Implements image validation

3. Database (uses migration-patterns skill):
   - Adds avatar_url column to users table
   - Creates migration file

Returns: "✅ Complete profile feature implemented across all layers"
```

**Context Diagram**:
```
Main Conversation
     ↓
     /fullstack-orchestrator "Add user profile..."
     ↓
     Subagent Context (Isolated)
     ├─> frontend-design skill
     │   └─> Component creation
     ├─> api-generator skill
     │   └─> API endpoint creation
     └─> migration-patterns skill
         └─> Database migration
     ↓
     Returns integrated solution
```

### Example 2: Data Pipeline Orchestrator

**Scenario**: ETL workflow with data validation, transformation, and loading

**Architecture**:
```yaml
---
name: data-pipeline-orchestrator
description: ETL pipeline management
skills: data-validator, etl-patterns, sql-optimizer
tools: Read, Write, Bash, Task
model: sonnet
---

You orchestrate data pipelines.

## Pipeline Stages:

1. **Extract** (etl-patterns):
   - Source data extraction
   - Format detection

2. **Validate** (data-validator):
   - Schema validation
   - Data quality checks

3. **Transform** (etl-patterns):
   - Data transformation
   - Business logic

4. **Load** (sql-optimizer):
   - Optimized bulk inserts
   - Index management
```

**Example Flow**:
```
User: /data-pipeline-orchestrator Import CSV to database

Agent coordinates:

Phase 1 - Extract (etl-patterns):
├─> Reads CSV file
├─> Detects schema
└─> Identifies 10,000 rows

Phase 2 - Validate (data-validator):
├─> Validates against schema
├─> Finds 3 invalid rows
└─> Reports issues

Phase 3 - Transform (etl-patterns):
├─> Normalizes data
├─> Applies business rules
└─> Prepares for load

Phase 4 - Load (sql-optimizer):
├─> Creates optimal batch inserts
├─> Adds indexes
└─> Verifies data integrity

Returns: "✅ Loaded 9,997 rows successfully (3 invalid rows logged)"
```

### Example 3: DevOps Workflow Agent

**Scenario**: Complete deployment pipeline from build to production

**Architecture**:
```yaml
---
name: devops-orchestrator
description: Complete CI/CD workflow orchestration
skills: docker-patterns, deployment-patterns, monitoring-setup
tools: Read, Write, Bash, Task
model: sonnet
---

You orchestrate DevOps workflows.

## Deployment Workflow:

1. **Containerization** (docker-patterns):
   - Dockerfile optimization
   - Multi-stage builds

2. **Deployment** (deployment-patterns):
   - Environment validation
   - Blue-green deployment

3. **Monitoring** (monitoring-setup):
   - Health checks
   - Alerting configuration
```

**Complete Workflow Example**:
```
User: /devops-orchestrator Deploy new version

Agent orchestrates:

Stage 1 - Containerization (docker-patterns):
✓ Optimized Dockerfile
✓ Built image: app:v1.2.3
✓ Pushed to registry

Stage 2 - Deployment (deployment-patterns):
✓ Validated staging environment
✓ Deployed to staging
✓ Ran smoke tests
✓ Deployed to production (blue-green)
✓ Switched traffic

Stage 3 - Monitoring (monitoring-setup):
✓ Configured health checks
✓ Set up error tracking
✓ Enabled performance monitoring

Returns: "✅ v1.2.3 deployed successfully with full monitoring"
```

## Decision Matrix: Single vs Multi

| Scenario | Architecture | Reasoning |
|----------|--------------|-----------|
| SQL optimization only | Single-Skill | Focused domain, one expertise |
| Database migrations only | Single-Skill | Specialized task |
| Authentication implementation | Single-Skill | One security domain |
| Full-stack feature | Multi-Skill | Frontend + Backend + DB |
| Data pipeline | Multi-Skill | Extract + Validate + Transform + Load |
| Complete deployment | Multi-Skill | Build + Deploy + Monitor |
| API endpoint creation only | Single-Skill | One task |
| Microservice creation | Multi-Skill | API + Docker + Deploy |

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Over-Orchestration

**Bad**:
```yaml
name: tiny-orchestrator
skills: css-helper, html-formatter
```

**Problem**: Two highly related skills don't need orchestration

**Better**: Combine into single `frontend-helper` skill

### ❌ Anti-Pattern 2: Under-Specialization

**Bad**:
```yaml
name: generic-helper
skills: frontend, backend, database, devops, security, testing
```

**Problem**: Too many unrelated skills, no clear purpose

**Better**: Create focused orchestrators per workflow

### ❌ Anti-Pattern 3: Skill Redundancy

**Bad**:
```yaml
name: api-orchestrator
skills: api-generator, rest-patterns, graphql-builder
```

**Problem**: All three skills do similar things

**Better**: Consolidate into comprehensive `api-generator` skill

## Best Practices

### 1. Clear Skill Boundaries

Each skill in orchestrator should have **distinct responsibility**:

```yaml
skills: frontend-design, api-generator, migration-patterns
```

- ✅ frontend-design: UI/UX only
- ✅ api-generator: Backend API only
- ✅ migration-patterns: Database schema only

No overlap.

### 2. Logical Workflow Grouping

Orchestrate skills that **work together** in workflows:

```yaml
# Good: Complete feature workflow
skills: component-generator, api-generator, test-generator

# Bad: Unrelated skills
skills: css-optimizer, docker-builder, email-sender
```

### 3. Appropriate Tool Sets

**Single-Skill Consumer**:
```yaml
tools: Read, Grep, Glob  # Minimal, focused
```

**Multi-Skill Orchestrator**:
```yaml
tools: Read, Write, Edit, Bash, Task  # Comprehensive
```

### 4. Clear Skill Selection Logic

Document WHEN to use each skill:

```markdown
## Skill Selection

| Request Contains | Use Skill |
|------------------|-----------|
| "component", "UI" | frontend-design |
| "endpoint", "API" | api-generator |
| "table", "column" | migration-patterns |
```

## Performance Considerations

### Context Window Usage

**Single-Skill**:
```
Main context: Clean
Subagent context: ~1,000 words (one skill)
Total overhead: Minimal
```

**Multi-Skill**:
```
Main context: Clean
Subagent context: ~3,000 words (three skills)
Total overhead: Moderate but acceptable
```

**Rule of Thumb**: Keep orchestrators to 3-5 skills maximum.

These examples demonstrate when to use each architecture pattern effectively.
