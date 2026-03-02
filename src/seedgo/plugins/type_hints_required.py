"""
Seed Go Plugin: type-hints-required

Checks that public functions have return type annotations. Type hints improve
IDE support, catch bugs early, and make code self-documenting. This plugin
targets the most impactful annotation: the return type.

Skips:
  - Private functions (starting with _ or __)
  - __init__, __str__, __repr__, and other dunder methods
  - Functions that are very short (< 2 lines) — likely trivial wrappers

Uses the `ast` module for reliable parsing rather than fragile regex, so it
correctly handles multi-line signatures, decorators, and nested functions.
"""

import ast
from pathlib import Path

from seedgo.models import CheckItem, CheckResult, Severity

PLUGIN_NAME = "type-hints-required"
PLUGIN_DESCRIPTION = "Public functions must have return type annotations."
FILE_TYPES = ["*.py"]
PLUGIN_VERSION = "1.0.0"

# Dunder methods commonly exempted from return type requirements
_EXEMPT_DUNDERS = {
    "__init__",
    "__str__",
    "__repr__",
    "__len__",
    "__bool__",
    "__hash__",
    "__del__",
    "__enter__",
    "__exit__",
    "__iter__",
    "__next__",
    "__contains__",
    "__getitem__",
    "__setitem__",
    "__delitem__",
    "__call__",
}


def check(file_path: str, config: dict | None = None) -> CheckResult:
    """Check a Python file for public functions missing return type annotations.

    Parses the file with the ast module and inspects all function definitions.
    Only public, non-exempted functions are checked.

    Args:
        file_path: Absolute path to the Python file to check.
        config: Optional plugin config dict (unused by this plugin).

    Returns:
        CheckResult with one CheckItem per violation found, or a passing item
        if all public functions have return type annotations.
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
                name="type-hints-required",
                passed=True,
                message="Empty file — no functions to check.",
                severity=Severity.WARNING,
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
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        func_name = node.name

        # Skip private functions (starting with _)
        if func_name.startswith("_"):
            continue

        # Skip exempt dunder methods
        if func_name in _EXEMPT_DUNDERS:
            continue

        # Skip very short functions (< 2 statements — likely trivial)
        if len(node.body) < 2:
            # Check if it's just a pass or docstring
            if _is_trivial_body(node.body):
                continue

        # Check for missing return annotation
        if node.returns is None:
            # Estimate function length from source lines
            violations.append(
                CheckItem(
                    name="type-hints-required",
                    passed=False,
                    message=(
                        f"Public function `{func_name}` at line {node.lineno} "
                        f"missing return type annotation."
                    ),
                    severity=Severity.WARNING,
                    line=node.lineno,
                    fix_hint=f"Add `-> ReturnType` before the colon: `def {func_name}(...) -> ReturnType:`",
                )
            )

    if violations:
        passed = False
        checks = violations
    else:
        passed = True
        checks = [
            CheckItem(
                name="type-hints-required",
                passed=True,
                message="All public functions have return type annotations.",
                severity=Severity.WARNING,
            )
        ]

    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=passed,
        checks=checks,
        file_path=file_path,
        metadata={"violations_found": len(violations)},
    )


def _is_trivial_body(body: list) -> bool:
    """Return True if a function body is trivially simple (pass, ellipsis, or docstring only)."""
    if len(body) == 0:
        return True
    if len(body) == 1:
        stmt = body[0]
        # pass statement
        if isinstance(stmt, ast.Pass):
            return True
        # ... (ellipsis)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            if stmt.value.value is ...:
                return True
            # String = docstring
            if isinstance(stmt.value.value, str):
                return True
    return False
