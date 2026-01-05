#!/usr/bin/env python3
"""
Solution Synthesis Gate - W035 Enforcement Hook

Warns when ANALYZE route completes without Solution Synthesis section.
This ensures skillmaker's philosophy ("문서 기반 강제는 무의미") is applied to itself.

Hook Type: PostToolUse (Task)
Behavior: Warning only (does not block)
"""

import sys
import json


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # No input or invalid JSON - allow
        sys.exit(0)
    
    tool_name = data.get('tool_name', '')
    
    # Only check Task tool completions
    if tool_name != 'Task':
        sys.exit(0)
    
    # Check if this was an ANALYZE-related task
    tool_input = data.get('tool_input', {})
    prompt = tool_input.get('prompt', '').lower()
    description = tool_input.get('description', '').lower()
    
    # Keywords indicating ANALYZE route
    analyze_keywords = ['analyze', 'analysis', '분석', '고찰', 'review', '리뷰', '검토']
    
    is_analyze_task = any(kw in prompt or kw in description for kw in analyze_keywords)
    
    if not is_analyze_task:
        sys.exit(0)
    
    # Check the result for Solution Synthesis section
    tool_result = data.get('tool_result', '')
    
    # Keywords indicating Solution Synthesis was performed
    synthesis_markers = [
        '해결책 종합',
        'Solution Synthesis',
        '해결책 직접 추출',
        '적극적 추출',
        '구현 단계',
        '구체적 방법',
        '즉시 실행 가능'
    ]
    
    has_synthesis = any(marker in tool_result for marker in synthesis_markers)
    
    if not has_synthesis:
        # Issue warning but don't block
        print("=" * 60)
        print("⚠️  SOLUTION SYNTHESIS WARNING (W035 Enforcement)")
        print("=" * 60)
        print()
        print("ANALYZE 라우트가 완료되었으나 Solution Synthesis 섹션이 감지되지 않았습니다.")
        print()
        print("skillmaker 원칙에 따라:")
        print("  1. 문제 발견 시 관련 스킬을 즉시 로드해야 합니다")
        print("  2. 스킬의 references/에서 해결책을 추출해야 합니다")
        print("  3. 사용자가 바로 실행 가능한 형태로 제시해야 합니다")
        print()
        print("금지 행동:")
        print("  ❌ '이 스킬을 참고하세요' (수동적)")
        print("  ❌ '패턴이 있습니다' (구체성 부족)")
        print()
        print("권장 행동:")
        print("  ✅ Skill('forge-editor:relevant-skill') 로드")
        print("  ✅ Read('references/solution.md') 수행")
        print("  ✅ 구체적 명령/코드 추출하여 제시")
        print("=" * 60)
    
    # Always allow (warning only, not blocking)
    sys.exit(0)


if __name__ == '__main__':
    main()
