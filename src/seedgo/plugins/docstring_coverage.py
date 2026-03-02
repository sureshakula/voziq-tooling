"""
Seed Go Plugin: docstring-coverage

Checks that public functions and classes have docstrings. Docstrings are the
primary mechanism for in-code documentation and are used by help(), IDEs, and
documentation generators like Sphinx.

Skips:
  - Private functions/classes (starting with _)
  - Very short functions (< 3 lines of body statements)
  - __init__ and other dunders (covered by class docstring)

Uses the `ast` module for reliable parsing. Reports at INFO severity — this
is a suggestion, not a blocking violation.
"""

import ast
from pathlib import Path

from seedgo.models import CheckItem, CheckResult, Severity

PLUGIN_NAME = "docstring-coverage"
PLUGIN_DESCRIPTION = "Public functions and classes should have docstrings."
FILE_TYPES = ["*.py"]
PLUGIN_VERSION = "1.0.0"

# Minimum number of body statements to require a docstring
_MIN_BODY_LINES = 3


def check(file_path: str, config: dict | None = None) -> CheckResult:
    """Check a Python file for public functions and classes missing docstrings.

    Parses the file with ast and checks the first statement of each public
    function and class body. If the first statement is not a string literal,
    the docstring is considered missing.

    Args:
        file_path: Absolute path to the Python file to check.
        config: Optional plugin config dict (unused by this plugin).

    Returns:
        CheckResult with INFO-severity items for missing docstrings.
    """
    _ = config  # Part of plugin interface contract

    try:
        source = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return CheckResult(
            plugin=PLUGIN_NAME,
            passed=True,
            checks=[],
            file_path=file_path,
            metadata={"skipped": True, "reason": "file_read_error"},
        )

    if not source.strip():
        return CheckResult(
            plugin=PLUGIN_NAME,
            passed=True,
            checks=[CheckItem(
                name="docstring-coverage",
                passed=True,
                message="Empty file — nothing to check.",
                severity=Severity.INFO,
            )],
            file_path=file_path,
        )

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return CheckResult(
            plugin=PLUGIN_NAME,
            passed=True,
            checks=[],
            file_path=file_path,
            metadata={"skipped": True, "reason": "syntax_error"},
        )

    violations: list[CheckItem] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if _should_check_class(node):
                if not _has_docstring(node):
                    violations.append(CheckItem(
                        name="docstring-coverage",
                        passed=False,
                        message=(
                            f"Class `{node.name}` at line {node.lineno} "
                            f"is missing a docstring."
                        ),
                        severity=Severity.INFO,
                        line=node.lineno,
                        fix_hint=f'Add a docstring as the first statement: """Describe {node.name} here."""',
                    ))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _should_check_function(node):
                if not _has_docstring(node):
                    violations.append(CheckItem(
                        name="docstring-coverage",
                        passed=False,
                        message=(
                            f"Function `{node.name}` at line {node.lineno} "
                            f"is missing a docstring."
                        ),
                        severity=Severity.INFO,
                        line=node.lineno,
                        fix_hint=f'Add a docstring as the first statement: """Describe what {node.name} does."""',
                    ))

    if violations:
        # INFO violations don't cause overall failure
        passed = True
        checks = violations
    else:
        passed = True
        checks = [
            CheckItem(
                name="docstring-coverage",
                passed=True,
                message="All public functions and classes have docstrings.",
                severity=Severity.INFO,
            )
        ]

    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=passed,
        checks=checks,
        file_path=file_path,
        metadata={"violations_found": len(violations)},
    )


def _has_docstring(node: ast.AST) -> bool:
    """Return True if the node's body starts with a string literal (docstring)."""
    body = getattr(node, "body", [])
    if not body:
        return False
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return isinstance(first.value.value, str)
    return False


def _should_check_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if this function should be checked for a docstring."""
    # Skip private functions
    if node.name.startswith("_"):
        return False

    # Skip very short functions (fewer than _MIN_BODY_LINES body statements)
    # Count non-docstring statements
    body = node.body
    if len(body) < _MIN_BODY_LINES:
        return False

    return True


def _should_check_class(node: ast.ClassDef) -> bool:
    """Return True if this class should be checked for a docstring."""
    # Skip private classes
    if node.name.startswith("_"):
        return False
    return True
