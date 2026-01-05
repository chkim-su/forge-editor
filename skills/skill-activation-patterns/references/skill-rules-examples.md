# skill-rules.json Examples

## Minimal Example

```json
{
  "version": "1.0",
  "skills": {
    "my-skill": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "promptTriggers": {
        "keywords": ["my-keyword"]
      }
    }
  }
}
```

---

## Backend Development Skill

```json
{
  "backend-patterns": {
    "type": "domain",
    "enforcement": "suggest",
    "priority": "high",
    "description": "Backend development patterns for Node.js/Express",
    "promptTriggers": {
      "keywords": [
        "backend",
        "API",
        "endpoint",
        "controller",
        "service",
        "repository",
        "middleware",
        "route",
        "express"
      ],
      "intentPatterns": [
        "(create|add|implement).*?(route|endpoint|API|controller)",
        "(how to|best practice).*?(backend|service|API)"
      ]
    },
    "fileTriggers": {
      "pathPatterns": [
        "src/backend/**/*.ts",
        "api/**/*.ts",
        "server/**/*.ts"
      ],
      "pathExclusions": [
        "**/*.test.ts",
        "**/*.spec.ts"
      ],
      "contentPatterns": [
        "router\\.(get|post|put|delete)",
        "export.*Controller",
        "export.*Service"
      ]
    }
  }
}
```

---

## Frontend Guardrail (Block Enforcement)

```json
{
  "frontend-standards": {
    "type": "guardrail",
    "enforcement": "block",
    "priority": "critical",
    "description": "Enforce React/MUI best practices",
    "promptTriggers": {
      "keywords": [
        "component",
        "React",
        "MUI",
        "Material-UI",
        "Grid"
      ],
      "intentPatterns": [
        "(create|add|build).*?(component|UI|page)"
      ]
    },
    "fileTriggers": {
      "pathPatterns": ["src/**/*.tsx"],
      "contentPatterns": [
        "from '@mui/material'",
        "<Grid "
      ]
    },
    "blockMessage": "⚠️ BLOCKED - Frontend Standards Required\n\n1. Use Skill tool: 'frontend-standards'\n2. Review React best practices\n3. Check MUI patterns\n4. Retry edit\n\nReason: Prevent incompatible patterns",
    "skipConditions": {
      "sessionSkillUsed": true,
      "fileMarkers": ["@skip-validation"]
    }
  }
}
```

---

## MCP Gateway Skill

Integrating with skillmaker's mcp-gateway-patterns:

```json
{
  "mcp-gateway-patterns": {
    "type": "domain",
    "enforcement": "suggest",
    "priority": "high",
    "description": "MCP Gateway design patterns",
    "promptTriggers": {
      "keywords": [
        "MCP",
        "gateway",
        "MCP server",
        "subprocess isolation",
        "tool schema",
        "context token"
      ],
      "intentPatterns": [
        "(design|create|implement).*?(MCP|gateway)",
        "(reduce|optimize).*?(token|context)",
        "(isolate|separate).*?(MCP|session)"
      ]
    }
  }
}
```

---

## Testing Skill

```json
{
  "testing-patterns": {
    "type": "domain",
    "enforcement": "suggest",
    "priority": "medium",
    "description": "Testing best practices",
    "promptTriggers": {
      "keywords": [
        "test",
        "testing",
        "unit test",
        "integration test",
        "mock",
        "jest",
        "vitest"
      ],
      "intentPatterns": [
        "(write|add|create).*?test",
        "(how to|best practice).*?test"
      ]
    },
    "fileTriggers": {
      "pathPatterns": [
        "**/*.test.ts",
        "**/*.spec.ts",
        "**/__tests__/**"
      ]
    }
  }
}
```

---

## Multi-Skill Configuration

Complete example with multiple skills:

```json
{
  "version": "1.0",
  "description": "Project skill activation rules",
  "skills": {
    "backend-patterns": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "promptTriggers": {
        "keywords": ["backend", "API", "controller"]
      },
      "fileTriggers": {
        "pathPatterns": ["src/api/**/*.ts"]
      }
    },
    "frontend-standards": {
      "type": "guardrail",
      "enforcement": "block",
      "priority": "critical",
      "promptTriggers": {
        "keywords": ["component", "React"]
      },
      "fileTriggers": {
        "pathPatterns": ["src/components/**/*.tsx"]
      },
      "blockMessage": "Use frontend-standards skill first"
    },
    "testing-patterns": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "medium",
      "promptTriggers": {
        "keywords": ["test", "testing"]
      }
    },
    "security-guidelines": {
      "type": "guardrail",
      "enforcement": "warn",
      "priority": "high",
      "promptTriggers": {
        "keywords": ["auth", "password", "token", "secret"]
      }
    }
  },
  "notes": {
    "customization": "Adjust pathPatterns to match your project structure"
  }
}
```

---

## Trigger Pattern Tips

### Keywords: Be Specific
```json
// ❌ Too generic - will over-trigger
"keywords": ["code", "file", "function"]

// ✅ Domain-specific
"keywords": ["controller", "service", "repository", "middleware"]
```

### Intent Patterns: Capture Action + Object
```json
// Pattern structure: (action verbs).*?(target objects)
"intentPatterns": [
  "(create|add|implement|build).*?(route|endpoint|API)",
  "(fix|debug|handle).*?(error|exception)",
  "(how to|best practice).*?(backend|service)"
]
```

### Path Patterns: Use Globs
```json
// Match deep directories
"pathPatterns": ["src/**/api/**/*.ts"]

// Multiple patterns
"pathPatterns": [
  "backend/**/*.ts",
  "api/**/*.ts",
  "server/**/*.ts"
]
```

### Content Patterns: Escape Special Chars
```json
// Escape regex special characters
"contentPatterns": [
  "router\\.(get|post|put|delete)",  // Match router.get, router.post, etc.
  "export.*Controller",               // Match export class XxxController
  "import.*from '@mui"               // Match MUI imports
]
```
