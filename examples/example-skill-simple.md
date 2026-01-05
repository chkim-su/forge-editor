---
name: sql-optimizer
description: Optimize SQL queries for performance. Trigger phrases: "optimize sql", "improve query performance", "sql performance", "slow query"
allowed-tools: ["Read", "Grep", "Glob"]
---

# SQL Optimizer

Analyzes and optimizes SQL queries for better performance.

## When to Use

- When SQL queries are slow
- To identify query bottlenecks
- Before deploying database changes to production
- When reviewing code with database operations

## Core Instructions

1. **Analyze query structure**: Check for missing indexes, N+1 queries, unnecessary JOINs
2. **Identify bottlenecks**: Find expensive operations like table scans, subqueries
3. **Suggest optimizations**: Provide concrete improvements with explanations

## Quick Examples

### Example 1: Missing Index
**User**: "This SELECT * FROM users WHERE email = 'x' is slow"
**Assistant**: Add index on email column: `CREATE INDEX idx_users_email ON users(email);`

### Example 2: N+1 Query
**User**: "Why is this loop slow?"
**Assistant**: Replace loop with JOIN to avoid N+1 queries

## Key Principles

- Always explain why each optimization helps
- Provide before/after performance comparisons
- Consider database-specific features (PostgreSQL, MySQL, etc.)
- Test optimizations before deploying
