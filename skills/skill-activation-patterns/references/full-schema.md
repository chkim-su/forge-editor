# Full skill-rules.json Schema

## Complete Schema

```json
{
  "version": "1.0",
  "skills": {
    "skill-name": {
      "type": "domain|guardrail",
      "enforcement": "suggest|warn|block",
      "priority": "critical|high|medium|low",
      "promptTriggers": {
        "keywords": ["keyword1", "keyword2"],
        "intentPatterns": ["regex pattern"]
      },
      "fileTriggers": {
        "pathPatterns": ["src/**/*.ts"],
        "pathExclusions": ["**/*.test.ts"],
        "contentPatterns": ["import.*Pattern"]
      },
      "blockMessage": "Custom message when blocked",
      "skipConditions": {
        "sessionSkillUsed": true,
        "fileMarkers": ["@skip-validation"]
      }
    }
  }
}
```

---

## Trigger Types

### 1. Keyword Triggers
Simple case-insensitive matching:
```json
"keywords": ["backend", "API", "controller", "service"]
```

### 2. Intent Pattern Triggers
Regex for user intent:
```json
"intentPatterns": [
  "(create|add|implement).*?(route|endpoint|API)",
  "(how to|best practice).*?(backend|service)"
]
```

### 3. File Path Triggers
Glob patterns for file context:
```json
"pathPatterns": ["src/backend/**/*.ts", "api/**/*.ts"],
"pathExclusions": ["**/*.test.ts", "**/*.spec.ts"]
```

### 4. Content Pattern Triggers
Code content detection:
```json
"contentPatterns": ["import.*Prisma", "router\\.get"]
```

---

## Priority Levels

| Priority | When Triggered | Display |
|----------|----------------|---------|
| **critical** | Always | ⚠️ CRITICAL SKILLS (REQUIRED) |
| **high** | Most matches | 📚 RECOMMENDED SKILLS |
| **medium** | Clear matches | 💡 SUGGESTED SKILLS |
| **low** | Explicit only | 📌 OPTIONAL SKILLS |

---

## Hook Registration

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation.sh"
      }]
    }]
  }
}
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                 AUTO-ACTIVATION SYSTEM                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  User Prompt → [UserPromptSubmit Hook]                  │
│                      ↓                                   │
│              Read skill-rules.json                       │
│                      ↓                                   │
│              Match triggers:                             │
│              • Keywords (case-insensitive)               │
│              • Intent patterns (regex)                   │
│              • File paths (glob)                         │
│              • Content patterns (code detection)         │
│                      ↓                                   │
│              Output skill suggestions                    │
│                      ↓                                   │
│              Claude uses Skill tool                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```
