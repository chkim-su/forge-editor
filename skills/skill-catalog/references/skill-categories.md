# Skill Categories Reference

Comprehensive categorization system for organizing skills.

## Primary Categories

### 🎨 Design & Frontend
Skills for UI/UX design, frontend development, and visual work.

**Examples**:
- `frontend-design` - Component design, styling, layouts
- `ui-patterns` - Common UI component patterns
- `css-optimizer` - CSS performance and best practices
- `accessibility-checker` - A11y compliance and WCAG standards
- `responsive-design` - Mobile-first and responsive patterns

**Trigger Phrases**:
- "design a component"
- "create UI for..."
- "style this page"
- "make it responsive"

### 📦 Code Generation
Skills that generate code, boilerplate, or templates.

**Examples**:
- `api-generator` - REST/GraphQL API scaffolding
- `test-generator` - Unit/integration test creation
- `component-generator` - React/Vue/Angular components
- `config-generator` - Configuration file templates
- `schema-generator` - Database schema/ORM models

**Trigger Phrases**:
- "generate API endpoint"
- "create tests for..."
- "scaffold component"
- "generate configuration"

### 📊 Data & Analysis
Skills for data processing, analysis, and optimization.

**Examples**:
- `sql-optimizer` - Query optimization and indexing
- `data-validator` - Schema validation and data quality
- `query-analyzer` - Performance analysis
- `etl-patterns` - Extract, transform, load workflows
- `data-migration` - Data transformation and migration

**Trigger Phrases**:
- "optimize this query"
- "validate data schema"
- "analyze query performance"
- "migrate data from..."

### 🔧 DevOps & Infrastructure
Skills for deployment, infrastructure, and operations.

**Examples**:
- `deployment-patterns` - CI/CD workflows
- `docker-orchestrator` - Container management
- `kubernetes-helper` - K8s configuration and deployment
- `infrastructure-as-code` - Terraform/CloudFormation
- `monitoring-setup` - Observability and alerting

**Trigger Phrases**:
- "deploy to production"
- "configure docker"
- "set up kubernetes"
- "create terraform config"

### 🔒 Security & Auth
Skills for authentication, authorization, and security.

**Examples**:
- `auth-patterns` - JWT, OAuth, session management
- `security-auditor` - Vulnerability scanning
- `encryption-helper` - Encryption/hashing best practices
- `permission-manager` - RBAC and permission systems
- `security-headers` - HTTP security headers

**Trigger Phrases**:
- "add authentication"
- "audit security"
- "implement permissions"
- "secure this endpoint"

### 🧪 Testing & Quality
Skills for testing, quality assurance, and validation.

**Examples**:
- `test-strategy` - Test planning and coverage
- `e2e-tester` - End-to-end test patterns
- `mock-generator` - Test data and mocking
- `performance-tester` - Load testing and benchmarks
- `code-reviewer` - Code quality analysis

**Trigger Phrases**:
- "write tests for..."
- "create e2e test"
- "generate mock data"
- "review code quality"

### 📚 Documentation
Skills for documentation generation and maintenance.

**Examples**:
- `api-doc-generator` - OpenAPI/Swagger docs
- `readme-generator` - Project documentation
- `inline-doc-helper` - JSDoc/docstrings
- `changelog-manager` - Release notes and changelogs
- `tutorial-creator` - User guides and tutorials

**Trigger Phrases**:
- "document this API"
- "create README"
- "add docstrings"
- "write tutorial for..."

### 🗄️ Database & Persistence
Skills for database design, migrations, and queries.

**Examples**:
- `migration-patterns` - Schema migrations
- `orm-helper` - Prisma/TypeORM/Sequelize patterns
- `database-optimizer` - Index and query optimization
- `schema-designer` - Database schema design
- `transaction-patterns` - ACID and consistency patterns

**Trigger Phrases**:
- "create migration"
- "design database schema"
- "optimize database"
- "implement transactions"

### 🌐 API & Integration
Skills for API design and third-party integrations.

**Examples**:
- `rest-api-patterns` - RESTful design
- `graphql-builder` - GraphQL schemas and resolvers
- `webhook-handler` - Webhook patterns
- `api-client-generator` - SDK/client generation
- `integration-patterns` - Third-party API integration

**Trigger Phrases**:
- "design REST API"
- "create GraphQL schema"
- "handle webhooks"
- "integrate with [service]"

### 🎯 Business Logic
Skills for domain-specific business logic.

**Examples**:
- `payment-processing` - Payment gateway patterns
- `notification-system` - Email/SMS/push notifications
- `scheduling-patterns` - Cron jobs and task scheduling
- `workflow-engine` - State machines and workflows
- `analytics-tracking` - Event tracking and analytics

**Trigger Phrases**:
- "process payments"
- "send notifications"
- "schedule tasks"
- "implement workflow"

## Secondary Attributes

### By Language/Framework
- **JavaScript/TypeScript**: Node.js, React, Vue, Angular
- **Python**: Django, Flask, FastAPI
- **Go**: Gin, Echo, fiber
- **Rust**: Actix, Rocket
- **Java**: Spring Boot

### By Complexity Level
- **Beginner**: Simple, well-documented patterns
- **Intermediate**: Multi-step workflows
- **Advanced**: Complex orchestration and optimization

### By Tool Requirements
- **Read-only**: Grep, Glob, Read
- **Write**: Write, Edit
- **Automation**: Bash, Task

## Categorization Best Practices

### Multiple Categories
Skills can belong to multiple categories:

```yaml
skill: api-generator
primary_category: Code Generation
secondary_categories:
  - API & Integration
  - Backend Development
```

### Category Hierarchies

```
📦 Code Generation
├── 🎨 Frontend Generators
│   ├── Component generators
│   └── Style generators
├── 🔙 Backend Generators
│   ├── API generators
│   └── Model generators
└── 🧪 Test Generators
    ├── Unit test generators
    └── Integration test generators
```

### Category Tags

```yaml
tags:
  - category: code-generation
  - language: typescript
  - framework: react
  - complexity: intermediate
```

## Skill Discovery Patterns

### By Use Case
"I need to..." → Recommended category

- "...build a UI" → Design & Frontend
- "...create an API" → API & Integration + Code Generation
- "...deploy my app" → DevOps & Infrastructure
- "...add auth" → Security & Auth
- "...optimize queries" → Data & Analysis

### By Problem Type
"I'm having issues with..." → Recommended category

- "...slow queries" → Data & Analysis
- "...failing tests" → Testing & Quality
- "...deployment errors" → DevOps & Infrastructure
- "...security vulnerabilities" → Security & Auth

## Catalog Organization

### Alphabetical Listing
```
📊 Data & Analysis:
- data-migration
- data-validator
- etl-patterns
- query-analyzer
- sql-optimizer
```

### Usage-Based Listing
```
📊 Data & Analysis (by popularity):
- sql-optimizer ⭐⭐⭐⭐⭐
- query-analyzer ⭐⭐⭐⭐
- data-validator ⭐⭐⭐
- data-migration ⭐⭐
- etl-patterns ⭐
```

### Recency-Based Listing
```
📊 Data & Analysis (recently updated):
- sql-optimizer (updated 2 days ago)
- query-analyzer (updated 1 week ago)
- data-validator (updated 2 weeks ago)
```

This categorization system helps users quickly discover relevant skills.
