# Example: Hybrid Skill with Scripts and Assets

This example shows a **Hybrid Skill** that combines guidance with helper scripts and templates.

## Structure

```
api-generator/
├── SKILL.md
├── scripts/
│   └── scaffold.py
├── references/
│   └── patterns.md
└── assets/
    └── templates/
        ├── express-route.js
        └── fastapi-route.py
```

## SKILL.md

```yaml
---
name: api-generator
description: |
  Generate REST API endpoints with proper patterns.
  Supports: Express.js, FastAPI. Scaffolds routes with validation and error handling.
  Trigger phrases: "create API endpoint", "generate route", "scaffold API", "REST endpoint"
allowed-tools: ["Read", "Write", "Bash", "Grep", "Glob"]
---

# API Generator

Generate well-structured REST API endpoints with proper error handling and validation.

## Quick Start

**For scaffolding** (boilerplate):
```bash
python scripts/scaffold.py users --framework express --path src/routes
```

**For custom endpoints**: Follow patterns in references/patterns.md

## Workflow

1. **Determine framework**: Express.js or FastAPI
2. **Scaffold if boilerplate needed**: Use `scripts/scaffold.py`
3. **Customize**: Add business logic following patterns

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scaffold.py` | Generate route boilerplate | `python scripts/scaffold.py <resource> --framework <express\|fastapi>` |

## When to Use Scripts vs Generate Code

**Use scaffold.py when**:
- Creating new resource endpoints (CRUD)
- Need consistent boilerplate structure
- Starting a new API module

**Generate code manually when**:
- Custom endpoint logic
- Non-CRUD operations
- Complex business rules

## Framework Selection

### Express.js
- JavaScript/TypeScript backend
- Middleware-based architecture
- Template: `assets/templates/express-route.js`

### FastAPI
- Python backend
- Pydantic validation
- Template: `assets/templates/fastapi-route.py`

## Key Patterns

### Error Handling
Always wrap handlers in try-catch with proper HTTP status codes:
- 400: Bad request (validation error)
- 401: Unauthorized
- 404: Not found
- 500: Server error

### Validation
Validate input at the route level before business logic.

### Response Format
Consistent JSON structure:
```json
{
  "data": {...},
  "meta": {"timestamp": "..."}
}
```

---

For detailed patterns: [references/patterns.md](references/patterns.md)
```

## scripts/scaffold.py

```python
#!/usr/bin/env python3
"""
Scaffold REST API route boilerplate.

Usage:
    python scaffold.py <resource> --framework <express|fastapi> [--path <output-dir>]

Examples:
    python scaffold.py users --framework express --path src/routes
    python scaffold.py products --framework fastapi --path app/routes
"""

import argparse
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parent.parent

EXPRESS_TEMPLATE = '''const express = require('express');
const router = express.Router();

// GET /{resource}
router.get('/', async (req, res) => {
  try {
    // TODO: Implement list {resource}
    res.json({ data: [], meta: { timestamp: new Date().toISOString() } });
  } catch (error) {
    console.error('Error listing {resource}:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /{resource}/:id
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    // TODO: Implement get {resource} by id
    res.json({ data: { id }, meta: { timestamp: new Date().toISOString() } });
  } catch (error) {
    console.error('Error getting {resource}:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /{resource}
router.post('/', async (req, res) => {
  try {
    const data = req.body;
    // TODO: Validate and create {resource}
    res.status(201).json({ data, meta: { timestamp: new Date().toISOString() } });
  } catch (error) {
    console.error('Error creating {resource}:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /{resource}/:id
router.put('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const data = req.body;
    // TODO: Validate and update {resource}
    res.json({ data: { id, ...data }, meta: { timestamp: new Date().toISOString() } });
  } catch (error) {
    console.error('Error updating {resource}:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /{resource}/:id
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    // TODO: Implement delete {resource}
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting {resource}:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
'''

FASTAPI_TEMPLATE = '''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/{resource}", tags=["{Resource}"])


class {Resource}Base(BaseModel):
    # TODO: Define {resource} fields
    name: str


class {Resource}Create({Resource}Base):
    pass


class {Resource}Response({Resource}Base):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Meta(BaseModel):
    timestamp: datetime = datetime.utcnow()


class {Resource}ListResponse(BaseModel):
    data: List[{Resource}Response]
    meta: Meta


class {Resource}SingleResponse(BaseModel):
    data: {Resource}Response
    meta: Meta


@router.get("/", response_model={Resource}ListResponse)
async def list_{resource}():
    """List all {resource}."""
    # TODO: Implement list logic
    return {Resource}ListResponse(data=[], meta=Meta())


@router.get("/{{id}}", response_model={Resource}SingleResponse)
async def get_{resource}(id: int):
    """Get {resource} by ID."""
    # TODO: Implement get logic
    raise HTTPException(status_code=404, detail="{Resource} not found")


@router.post("/", response_model={Resource}SingleResponse, status_code=201)
async def create_{resource}(data: {Resource}Create):
    """Create new {resource}."""
    # TODO: Implement create logic
    return {Resource}SingleResponse(
        data={Resource}Response(id=1, created_at=datetime.utcnow(), **data.dict()),
        meta=Meta()
    )


@router.put("/{{id}}", response_model={Resource}SingleResponse)
async def update_{resource}(id: int, data: {Resource}Create):
    """Update {resource} by ID."""
    # TODO: Implement update logic
    return {Resource}SingleResponse(
        data={Resource}Response(id=id, created_at=datetime.utcnow(), **data.dict()),
        meta=Meta()
    )


@router.delete("/{{id}}", status_code=204)
async def delete_{resource}(id: int):
    """Delete {resource} by ID."""
    # TODO: Implement delete logic
    pass
'''


def scaffold(resource: str, framework: str, output_path: Path) -> None:
    """Generate route scaffold."""
    resource_lower = resource.lower()
    resource_title = resource.title()

    if framework == "express":
        template = EXPRESS_TEMPLATE.replace("{resource}", resource_lower)
        filename = f"{resource_lower}.routes.js"
    else:  # fastapi
        template = FASTAPI_TEMPLATE.replace("{resource}", resource_lower).replace("{Resource}", resource_title)
        filename = f"{resource_lower}.py"

    output_file = output_path / filename
    output_path.mkdir(parents=True, exist_ok=True)
    output_file.write_text(template)

    print(f"✅ Created: {output_file}")
    print(f"\nNext steps:")
    print(f"  1. Implement TODO comments in {output_file}")
    print(f"  2. Register route in your app")
    if framework == "express":
        print(f"     app.use('/{resource_lower}', require('./{filename}'));")
    else:
        print(f"     app.include_router({resource_lower}.router)")


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold REST API route boilerplate"
    )
    parser.add_argument("resource", help="Resource name (e.g., users, products)")
    parser.add_argument(
        "--framework",
        choices=["express", "fastapi"],
        required=True,
        help="Target framework"
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Output directory (default: current)"
    )
    args = parser.parse_args()

    scaffold(args.resource, args.framework, Path(args.path))


if __name__ == "__main__":
    main()
```

## references/patterns.md

```markdown
# API Design Patterns

## Error Handling Pattern

### Express.js

```javascript
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

// Usage
router.get('/', asyncHandler(async (req, res) => {
  const data = await fetchData();
  res.json({ data });
}));

// Error middleware
app.use((err, req, res, next) => {
  console.error(err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal server error'
  });
});
```

### FastAPI

```python
from fastapi import HTTPException

@router.get("/{id}")
async def get_item(id: int):
    item = await fetch_item(id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"data": item}
```

## Validation Pattern

### Express.js with Joi

```javascript
const Joi = require('joi');

const userSchema = Joi.object({
  email: Joi.string().email().required(),
  name: Joi.string().min(2).max(100).required(),
});

router.post('/', async (req, res) => {
  const { error, value } = userSchema.validate(req.body);
  if (error) {
    return res.status(400).json({ error: error.details[0].message });
  }
  // Use validated `value`
});
```

### FastAPI with Pydantic

```python
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    name: str

    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v):
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v
```

## Pagination Pattern

### Request

```
GET /users?page=1&limit=20
```

### Response

```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5
  }
}
```
```

## Key Characteristics of Hybrid Skills

1. **Mix of guidance and automation** - Patterns + scripts
2. **Scripts for boilerplate** - Scaffolding, code generation
3. **References for patterns** - Design decisions, best practices
4. **Assets for templates** - Starting points, boilerplate files
5. **SKILL.md guides when to use what** - Scripts vs manual coding

## When to Create a Hybrid Skill

- Preferred patterns exist, but some flexibility needed
- Boilerplate generation + customization
- Multiple valid approaches with guidance
- Framework-agnostic patterns with framework-specific scripts
