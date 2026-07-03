# =================== AIPass ====================
# Name: utils.py
# Description: Shared bypass checking utility for standards checkers
# Version: 1.0.0
# Created: 2026-04-27
# Modified: 2026-04-27
# =============================================

"""Shared bypass checking utility for standards checkers."""

from pathlib import Path

from aipass.seedgo.apps.handlers.json import json_handler


def is_bypassed(
    file_path: str,
    standard: str,
    line: int | None = None,
    bypass_rules: list | None = None,
    name: str | None = None,
) -> bool:
    """Check if a violation should be bypassed.

    Args:
        file_path: Path to the file being checked
        standard: Standard name (e.g., 'cli', 'imports')
        line: Optional specific line number of the violation
        bypass_rules: List of bypass rules from .seedgo/bypass.json
        name: Optional function/symbol name for name-scoped bypasses

    Returns:
        True if this violation should be bypassed
    """
    if not bypass_rules:
        return False
    # Normalize to forward slashes for cross-platform matching
    file_path_posix = Path(file_path).as_posix()
    for rule in bypass_rules:
        if rule.get("standard") and rule.get("standard") != standard:
            continue
        rule_file = rule.get("file", "")
        if rule_file and rule_file not in file_path_posix:
            continue
        functions = rule.get("functions")
        if functions and name is not None:
            if name not in functions:
                continue
        elif rule.get("lines") and line is not None:
            if line not in rule["lines"]:
                continue
        json_handler.log_operation(
            "bypass_matched",
            {
                "file": file_path,
                "standard": standard,
                "line": line,
                "name": name,
                "rule_file": rule_file,
            },
        )
        return True
    return False
