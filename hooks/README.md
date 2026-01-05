# Hooks Configuration

This directory contains hook configurations for automatic plugin validation.

## Setup

Copy the hook configuration to your `.claude/settings.json`:

```json
{
  "hooks": [
    {
      "event": "PreToolUse",
      "matcher": {
        "tool_name": "Bash",
        "query": "git push"
      },
      "command": "python3 scripts/validate_all.py",
      "run_in_background": false
    }
  ]
}
```

## What It Does

- **Trigger**: Before any `git push` command
- **Action**: Runs `validate_all.py` to check plugin integrity
- **Result**:
  - Exit 0 → Push proceeds
  - Exit 1/2 → Push blocked with error feedback

## Manual Validation

You can also run validation manually:

```bash
python3 scripts/validate_all.py
python3 scripts/validate_all.py --json  # JSON output
```

## Hook Events

| Event | When | Use Case |
|-------|------|----------|
| PreToolUse | Before tool runs | Block dangerous operations |
| PostToolUse | After tool runs | Auto-format, validate output |
| Stop | Claude finishes | Final checks |
| Notification | Alert sent | Custom notifications |
