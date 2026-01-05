# Hook Implementation

## Architecture

```
.claude/
├── hooks/
│   ├── skill-activation.sh       # Bash wrapper (entry point)
│   └── skill-activation.ts       # TypeScript implementation
├── skills/
│   └── skill-rules.json          # Trigger configuration
└── settings.json                 # Hook registration
```

---

## TypeScript Implementation

`skill-activation.ts`:

```typescript
#!/usr/bin/env npx ts-node
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// === Type Definitions ===

interface HookInput {
  session_id: string;
  prompt: string;
  cwd: string;
}

interface PromptTriggers {
  keywords?: string[];
  intentPatterns?: string[];
}

interface FileTriggers {
  pathPatterns?: string[];
  pathExclusions?: string[];
  contentPatterns?: string[];
}

interface SkillRule {
  type: 'guardrail' | 'domain';
  enforcement: 'block' | 'suggest' | 'warn';
  priority: 'critical' | 'high' | 'medium' | 'low';
  description?: string;
  promptTriggers?: PromptTriggers;
  fileTriggers?: FileTriggers;
  blockMessage?: string;
  skipConditions?: {
    sessionSkillUsed?: boolean;
    fileMarkers?: string[];
  };
}

interface SkillRules {
  version: string;
  skills: Record<string, SkillRule>;
}

interface MatchedSkill {
  name: string;
  matchType: 'keyword' | 'intent' | 'path' | 'content';
  config: SkillRule;
}

// === Main Logic ===

async function main(): Promise<void> {
  try {
    // Read hook input from stdin
    const input = readFileSync(0, 'utf-8');
    const data: HookInput = JSON.parse(input);
    const prompt = data.prompt.toLowerCase();

    // Load skill rules
    const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
    const rulesPath = join(projectDir, '.claude', 'skills', 'skill-rules.json');

    if (!existsSync(rulesPath)) {
      // No rules file, exit silently
      process.exit(0);
    }

    const rules: SkillRules = JSON.parse(readFileSync(rulesPath, 'utf-8'));
    const matchedSkills: MatchedSkill[] = [];

    // Check each skill for matches
    for (const [skillName, config] of Object.entries(rules.skills)) {
      const match = checkSkillMatch(prompt, skillName, config);
      if (match) {
        matchedSkills.push(match);
      }
    }

    // Generate output if matches found
    if (matchedSkills.length > 0) {
      console.log(formatOutput(matchedSkills));
    }

    process.exit(0);
  } catch (err) {
    console.error('Skill activation error:', err);
    process.exit(0); // Don't block on errors
  }
}

function checkSkillMatch(
  prompt: string,
  skillName: string,
  config: SkillRule
): MatchedSkill | null {
  // Check prompt triggers
  if (config.promptTriggers) {
    const { keywords, intentPatterns } = config.promptTriggers;

    // Keyword matching
    if (keywords?.some(kw => prompt.includes(kw.toLowerCase()))) {
      return { name: skillName, matchType: 'keyword', config };
    }

    // Intent pattern matching
    if (intentPatterns?.some(pattern => new RegExp(pattern, 'i').test(prompt))) {
      return { name: skillName, matchType: 'intent', config };
    }
  }

  return null;
}

function formatOutput(skills: MatchedSkill[]): string {
  const lines: string[] = [
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    '🎯 SKILL ACTIVATION',
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    ''
  ];

  // Group by priority
  const groups = {
    critical: skills.filter(s => s.config.priority === 'critical'),
    high: skills.filter(s => s.config.priority === 'high'),
    medium: skills.filter(s => s.config.priority === 'medium'),
    low: skills.filter(s => s.config.priority === 'low')
  };

  if (groups.critical.length > 0) {
    lines.push('⚠️ CRITICAL (REQUIRED):');
    groups.critical.forEach(s => lines.push(`  → ${s.name}`));
    lines.push('');
  }

  if (groups.high.length > 0) {
    lines.push('📚 RECOMMENDED:');
    groups.high.forEach(s => lines.push(`  → ${s.name}`));
    lines.push('');
  }

  if (groups.medium.length > 0) {
    lines.push('💡 SUGGESTED:');
    groups.medium.forEach(s => lines.push(`  → ${s.name}`));
    lines.push('');
  }

  if (groups.low.length > 0) {
    lines.push('📌 OPTIONAL:');
    groups.low.forEach(s => lines.push(`  → ${s.name}`));
    lines.push('');
  }

  lines.push('ACTION: Use Skill tool before responding');
  lines.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  return lines.join('\n');
}

main();
```

---

## Bash Wrapper

`skill-activation.sh`:

```bash
#!/bin/bash
# Skill Activation Hook - UserPromptSubmit
# Reads prompt from stdin, checks skill-rules.json, outputs suggestions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS_FILE="$SCRIPT_DIR/skill-activation.ts"

# Check if ts-node is available
if command -v npx &> /dev/null; then
    npx ts-node "$TS_FILE"
else
    # Fallback: try node with compiled JS
    node "${TS_FILE%.ts}.js" 2>/dev/null || exit 0
fi
```

---

## settings.json Registration

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation.sh"
          }
        ]
      }
    ]
  }
}
```

---

## File Trigger Implementation (Advanced)

For PostToolUse file pattern matching:

```typescript
// Add to skill-activation.ts for file-based triggers

interface FileContext {
  path: string;
  content?: string;
}

function checkFileTriggers(
  fileContext: FileContext,
  triggers: FileTriggers
): boolean {
  const { pathPatterns, pathExclusions, contentPatterns } = triggers;

  // Check path exclusions first
  if (pathExclusions?.some(pattern => minimatch(fileContext.path, pattern))) {
    return false;
  }

  // Check path patterns
  if (pathPatterns?.some(pattern => minimatch(fileContext.path, pattern))) {
    return true;
  }

  // Check content patterns
  if (fileContext.content && contentPatterns) {
    return contentPatterns.some(pattern =>
      new RegExp(pattern).test(fileContext.content!)
    );
  }

  return false;
}
```

---

## Dependencies

```json
{
  "devDependencies": {
    "typescript": "^5.0.0",
    "ts-node": "^10.9.0",
    "@types/node": "^20.0.0",
    "minimatch": "^9.0.0"
  }
}
```

---

## Testing

```bash
# Test hook manually
echo '{"prompt": "create a backend API endpoint", "session_id": "test"}' | \
  bash .claude/hooks/skill-activation.sh

# Expected output:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 SKILL ACTIVATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# 📚 RECOMMENDED:
#   → backend-dev-guidelines
#
# ACTION: Use Skill tool before responding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
