"""
Result tracking classes for forge-editor scripts.

Provides base classes for validation and test result tracking:
- BaseResult: Common result tracking (passed/failed/warnings)
- Extensible for specific use cases (ValidationResult, TestResult)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class BaseResult:
    """
    Base class for tracking operation results.

    Provides common functionality for:
    - Tracking passed/failed/warning items
    - Converting to dictionary for JSON output
    - Calculating summary statistics

    Subclasses can extend with additional functionality:
    - ValidationResult: Adds auto-fix capabilities
    - TestResult: Adds test-specific metadata
    """
    passed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_pass(self, item: str, detail: str = "") -> None:
        """Record a passed check."""
        msg = f"{item}: {detail}" if detail else item
        self.passed.append(msg)

    def add_fail(self, item: str, detail: str = "") -> None:
        """Record a failed check."""
        msg = f"{item}: {detail}" if detail else item
        self.failed.append(msg)

    def add_warning(self, item: str, detail: str = "") -> None:
        """Record a warning."""
        msg = f"{item}: {detail}" if detail else item
        self.warnings.append(msg)

    @property
    def success(self) -> bool:
        """True if no failures."""
        return len(self.failed) == 0

    @property
    def has_warnings(self) -> bool:
        """True if any warnings."""
        return len(self.warnings) > 0

    def summary(self) -> Dict[str, int]:
        """Get counts summary."""
        return {
            "total": len(self.passed) + len(self.failed),
            "passed": len(self.passed),
            "failed": len(self.failed),
            "warnings": len(self.warnings),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "summary": self.summary(),
            "success": self.success,
        }

    def merge(self, other: 'BaseResult') -> 'BaseResult':
        """Merge another result into this one."""
        self.passed.extend(other.passed)
        self.failed.extend(other.failed)
        self.warnings.extend(other.warnings)
        return self


@dataclass
class TestResult(BaseResult):
    """
    Extended result class for test suites.

    Adds test-specific metadata and categorization.
    """
    test_name: str = ""
    skipped: List[str] = field(default_factory=list)

    def add_skip(self, item: str, reason: str = "") -> None:
        """Record a skipped test."""
        msg = f"{item}: {reason}" if reason else item
        self.skipped.append(msg)

    def summary(self) -> Dict[str, int]:
        """Get counts summary including skipped."""
        base = super().summary()
        base["skipped"] = len(self.skipped)
        return base

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including skipped."""
        result = super().to_dict()
        result["skipped"] = self.skipped
        result["test_name"] = self.test_name
        return result
