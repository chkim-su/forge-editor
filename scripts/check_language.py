#!/usr/bin/env python3
"""
Language detection hook for forge-editor plugin documentation.

Detects non-English content (Korean, Japanese, Chinese, etc.) in markdown files
and issues warnings for accessibility considerations.

W048: Non-English content detected in documentation
"""

import json
import os
import re
import sys
from pathlib import Path

# Unicode ranges for common non-English scripts
KOREAN_RANGE = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')
JAPANESE_RANGE = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
CHINESE_RANGE = re.compile(r'[\u4e00-\u9fff]')
CYRILLIC_RANGE = re.compile(r'[\u0400-\u04ff]')
ARABIC_RANGE = re.compile(r'[\u0600-\u06ff]')

LANGUAGE_PATTERNS = {
    'Korean': KOREAN_RANGE,
    'Japanese': JAPANESE_RANGE,
    'Chinese': CHINESE_RANGE,
    'Cyrillic': CYRILLIC_RANGE,
    'Arabic': ARABIC_RANGE,
}


def detect_languages(text: str) -> dict[str, int]:
    """Detect non-English language characters in text."""
    results = {}
    for lang, pattern in LANGUAGE_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            results[lang] = len(matches)
    return results


def is_code_block(line: str, in_code_block: bool) -> tuple[bool, bool]:
    """Check if line is part of a code block."""
    if line.strip().startswith('```'):
        return True, not in_code_block
    return False, in_code_block


def analyze_file(filepath: Path) -> dict:
    """Analyze a file for non-English content."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return {'error': str(e)}

    # Skip files that are explicitly multilingual
    if 'multilingual' in filepath.name.lower() or 'i18n' in filepath.name.lower():
        return {'skipped': 'multilingual file'}

    lines = content.split('\n')
    findings = []
    in_code_block = False

    for line_num, line in enumerate(lines, 1):
        # Track code blocks
        is_fence, in_code_block = is_code_block(line, in_code_block)
        if is_fence or in_code_block:
            continue

        # Skip comments (yaml/json style)
        stripped = line.strip()
        if stripped.startswith('#') and ':' not in stripped[:20]:
            # This is likely a markdown header, not a comment
            pass
        elif stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Detect languages
        detected = detect_languages(line)
        if detected:
            findings.append({
                'line': line_num,
                'languages': detected,
                'preview': line[:80] + ('...' if len(line) > 80 else '')
            })

    return {
        'filepath': str(filepath),
        'findings': findings,
        'total_lines_with_non_english': len(findings)
    }


def main():
    """Main entry point for hook execution."""
    # Read tool input from environment or stdin
    tool_input = os.environ.get('TOOL_INPUT', '')

    if not tool_input:
        try:
            tool_input = sys.stdin.read()
        except Exception:
            pass

    if not tool_input:
        # No input, exit silently
        sys.exit(0)

    try:
        data = json.loads(tool_input)
    except json.JSONDecodeError:
        sys.exit(0)

    # Get the file path from Write/Edit tool input
    filepath = data.get('file_path') or data.get('filePath') or data.get('path')
    if not filepath:
        sys.exit(0)

    path = Path(filepath)

    # Only check markdown files
    if path.suffix.lower() not in ['.md', '.markdown']:
        sys.exit(0)

    # Skip certain directories
    skip_dirs = ['node_modules', '.git', 'vendor', 'dist', 'build']
    if any(skip_dir in str(path) for skip_dir in skip_dirs):
        sys.exit(0)

    # Skip bug_report_docs (user's own notes)
    if 'bug_report_docs' in str(path):
        sys.exit(0)

    # Analyze content if it's being written
    content = data.get('content', '')
    if not content and path.exists():
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            sys.exit(0)

    if not content:
        sys.exit(0)

    # Detect non-English content
    lines = content.split('\n')
    in_code_block = False
    findings = []

    for line_num, line in enumerate(lines, 1):
        is_fence, in_code_block = is_code_block(line, in_code_block)
        if is_fence or in_code_block:
            continue

        detected = detect_languages(line)
        if detected:
            findings.append({
                'line': line_num,
                'languages': list(detected.keys()),
                'char_count': sum(detected.values())
            })

    if findings:
        # Calculate summary
        total_chars = sum(f['char_count'] for f in findings)
        languages = set()
        for f in findings:
            languages.update(f['languages'])

        # Output warning
        output = {
            'status': 'warn',
            'code': 'W048',
            'message': f"Non-English content detected: {', '.join(sorted(languages))} ({total_chars} characters in {len(findings)} lines)",
            'details': {
                'file': str(path),
                'languages': list(languages),
                'affected_lines': len(findings),
                'total_non_english_chars': total_chars
            },
            'suggestion': "Consider translating for broader accessibility, or add '# multilingual' comment if intentional."
        }

        print(json.dumps(output, ensure_ascii=False))
        # Exit 0 = warning only, not blocking
        sys.exit(0)

    # No issues found
    sys.exit(0)


if __name__ == '__main__':
    main()
