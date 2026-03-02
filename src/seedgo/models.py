"""
Seed Go Core Data Models

Defines the plugin contract types: Severity, CheckItem, and CheckResult.
All plugin check() functions must return a CheckResult instance.

These are pure dataclasses with no external dependencies — safe to import
anywhere without pulling in AIPass or other infrastructure.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels for individual check items.

    Determines how a failed check impacts the overall score and pass/fail:
    - ERROR: Full score deduction. Any unresolved error blocks pass regardless of score.
    - WARNING: Half score deduction (configurable). Degrades score but does not block pass.
    - INFO: No score deduction. Informational only — shown in output, zero score impact.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CheckItem:
    """One individual check within a plugin result.

    Represents a single rule evaluation. A plugin may return many CheckItems,
    one per rule or per violation found in the file.

    Attributes:
        name: Short identifier for this check (e.g., "bare-except", "missing-type-hint").
        passed: Whether this specific check passed.
        message: Human-readable explanation of the result or violation.
        severity: How serious the violation is. Defaults to ERROR.
        line: Source line number where the violation was found, if applicable.
        fix_hint: Actionable suggestion for how to resolve the violation.
    """

    name: str
    passed: bool
    message: str
    severity: Severity = Severity.ERROR
    line: Optional[int] = None
    fix_hint: Optional[str] = None


@dataclass
class CheckResult:
    """Return type for all plugin check() functions.

    Every plugin must return exactly one CheckResult per file checked.
    The result aggregates all individual CheckItem results and provides
    an overall pass/fail verdict and score.

    Attributes:
        plugin: The plugin's PLUGIN_NAME string (e.g., "no-bare-except").
        passed: Overall pass/fail for this plugin against this file.
        checks: List of individual check results. Empty list means no checks ran.
        score: Weighted score from 0-100. Calculated by the scoring engine.
        file_path: Absolute path to the file that was checked.
        metadata: Plugin-defined extra data (e.g., AST stats, timing). Serializable to JSON.
    """

    plugin: str
    passed: bool
    checks: list[CheckItem] = field(default_factory=list)
    score: int = 0
    file_path: str = ""
    metadata: dict = field(default_factory=dict)
