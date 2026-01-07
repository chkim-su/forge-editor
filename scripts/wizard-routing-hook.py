#!/usr/bin/env python3
"""
Wizard Routing Enforcement Hook

Enforces semantic routing protocol for wizard skill invocations.
Ensures context analysis and intent classification happen before routing.

PreToolUse: Initialize wizard routing session
PostToolUse: Verify phases were followed, warn if skipped

State file: .claude/local/wizard-routing.json
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime


def get_state_path() -> Path:
    """Get wizard routing state file path."""
    cwd = Path.cwd()
    git_dir = cwd
    while git_dir != git_dir.parent:
        if (git_dir / ".git").exists():
            return git_dir / ".claude" / "local" / "wizard-routing.json"
        git_dir = git_dir.parent
    return cwd / ".claude" / "local" / "wizard-routing.json"


def load_state() -> dict:
    """Load wizard routing state."""
    state_path = get_state_path()
    if not state_path.exists():
        return {}
    try:
        with open(state_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_state(state: dict):
    """Save wizard routing state."""
    state_path = get_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def is_wizard_skill(tool_input: dict) -> bool:
    """Check if this is a wizard skill invocation."""
    skill_name = tool_input.get("skill", "")
    return "wizard" in skill_name.lower() and "forge-editor" in skill_name.lower()


def get_user_input(tool_input: dict) -> str:
    """Extract user input/args from skill invocation."""
    return tool_input.get("args", "")


# Routing patterns from wizard/SKILL.md - MUST check these FIRST
ROUTING_PATTERNS = {
    "MCP": ["mcp", "gateway", "isolation", "serena", "playwright", "daemon"],
    "LLM_INTEGRATION": ["llm", "sdk", "background agent"],
    "SKILL": ["skill create", "skill 만들", "스킬 생성"],
    "SKILL_FROM_CODE": ["convert", "from code", "변환"],
    "AGENT": ["agent", "subagent", "에이전트"],
    "COMMAND": ["command", "workflow"],
    "HOOK_DESIGN": ["hook design", "proper hook", "hook 설계"],
    "SKILL_RULES": ["skill-rules", "auto-activation", "trigger"],
    "ANALYZE": ["analyze", "review", "분석"],
    "VALIDATE": ["validate", "check", "검증"],
    "PUBLISH": ["publish", "deploy", "배포"],
    "LOCAL_REGISTER": ["register", "local", "등록"],
    "PROJECT_INIT": ["init", "new project", "새 프로젝트"],
    "FORGE": ["forge", "clarify", "idea", "vague", "unsure"],
}


def detect_pattern_matches(user_input: str) -> list[tuple[str, str]]:
    """Detect routing patterns in user input. Returns list of (route, matched_keyword)."""
    input_lower = user_input.lower()
    matches = []
    for route, keywords in ROUTING_PATTERNS.items():
        for kw in keywords:
            if kw in input_lower:
                matches.append((route, kw))
    return matches


def handle_pre_tool_use(input_data: dict):
    """PreToolUse: Initialize wizard routing session with pattern detection."""
    tool_input = input_data.get("tool_input", {})

    if not is_wizard_skill(tool_input):
        sys.exit(0)  # Not wizard, allow

    user_input = get_user_input(tool_input)

    # Auto-detect routing patterns
    pattern_matches = detect_pattern_matches(user_input)

    # Initialize new wizard routing session
    state = {
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "user_input": user_input,
        "detected_patterns": [{"route": r, "keyword": k} for r, k in pattern_matches],
        "phases": {
            "pattern_check": {"status": "pending", "result": None},
            "context_analysis": {"status": "pending", "result": None},
            "intent_classification": {"status": "pending", "result": None},
            "route_execution": {"status": "pending", "result": None}
        },
        "context": {
            "keywords": [],
            "topics": [],
            "is_followup": False
        },
        "classification": {
            "route": None,
            "confidence": None
        },
        "created_at": datetime.now().isoformat()
    }

    save_state(state)

    # Build pattern match alert if patterns detected
    pattern_alert = ""
    if pattern_matches:
        detected_routes = list(set(r for r, _ in pattern_matches))
        matched_keywords = [k for _, k in pattern_matches]
        pattern_alert = f"""
## PATTERN MATCH DETECTED - USE THIS ROUTE

The following routing keywords were detected in user input:
- **Keywords found**: {', '.join(f'`{k}`' for k in matched_keywords)}
- **Matched routes**: {', '.join(detected_routes)}

**You MUST route to: `{detected_routes[0]}`** (highest priority match)

DO NOT override with semantic analysis. Pattern matching takes precedence.
"""

    # Inject context reminder about semantic routing protocol
    additional_context = f"""{pattern_alert}
## Wizard Routing Protocol (MANDATORY)

### STEP 0: Pattern Matching (ALWAYS FIRST)

**Check the routing table BEFORE any semantic analysis:**

| Pattern | Route |
|---------|-------|
| mcp, gateway, isolation, serena, playwright | MCP |
| llm, sdk, background agent | LLM_INTEGRATION |
| skill create | SKILL |
| agent, subagent | AGENT |
| hook design | HOOK_DESIGN |
| analyze, review | ANALYZE |
| validate, check | VALIDATE |

**If a pattern matches → Route directly. Skip semantic analysis.**

### Phase 1: Semantic Context Analysis (ONLY if no pattern match)
Extract from conversation:
- keywords: technical terms (MCP, skill, hook, etc.)
- topics: what was being discussed
- is_followup: is this input referencing prior discussion?

After analysis, record with:
```bash
python3 scripts/forge-state.py wizard-context "keyword1,keyword2" "topic1,topic2" "true/false"
```

### Phase 2: Intent Classification (REQUIRES Phase 1)
Classify user intent using input + context:
```bash
python3 scripts/forge-state.py wizard-classify "ROUTE_NAME" "high/medium/low"
```

### Phase 3: Route Execution
Execute classified route OR show context-aware Q&A.
Mark completion with:
```bash
python3 scripts/forge-state.py wizard-phase route_execution completed
```

### CRITICAL WARNING
- Pattern matching MUST happen BEFORE semantic analysis
- If `mcp` is in user input → Route to MCP, not SKILL
- Overriding pattern match with semantic judgment is a ROUTING FAILURE
"""

    # Output additional context for injection
    print(json.dumps({"additionalContext": additional_context}))
    sys.exit(0)


def handle_post_tool_use(input_data: dict):
    """PostToolUse: Verify wizard routing phases."""
    tool_input = input_data.get("tool_input", {})
    tool_output = input_data.get("tool_output", "")

    if not is_wizard_skill(tool_input):
        sys.exit(0)  # Not wizard, allow

    state = load_state()
    if not state:
        # No state - this shouldn't happen if PreToolUse ran
        sys.exit(0)

    # Check if phases were completed
    context_done = state.get("phases", {}).get("context_analysis", {}).get("status") == "completed"
    classify_done = state.get("phases", {}).get("intent_classification", {}).get("status") == "completed"

    # Analyze output for signs of skipped routing
    output_lower = tool_output.lower() if tool_output else ""

    # Signs of skipping semantic routing
    skip_indicators = [
        "라우팅 패턴과 맞지 않",  # "doesn't match routing patterns"
        "wizard 라우팅 패턴",
        "what would you like to do",
        "무엇을 도와드릴까요",
    ]

    # Signs of proper semantic routing
    proper_routing_indicators = [
        "context analysis",
        "컨텍스트 분석",
        "keywords:",
        "키워드:",
        "intent classification",
        "의도 분류",
        "wizard-context",
        "wizard-classify",
    ]

    skipped = any(indicator in output_lower for indicator in skip_indicators)
    proper = any(indicator in output_lower for indicator in proper_routing_indicators)

    if skipped and not proper and not context_done:
        # Semantic routing was likely skipped
        print("=" * 60, file=sys.stderr)
        print("  WARNING: Wizard semantic routing may have been skipped", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)
        print("  The wizard output suggests generic menu was shown", file=sys.stderr)
        print("  without proper context analysis.", file=sys.stderr)
        print(file=sys.stderr)
        print("  Phase Status:", file=sys.stderr)
        print(f"    [ ] context_analysis: {state.get('phases', {}).get('context_analysis', {}).get('status', 'unknown')}", file=sys.stderr)
        print(f"    [ ] intent_classification: {state.get('phases', {}).get('intent_classification', {}).get('status', 'unknown')}", file=sys.stderr)
        print(file=sys.stderr)
        print("  Please ensure semantic routing protocol is followed.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # Don't block, just warn (exit 0)
        # For blocking, use exit 2

    sys.exit(0)


def main():
    """Main entry point - detect hook event type and handle."""
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)  # No valid input, allow

    # Determine if this is PreToolUse or PostToolUse based on presence of tool_output
    if "tool_output" in input_data:
        handle_post_tool_use(input_data)
    else:
        handle_pre_tool_use(input_data)


if __name__ == "__main__":
    main()
