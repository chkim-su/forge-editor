"""
Shared utilities for forge-editor scripts.

This module provides common functionality used across multiple scripts:
- Path utilities (project root detection, file traversal)
- Result tracking (base classes for validation/test results)
- Output formatting (colors, structured output)

Usage:
    from lib.paths import get_project_root, find_files
    from lib.results import BaseResult
    from lib.formatting import format_error, format_warning
"""

from .paths import get_project_root, find_files, get_relative_path
from .results import BaseResult
from .formatting import Colors, format_error, format_warning, format_pass

__all__ = [
    'get_project_root',
    'find_files',
    'get_relative_path',
    'BaseResult',
    'Colors',
    'format_error',
    'format_warning',
    'format_pass',
]
