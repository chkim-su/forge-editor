# PROJECT_INIT Route

Initialize a new plugin project with clear intent understanding.

## Step 1: Understand Intent

```yaml
AskUserQuestion:
  question: "What is your goal?"
  header: "Purpose"
  options:
    - label: "Marketplace Distribution (Recommended)"
      description: "Create a marketplace that others can install via 'claude marketplace add'"
    - label: "Personal Use Only"
      description: "Local plugin for your own use (simpler setup)"
```

## Step 2: If Marketplace Distribution

```yaml
AskUserQuestion:
  question: "Do you have a GitHub account/organization?"
  header: "GitHub"
  options:
    - label: "Yes - Use GitHub"
      description: "Deploy via GitHub repository"
    - label: "No - Local Path"
      description: "Users will need to clone/download"
```

**If GitHub**: Ask for owner/repo format.

## Step 3: Create Project Structure

### For Marketplace (GitHub):

```
{project-name}/
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
├── .claude/skills/skill-rules.json  ← Optional
├── skills/
├── commands/
├── agents/
├── hooks/hooks.json
└── scripts/
```

**marketplace.json** (GitHub source):
```json
{
  "name": "{project-name}-marketplace",
  "owner": {"name": "{user}"},
  "plugins": [{
    "name": "{plugin-name}",
    "source": {"source": "github", "repo": "{owner/repo}"},
    "skills": ["./skills/{skill-name}"],
    "commands": ["./commands/{command-name}.md"],
    "agents": ["./agents/{agent-name}.md"]
  }]
}
```

### For Personal Use:

**marketplace.json** (local source):
```json
{
  "name": "{project-name}-marketplace",
  "owner": {"name": "{user}"},
  "plugins": [{
    "name": "{plugin-name}",
    "source": "./",
    "skills": ["./skills/{skill-name}"]
  }]
}
```

## Step 4: Critical Explanation

```markdown
## 프로젝트 구조 이해하기

### 마켓플레이스 vs 플러그인
- **마켓플레이스**: 플러그인 목록 레지스트리
- **플러그인**: 실제 기능 코드

### Source 설정
| Source 타입 | 의미 | 사용 시점 |
|------------|------|----------|
| `"./"` | 로컬 파일 | 개발/테스트 |
| `{"source": "github", ...}` | GitHub 다운로드 | 배포 후 |
```

## Step 5: Post-Init Validation

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py
```

**MUST pass before proceeding.**

## Step 6: Next Steps

```markdown
1. **컴포넌트 생성**: `/wizard skill`, `/wizard agent`, `/wizard command`
2. **(Optional) Skill Auto-Activation**: `skill-activation-patterns` 참고
3. **로컬 테스트**: `/wizard register` → Claude Code 재시작
4. **배포**: `git push` → `/wizard publish`
```
