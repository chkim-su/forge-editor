"""
Path utilities for forge-editor scripts.

Provides consistent path handling across all scripts:
- Project root detection
- File discovery with glob patterns
- Relative path calculation
"""

from pathlib import Path
from typing import List, Optional, Union


def get_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Find the forge-editor project root directory.

    Searches upward from start_path (default: script location) for:
    1. plugin.json (plugin root marker)
    2. .claude/ directory (Claude project marker)
    3. .git directory (git root fallback)

    Args:
        start_path: Starting directory for search. Defaults to script's parent.

    Returns:
        Path to project root directory.

    Raises:
        FileNotFoundError: If no project root markers found.
    """
    if start_path is None:
        # Get the caller's script directory
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_file = frame.f_back.f_globals.get('__file__')
            if caller_file:
                start_path = Path(caller_file).parent
            else:
                start_path = Path.cwd()
        else:
            start_path = Path.cwd()

    current = start_path.resolve()

    # Search upward for project markers
    while current != current.parent:
        # Check for plugin.json (primary marker)
        if (current / 'plugin.json').exists():
            return current
        # Check for .claude directory
        if (current / '.claude').is_dir():
            return current
        # Check for .git directory (fallback)
        if (current / '.git').is_dir():
            return current
        current = current.parent

    # Fallback: return start_path's parent (scripts/ -> project root)
    return start_path.parent


def find_files(
    root: Path,
    patterns: Union[str, List[str]],
    exclude_dirs: Optional[List[str]] = None
) -> List[Path]:
    """
    Find files matching glob patterns.

    Args:
        root: Directory to search from.
        patterns: Glob pattern(s) to match (e.g., "**/*.py", ["*.md", "*.txt"]).
        exclude_dirs: Directory names to skip (e.g., ["node_modules", ".git"]).

    Returns:
        List of matching file paths, sorted by path.

    Example:
        >>> find_files(root, "**/*.py", exclude_dirs=["__pycache__"])
        [Path('scripts/validate_all.py'), Path('scripts/lib/paths.py'), ...]
    """
    if exclude_dirs is None:
        exclude_dirs = ['node_modules', '.git', '__pycache__', '.venv', 'venv']

    if isinstance(patterns, str):
        patterns = [patterns]

    results = []
    for pattern in patterns:
        for path in root.rglob(pattern):
            # Skip excluded directories
            if any(excluded in path.parts for excluded in exclude_dirs):
                continue
            if path.is_file():
                results.append(path)

    return sorted(set(results))


def get_relative_path(path: Path, root: Optional[Path] = None) -> str:
    """
    Get path relative to project root, for display purposes.

    Args:
        path: Absolute path to convert.
        root: Project root. Auto-detected if not provided.

    Returns:
        Relative path string (e.g., "scripts/validate_all.py").
    """
    if root is None:
        root = get_project_root()

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
