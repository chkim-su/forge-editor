"""
Output formatting utilities for forge-editor scripts.

Provides consistent formatting across all scripts:
- ANSI color codes for terminal output
- Structured message formatting (errors, warnings, passes)
- Table formatting utilities
"""

import sys
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'

    # Reset
    RESET = '\033[0m'

    @classmethod
    def disable(cls) -> None:
        """Disable colors (for non-TTY output)."""
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''
        cls.WHITE = ''
        cls.BOLD = ''
        cls.DIM = ''
        cls.UNDERLINE = ''
        cls.RESET = ''

    @classmethod
    def auto_detect(cls) -> None:
        """Auto-disable colors if not connected to TTY."""
        if not sys.stdout.isatty():
            cls.disable()


def format_error(code: str, message: str, detail: Optional[str] = None) -> str:
    """
    Format an error message with consistent styling.

    Args:
        code: Error code (e.g., "E016", "E017")
        message: Main error message
        detail: Optional additional detail

    Returns:
        Formatted error string with color codes
    """
    result = f"{Colors.RED}{Colors.BOLD}{code}{Colors.RESET}: {message}"
    if detail:
        result += f"\n  {Colors.DIM}{detail}{Colors.RESET}"
    return result


def format_warning(code: str, message: str, detail: Optional[str] = None) -> str:
    """
    Format a warning message with consistent styling.

    Args:
        code: Warning code (e.g., "W028", "W037")
        message: Main warning message
        detail: Optional additional detail

    Returns:
        Formatted warning string with color codes
    """
    result = f"{Colors.YELLOW}{code}{Colors.RESET}: {message}"
    if detail:
        result += f"\n  {Colors.DIM}{detail}{Colors.RESET}"
    return result


def format_pass(item: str, detail: Optional[str] = None) -> str:
    """
    Format a passed check message.

    Args:
        item: Item that passed
        detail: Optional additional detail

    Returns:
        Formatted pass string with color codes
    """
    result = f"{Colors.GREEN}[PASS]{Colors.RESET} {item}"
    if detail:
        result += f" {Colors.DIM}({detail}){Colors.RESET}"
    return result


def format_summary(passed: int, failed: int, warnings: int) -> str:
    """
    Format a summary line.

    Args:
        passed: Number of passed checks
        failed: Number of failed checks
        warnings: Number of warnings

    Returns:
        Formatted summary string
    """
    total = passed + failed

    if failed > 0:
        status = f"{Colors.RED}{Colors.BOLD}FAIL{Colors.RESET}"
    elif warnings > 0:
        status = f"{Colors.YELLOW}WARN{Colors.RESET}"
    else:
        status = f"{Colors.GREEN}PASS{Colors.RESET}"

    return (
        f"\n{Colors.BOLD}Summary{Colors.RESET}: {status}\n"
        f"  Passed: {Colors.GREEN}{passed}{Colors.RESET}/{total}\n"
        f"  Failed: {Colors.RED}{failed}{Colors.RESET}\n"
        f"  Warnings: {Colors.YELLOW}{warnings}{Colors.RESET}"
    )


def indent(text: str, prefix: str = "  ") -> str:
    """
    Indent all lines of text.

    Args:
        text: Text to indent
        prefix: Prefix to add to each line

    Returns:
        Indented text
    """
    return "\n".join(prefix + line for line in text.split("\n"))
