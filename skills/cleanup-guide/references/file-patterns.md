# File Pattern Reference

Complete list of unnecessary file patterns detected by W036.

## SENSITIVE (Security Risk)

Files that may contain secrets - **NEVER commit**.

| Pattern | Description | Risk |
|---------|-------------|------|
| `.env` | Environment variables | API keys, passwords |
| `.env.local` | Local environment | Development secrets |
| `.env.production` | Production secrets | Production credentials |
| `credentials.json` | Service account | Full API access |
| `*.pem` | Private key | Authentication |
| `*.key` | Private key | Encryption keys |
| `service-account*.json` | GCP service account | Cloud access |
| `*-credentials.json` | Various credentials | API access |

### Remediation

```bash
# 1. Add to .gitignore
echo ".env*" >> .gitignore
echo "*.pem" >> .gitignore
echo "*.key" >> .gitignore
echo "*credentials*.json" >> .gitignore

# 2. Remove from git history if already committed
git rm --cached .env
git rm --cached credentials.json

# 3. Rotate exposed secrets
# - Regenerate API keys
# - Change passwords
# - Revoke service accounts
```

## DELETE (Cleanup Recommended)

Files/directories that should be removed before distribution.

### Log Files

| Pattern | Source | Command |
|---------|--------|---------|
| `firebase-debug.log` | Firebase CLI | `rm firebase-debug.log` |
| `npm-debug.log` | NPM errors | `rm npm-debug.log` |
| `yarn-error.log` | Yarn errors | `rm yarn-error.log` |
| `debug.log` | Various | `rm debug.log` |
| `*.log` | All logs | `rm *.log` |

### Cache Directories

| Pattern | Source | Command |
|---------|--------|---------|
| `__pycache__` | Python bytecode | `rm -rf __pycache__` |
| `.pytest_cache` | Pytest | `rm -rf .pytest_cache` |
| `.mypy_cache` | Mypy type checker | `rm -rf .mypy_cache` |
| `.cache` | Various | `rm -rf .cache` |
| `node_modules` | NPM packages | `rm -rf node_modules` |
| `.next` | Next.js build | `rm -rf .next` |
| `dist` | Build output | Check if needed |
| `build` | Build output | Check if needed |

### Bulk Cleanup

```bash
# One-liner cleanup
rm -rf __pycache__ .pytest_cache .mypy_cache .cache node_modules
rm -f *.log firebase-debug.log npm-debug.log yarn-error.log
```

## GITIGNORE (Should Be Ignored)

Files that should be in `.gitignore` but don't need immediate deletion.

### System Files

| Pattern | OS | Description |
|---------|-----|-------------|
| `.DS_Store` | macOS | Folder metadata |
| `Thumbs.db` | Windows | Thumbnail cache |
| `desktop.ini` | Windows | Folder settings |
| `.Spotlight-V100` | macOS | Spotlight index |

### IDE/Editor Files

| Pattern | Editor | Recommendation |
|---------|--------|----------------|
| `.idea/` | JetBrains | Usually gitignore |
| `.vscode/` | VS Code | Some files may be shared |
| `*.swp` | Vim | Always gitignore |
| `*.swo` | Vim | Always gitignore |
| `*~` | Emacs backup | Always gitignore |

### Recommended .gitignore

```gitignore
# OS
.DS_Store
Thumbs.db

# Editor
.idea/
.vscode/
*.swp
*.swo
*~

# Logs
*.log

# Caches
__pycache__/
.pytest_cache/
.mypy_cache/
.cache/
node_modules/

# Secrets
.env*
*.pem
*.key
*credentials*.json
```

## Decision Matrix

When to DELETE vs GITIGNORE:

| File Exists | In Git | Action |
|-------------|--------|--------|
| Yes | No | Add to .gitignore |
| Yes | Yes | `git rm --cached` then .gitignore |
| No | N/A | Just add pattern to .gitignore |

## Validation Integration

This pattern list is used by:
- `scripts/validate_all.py` → W036 check
- `/forge-editor:wizard validate` → Automatic detection
- `/forge-editor:cleanup-guide` → Manual cleanup guidance
