# =================== AIPass ====================
# Name: subcommand_help_check.py
# Description: Subcommand Help Standards Checker Handler
# Version: 1.0.0
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""Subcommand Help Standards Checker Handler.

Validates that branch entry points handle <cmd> --help by showing
subcommand-specific help — never executing the command, never silently
falling back to top-level help.

THE CONTRACT:
  Every entry point that routes subcommands must intercept --help in the
  remaining args (after command extraction) BEFORE dispatching to handlers.

WHAT PASSES (any one of):
  a) Explicit subcommand --help guard on remaining args
  b) argparse with parse_known_args (absorbs --help from any position)

Only entry point files are checked (apps/{branch}.py).
"""

import ast
from pathlib import Path
from typing import Dict

from aipass.prax import logger
from aipass.seedgo.apps.handlers.bypass.utils import is_bypassed
from aipass.seedgo.apps.handlers.json import json_handler

AUDIT_SCOPE = "entry_point"

_TOPLEVEL_ARG_NAMES = frozenset({"args", "argv"})

_HELP_STRINGS = frozenset({"--help", "-h"})


_ENTRY_NAMES = {"main", "handle_command"}


def _called_names(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return names of functions called directly from func_node's body."""
    names: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def _find_entry_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return entry functions and their direct delegates from the module top level."""
    all_funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_funcs[node.name] = node

    targets: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for name in _ENTRY_NAMES:
        if name not in all_funcs:
            continue
        func = all_funcs[name]
        targets.append(func)
        for called in _called_names(func):
            if called in all_funcs and called.startswith("_") and called not in _ENTRY_NAMES:
                targets.append(all_funcs[called])
    return targets


def _has_argparse_known_args(func_node: ast.AST) -> bool:
    """Return True if the function uses argparse parse_known_args."""
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "parse_known_args":
            return True
    return False


def _compare_has_help_string(node: ast.Compare) -> bool:
    """Return True if a Compare node involves a --help string constant."""
    for part in [node.left, *node.comparators]:
        if isinstance(part, ast.Constant) and part.value in _HELP_STRINGS:
            return True
        if isinstance(part, (ast.List, ast.Tuple, ast.Set)):
            for elt in part.elts:
                if isinstance(elt, ast.Constant) and elt.value in _HELP_STRINGS:
                    return True
    return False


def _is_subscript_on_name(node: ast.expr, names: frozenset[str]) -> bool:
    """Return True if node is name[N] where name is in the given set."""
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.value.id in names
    return False


def _is_toplevel_help_check(node: ast.Compare) -> bool:
    """Return True if this is a top-level args[0] --help check."""
    return _is_subscript_on_name(node.left, _TOPLEVEL_ARG_NAMES)


def _is_help_in_nonargs_var(node: ast.Compare) -> bool:
    """Check for '"--help" in some_var' where some_var is not args/argv."""
    if not isinstance(node.left, ast.Constant) or node.left.value not in _HELP_STRINGS:
        return False
    if not any(isinstance(op, ast.In) for op in node.ops):
        return False
    return any(isinstance(c, ast.Name) and c.id not in _TOPLEVEL_ARG_NAMES for c in node.comparators)


def _is_nonargs_subscript_help(node: ast.Compare) -> bool:
    """Check for 'remaining[0] in ["--help", ...]' where remaining != args."""
    left = node.left
    if not isinstance(left, ast.Subscript) or not isinstance(left.value, ast.Name):
        return False
    return left.value.id not in _TOPLEVEL_ARG_NAMES


def _has_subcommand_help_guard(func_node: ast.AST, func_name: str = "") -> bool:
    """Return True if the function has a subcommand-level --help check.

    Detects patterns like:
      remaining_args[0] in ["--help", "-h"]
      "--help" in remaining_args
      rest[0] == "--help"
    where the variable is NOT the raw args/argv.

    In handle_command(), args IS the subcommand args (not full argv),
    so args[0] checks there count as subcommand guards.
    """
    args_are_subcommand = func_name == "handle_command"
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Compare):
            continue
        if not _compare_has_help_string(node):
            continue
        if _is_toplevel_help_check(node):
            if args_are_subcommand:
                return True
            continue
        if _is_subscript_on_name(node.left, _TOPLEVEL_ARG_NAMES):
            if args_are_subcommand:
                return True
            continue
        if _is_help_in_nonargs_var(node):
            return True
        if _is_nonargs_subscript_help(node):
            return True
        if isinstance(node.left, ast.Name) and node.left.id not in _TOPLEVEL_ARG_NAMES:
            return True
    return False


def check_module(module_path: str, bypass_rules: list | None = None) -> Dict:
    """Check if entry point handles subcommand --help."""
    path = Path(module_path)

    if is_bypassed(module_path, "subcommand_help", bypass_rules=bypass_rules):
        return {
            "passed": True,
            "checks": [{"name": "Bypassed", "passed": True, "message": "Standard bypassed via .seedgo/bypass.json"}],
            "score": 100,
            "standard": "SUBCOMMAND_HELP",
        }

    if not path.exists():
        return {
            "passed": False,
            "checks": [{"name": "File exists", "passed": False, "message": f"File not found: {module_path}"}],
            "score": 0,
            "standard": "SUBCOMMAND_HELP",
        }

    if path.parent.name != "apps":
        return {
            "passed": True,
            "checks": [{"name": "Subcommand help", "passed": True, "message": "Not an entry point (skipped)"}],
            "score": 100,
            "standard": "SUBCOMMAND_HELP",
        }

    try:
        source = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.info("Cannot read %s: %s", path, e)
        return {
            "passed": False,
            "checks": [{"name": "File readable", "passed": False, "message": f"Error reading file: {e}"}],
            "score": 0,
            "standard": "SUBCOMMAND_HELP",
        }

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        logger.info("Skipped %s: SyntaxError during parse", path)
        return {
            "passed": False,
            "checks": [{"name": "File parseable", "passed": False, "message": f"Syntax error: {e}"}],
            "score": 0,
            "standard": "SUBCOMMAND_HELP",
        }

    entry_funcs = _find_entry_functions(tree)
    if not entry_funcs:
        return {
            "passed": True,
            "checks": [
                {
                    "name": "Subcommand help",
                    "passed": True,
                    "message": "No main/handle_command entry function found (skipped)",
                }
            ],
            "score": 100,
            "standard": "SUBCOMMAND_HELP",
        }

    for func in entry_funcs:
        if _has_argparse_known_args(func):
            json_handler.log_operation(
                "check_completed",
                {"file": str(module_path), "score": 100, "standard": "subcommand_help"},
            )
            return {
                "passed": True,
                "checks": [
                    {
                        "name": "Subcommand help",
                        "passed": True,
                        "message": f"argparse parse_known_args in {func.name}() absorbs --help",
                    }
                ],
                "score": 100,
                "standard": "SUBCOMMAND_HELP",
            }

        if _has_subcommand_help_guard(func, func.name):
            json_handler.log_operation(
                "check_completed",
                {"file": str(module_path), "score": 100, "standard": "subcommand_help"},
            )
            return {
                "passed": True,
                "checks": [
                    {
                        "name": "Subcommand help",
                        "passed": True,
                        "message": f"Subcommand --help guard found in {func.name}()",
                    }
                ],
                "score": 100,
                "standard": "SUBCOMMAND_HELP",
            }

    func_names = ", ".join(f.name for f in entry_funcs)
    json_handler.log_operation(
        "check_completed",
        {"file": str(module_path), "score": 0, "standard": "subcommand_help"},
    )
    return {
        "passed": False,
        "checks": [
            {
                "name": "Subcommand help",
                "passed": False,
                "message": (
                    f"No subcommand --help guard in {func_names}() — "
                    "<cmd> --help will execute the command or fall to top-level help"
                ),
            }
        ],
        "score": 0,
        "standard": "SUBCOMMAND_HELP",
    }
