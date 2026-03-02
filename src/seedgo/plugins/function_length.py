"""
Seed Go Plugin: function-length

Flags functions that exceed a configurable maximum line count. Long functions
are harder to read, test, and maintain. Breaking them into smaller, focused
functions improves code quality significantly.

This is a Seed Go differentiator: ruff has no function length rule. No
traditional linter checks this. Only architectural tools can enforce it.

Default max_lines: 50 (configurable via plugin config)
Config example:
    {
        "plugins": {
            "config": {
                "function-length": {"max_lines": 40}
            }
        }
    }

Uses the `ast` module's end_lineno attribute (Python 3.8+) to get accurate
function boundaries including all nested code.
"""

import ast
from pathlib import Path

from seedgo.models import CheckItem, CheckResult, Severity

PLUGIN_NAME = "function-length"
PLUGIN_DESCRIPTION = "Flag functions exceeding a configurable maximum line count."
FILE_TYPES = ["*.py"]
PLUGIN_VERSION = "1.0.0"

DEFAULT_MAX_LINES = 50


def check(file_path: str, config: dict | None = None) -> CheckResult:
    """Check a Python file for functions exceeding the maximum line count.

    Uses ast.parse() and end_lineno to measure function length precisely,
    including all nested statements, docstrings, and blank lines within the body.

    Args:
        file_path: Absolute path to the Python file to check.
        config: Optional dict with key "max_lines" (int). Defaults to 50.

    Returns:
        CheckResult with one WARNING CheckItem per oversized function found.
    """

    cfg = config or {}
    max_lines: int = int(cfg.get("max_lines", DEFAULT_MAX_LINES))

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
                name="function-length",
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

        start_line: int = node.lineno
        # end_lineno is available from Python 3.8+
        end_line: int = getattr(node, "end_lineno", node.lineno)
        func_lines: int = end_line - start_line + 1

        if func_lines > max_lines:
            func_name = node.name
            violations.append(
                CheckItem(
                    name="function-length",
                    passed=False,
                    message=(
                        f"Function `{func_name}` at line {start_line} "
                        f"is {func_lines} lines long (max: {max_lines})."
                    ),
                    severity=Severity.WARNING,
                    line=start_line,
                    fix_hint=(
                        f"Break `{func_name}` into smaller functions. "
                        f"Extract logical sections into helper functions."
                    ),
                )
            )

    if violations:
        passed = False
        checks = violations
    else:
        passed = True
        checks = [
            CheckItem(
                name="function-length",
                passed=True,
                message=f"All functions are within the {max_lines}-line limit.",
                severity=Severity.WARNING,
            )
        ]

    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=passed,
        checks=checks,
        file_path=file_path,
        metadata={
            "violations_found": len(violations),
            "max_lines": max_lines,
        },
    )
