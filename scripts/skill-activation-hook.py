#!/usr/bin/env python3
"""
Skillmaker UserPromptSubmit Hook - Semantic Analysis Edition
Suggests relevant skills using LLM-based intent classification when keyword matching fails.
"""

import json
import os
import sys
import re
import asyncio
from pathlib import Path
from typing import Optional

# Skill catalog for semantic classification
SKILL_CATALOG = """
Available skills and their purposes:
- skill-design: Creating new skills, skill structure, SKILL.md format
- orchestration-patterns: Creating agents, subagents, multi-agent coordination
- mcp-gateway-patterns: MCP tool isolation, Serena/Playwright integration
- hook-templates: Creating hooks, automation, triggers
- skill-activation-patterns: Auto-loading skills, skill-rules.json configuration
- workflow-state-patterns: Multi-phase workflows, state machines, gates
- critical-analysis-patterns: Code review, architectural analysis, design evaluation
- plugin-test-framework: Testing plugins, validation, test environments
- hook-capabilities: Advanced hook features, debugging hooks
- hook-sdk-integration: LLM calls from hooks, background agents
- llm-sdk-guide: u-llm-sdk and claude-only-sdk usage
- mcp-daemon-isolation: Advanced MCP daemon patterns
- skill-catalog: List of available skills
- wizard: Smart routing for plugin development
- cleanup-guide: Removing unnecessary files
- hook-system: Hook fundamentals
"""

def load_skill_rules():
    """Load skill-rules.json from .claude/skills/"""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        rules_path = Path(plugin_root) / ".claude" / "skills" / "skill-rules.json"
    else:
        script_dir = Path(__file__).parent.parent
        rules_path = script_dir / ".claude" / "skills" / "skill-rules.json"

    if not rules_path.exists():
        return None

    with open(rules_path) as f:
        return json.load(f)


def match_keywords(prompt: str, keywords: list) -> bool:
    """Check if any keyword matches in prompt (case-insensitive)"""
    prompt_lower = prompt.lower()
    return any(kw.lower() in prompt_lower for kw in keywords)


def match_patterns(prompt: str, patterns: list) -> bool:
    """Check if any regex pattern matches in prompt"""
    prompt_lower = prompt.lower()
    for pattern in patterns:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return True
    return False


def detect_complexity(prompt: str, complexity_levels: dict) -> Optional[str]:
    """Detect complexity level from prompt"""
    prompt_lower = prompt.lower()
    for level in ["advanced", "standard", "simple"]:
        if level in complexity_levels:
            keywords = complexity_levels[level].get("keywords", [])
            if any(kw.lower() in prompt_lower for kw in keywords):
                return level
    return None


def find_matching_skills_keyword(prompt: str, rules: dict) -> list:
    """Find skills that match the prompt via keywords/patterns"""
    matched = []
    skills = rules.get("skills", {})

    for skill_name, config in skills.items():
        triggers = config.get("promptTriggers", {})
        keywords = triggers.get("keywords", [])
        patterns = triggers.get("intentPatterns", [])

        if match_keywords(prompt, keywords) or match_patterns(prompt, patterns):
            matched.append({
                "name": skill_name,
                "priority": config.get("priority", "low"),
                "type": config.get("type", "domain"),
                "confidence": "high",
                "method": "keyword"
            })

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    matched.sort(key=lambda x: priority_order.get(x["priority"], 99))
    return matched


async def semantic_classify(prompt: str) -> list:
    """Use LLM to classify user intent and match to skills"""
    try:
        # Dynamic import to avoid issues if SDK not installed
        from u_llm_sdk import LLM, LLMConfig
        from llm_types import Provider, ModelTier, AutoApproval
    except ImportError:
        return []  # Fall back to keyword matching only

    config = LLMConfig(
        provider=Provider.CLAUDE,
        tier=ModelTier.LOW,  # Use fast/cheap model for classification
        auto_approval=AutoApproval.FULL,
        timeout=5.0,  # Quick timeout
    )

    classification_prompt = f"""Given this user request, identify the most relevant skillmaker skills.

User request: "{prompt}"

{SKILL_CATALOG}

Reply with a JSON array of skill names, ordered by relevance. Max 3 skills.
Example: ["skill-design", "orchestration-patterns"]

If the request is unclear or doesn't match any skill, reply with: ["UNCLEAR"]
If the request seems to need clarification, reply with: ["ASK_USER"]

ONLY output the JSON array, nothing else."""

    try:
        async with LLM(config) as llm:
            result = await llm.run(classification_prompt)

            # Parse result
            text = result.text.strip()
            if text.startswith("[") and text.endswith("]"):
                skills = json.loads(text)

                if skills == ["UNCLEAR"] or skills == ["ASK_USER"]:
                    return [{"name": "_ambiguous", "confidence": "low", "method": "semantic"}]

                return [
                    {"name": s, "priority": "medium", "confidence": "medium", "method": "semantic"}
                    for s in skills if isinstance(s, str)
                ]
    except Exception:
        pass  # Silently fail, fall back to keyword matching

    return []


def should_use_semantic(prompt: str, keyword_matches: list) -> bool:
    """Determine if semantic analysis should be used"""
    # Don't use semantic if we already have high-confidence matches
    if len(keyword_matches) >= 2:
        return False

    # Use semantic for longer, more complex prompts
    if len(prompt) > 50 and len(keyword_matches) == 0:
        return True

    # Use semantic for Korean text without keyword matches
    if any('\uac00' <= c <= '\ud7af' for c in prompt) and len(keyword_matches) == 0:
        return True

    return False


ANALYSIS_KEYWORDS = [
    # Korean
    "검증", "분석", "리뷰", "검토", "진단", "평가", "감사",
    # English
    "analyze", "analysis", "review", "audit", "diagnose", "evaluate",
    "validate", "verify", "check", "inspect", "assess"
]

ANALYSIS_PATTERNS = [
    r"(전반적|종합적|전체).*검",  # 전반적 검토, 종합적 검증
    r"강건성|적합성|건전성",  # robustness, suitability
    r"개선.*나열|문제.*찾",  # list improvements, find issues
]


def detect_analysis_intent(prompt: str) -> bool:
    """Detect if user is asking for analysis/validation."""
    prompt_lower = prompt.lower()

    # Check keywords
    for kw in ANALYSIS_KEYWORDS:
        if kw.lower() in prompt_lower:
            return True

    # Check patterns
    for pattern in ANALYSIS_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return True

    return False


def output_analysis_context():
    """Output additionalContext for semantic analysis trigger."""
    context = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 SEMANTIC ANALYSIS TRIGGERED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analysis keywords detected. You MUST:

1. Run static validation first:
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_all.py --json

2. Then dispatch semantic agents via Task tool:
   Task(subagent_type="forge-editor:diagnostic-orchestrator",
        prompt="Run comprehensive analysis on this project")

3. Synthesize findings from both layers.

DO NOT skip semantic analysis when user asks for verification/review.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(context)


def format_output(skills: list, complexity: Optional[str], ambiguous: bool = False):
    """Format output for display"""
    if not skills and not ambiguous:
        return

    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📚 RECOMMENDED SKILLS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if complexity:
        print(f"Complexity: {complexity.upper()}")
        print("")

    if ambiguous:
        print("  ⚠️ Request is ambiguous. Consider using:")
        print("     AskUserQuestion to clarify intent")
        print("")

    for skill in skills[:5]:
        if skill.get("name") == "_ambiguous":
            continue
        priority = skill.get("priority", "low")
        method = skill.get("method", "keyword")
        confidence = skill.get("confidence", "high")

        priority_icon = {"high": "⚡", "medium": "💡", "low": "📌"}.get(priority, "•")
        method_tag = f"[{method}]" if method == "semantic" else ""

        print(f"  {priority_icon} forge-editor:{skill['name']} {method_tag}")

    print("")
    print("Use: Skill(\"forge-editor:{name}\") to load")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")


async def async_main():
    """Async main for LLM-based classification"""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    rules = load_skill_rules()
    if not rules:
        sys.exit(0)

    # Step 1: Keyword matching (fast path)
    keyword_matches = find_matching_skills_keyword(prompt, rules)

    # Step 2: Complexity detection
    complexity = detect_complexity(prompt, rules.get("complexity_levels", {}))

    # Step 3: Semantic analysis if needed
    all_matches = keyword_matches.copy()
    ambiguous = False

    if should_use_semantic(prompt, keyword_matches):
        semantic_matches = await semantic_classify(prompt)

        # Check for ambiguity
        if any(s.get("name") == "_ambiguous" for s in semantic_matches):
            ambiguous = True
            semantic_matches = []

        # Merge results, avoiding duplicates
        for sm in semantic_matches:
            if not any(m["name"] == sm["name"] for m in all_matches):
                all_matches.append(sm)

    # Step 4: Add complexity-based skills
    if complexity:
        complexity_skills = rules.get("complexity_levels", {}).get(complexity, {}).get("auto_skills", [])
        for skill_name in complexity_skills:
            if not any(s["name"] == skill_name for s in all_matches):
                all_matches.append({
                    "name": skill_name,
                    "priority": "medium",
                    "confidence": "high",
                    "method": "complexity"
                })

    # Step 5: Detect analysis intent and output trigger
    if detect_analysis_intent(prompt):
        output_analysis_context()

    # Output skill recommendations
    format_output(all_matches, complexity, ambiguous)


def main():
    """Main entry point"""
    try:
        asyncio.run(async_main())
    except Exception:
        # Fallback to sync keyword-only matching
        try:
            input_data = json.load(sys.stdin)
            prompt = input_data.get("prompt", "")
            rules = load_skill_rules()

            if prompt and rules:
                # Check for analysis intent
                if detect_analysis_intent(prompt):
                    output_analysis_context()

                matches = find_matching_skills_keyword(prompt, rules)
                complexity = detect_complexity(prompt, rules.get("complexity_levels", {}))
                format_output(matches, complexity)
        except Exception:
            pass


if __name__ == "__main__":
    main()
