"""
Skill Handler Standards Checker Handler

Validates skill handler contract compliance for AIPass skills.
Checks run() function signature, return annotations, print usage, get_actions().
"""

# =================== META ====================
# Name: skill_handler_check.py
# Description: Skill Handler Standards Checker Handler
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


import ast
from pathlib import Path
from typing import Dict, List, Optional


def _find_function(tree: ast.Module, name: str) -> Optional[ast.FunctionDef]:
    """Find a top-level function by name in an AST tree.

    Args:
        tree: Parsed AST module
        name: Function name to find

    Returns:
        FunctionDef node or None
    """
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _get_param_names(func_node: ast.FunctionDef) -> List[str]:
    """Extract parameter names from a function definition.

    Args:
        func_node: AST FunctionDef node

    Returns:
        List of parameter name strings (excludes 'self')
    """
    params = []
    for arg in func_node.args.args:
        if arg.arg != "self":
            params.append(arg.arg)
    return params


def _has_print_calls(tree: ast.Module) -> List[int]:
    """Find all print() calls in the AST and return their line numbers.

    Args:
        tree: Parsed AST module

    Returns:
        List of line numbers where print() is called
    """
    print_lines = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # print(...)
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                print_lines.append(node.lineno)
            # builtins.print(...)
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "print"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "builtins"
            ):
                print_lines.append(node.lineno)

    return print_lines


def _get_return_annotation(func_node: ast.FunctionDef) -> Optional[str]:
    """Get the return type annotation of a function as a string.

    Args:
        func_node: AST FunctionDef node

    Returns:
        String representation of return annotation, or None
    """
    if func_node.returns is None:
        return None

    if isinstance(func_node.returns, ast.Name):
        return func_node.returns.id
    elif isinstance(func_node.returns, ast.Constant):
        return str(func_node.returns.value)
    elif isinstance(func_node.returns, ast.Attribute):
        return func_node.returns.attr

    return "complex"


def check_skill_handler(handler_path: str) -> Dict:
    """
    Check if skill handler implements the standard contract

    Args:
        handler_path: Path to handler.py file

    Returns:
        dict: {
            'passed': bool,
            'checks': list,
            'score': float,
            'standard': str
        }
    """
    checks: List[Dict] = []
    path = Path(handler_path)

    # Validate file exists
    if not path.exists():
        return {
            "passed": False,
            "checks": [
                {
                    "name": "handler.py exists",
                    "passed": False,
                    "message": f"File not found: {handler_path}",
                }
            ],
            "score": 0.0,
            "standard": "SKILL_HANDLER",
        }

    # Parse the handler file
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        return {
            "passed": False,
            "checks": [
                {
                    "name": "Syntax valid",
                    "passed": False,
                    "message": f"Syntax error in handler: {e}",
                }
            ],
            "score": 0.0,
            "standard": "SKILL_HANDLER",
        }
    except (UnicodeDecodeError, OSError) as e:
        return {
            "passed": False,
            "checks": [
                {
                    "name": "File readable",
                    "passed": False,
                    "message": f"Error reading handler: {e}",
                }
            ],
            "score": 0.0,
            "standard": "SKILL_HANDLER",
        }

    # Check 1: handler.py has a run() function
    run_func = _find_function(tree, "run")
    if run_func is None:
        checks.append(
            {
                "name": "run() function",
                "passed": False,
                "message": "run() function not found at module level",
            }
        )
        # Cannot check parameters without run()
        passed_count = sum(1 for c in checks if c["passed"])
        total = len(checks)
        score = (passed_count / total * 100) if total > 0 else 0.0
        return {
            "passed": False,
            "checks": checks,
            "score": score,
            "standard": "SKILL_HANDLER",
        }

    checks.append(
        {
            "name": "run() function",
            "passed": True,
            "message": "run() function found",
        }
    )

    # Check 2: run() accepts action, args, config parameters
    param_names = _get_param_names(run_func)
    required_params = ["action", "args", "config"]
    missing_params = [p for p in required_params if p not in param_names]

    if not missing_params:
        checks.append(
            {
                "name": "run() parameters",
                "passed": True,
                "message": f"run() accepts: {', '.join(param_names)}",
            }
        )
    else:
        checks.append(
            {
                "name": "run() parameters",
                "passed": False,
                "message": f"run() missing parameters: {', '.join(missing_params)} (has: {', '.join(param_names)})",
            }
        )

    # Check 3: run() return type annotation is dict (if present)
    return_annotation = _get_return_annotation(run_func)
    if return_annotation is None:
        checks.append(
            {
                "name": "run() return annotation",
                "passed": True,
                "message": "No return annotation (acceptable - annotation is optional)",
            }
        )
    elif return_annotation.lower() == "dict":
        checks.append(
            {
                "name": "run() return annotation",
                "passed": True,
                "message": "run() -> dict (correct)",
            }
        )
    else:
        checks.append(
            {
                "name": "run() return annotation",
                "passed": False,
                "message": f"run() -> {return_annotation} (expected dict)",
            }
        )

    # Check 4: No print() calls in handler code
    print_lines = _has_print_calls(tree)
    if print_lines:
        lines_str = ", ".join(str(ln) for ln in print_lines[:5])
        suffix = f" (and {len(print_lines) - 5} more)" if len(print_lines) > 5 else ""
        checks.append(
            {
                "name": "No print() calls",
                "passed": False,
                "message": f"print() found on lines: {lines_str}{suffix} (handlers should return dicts, not print)",
            }
        )
    else:
        checks.append(
            {
                "name": "No print() calls",
                "passed": True,
                "message": "No print() calls found (handlers return structured data)",
            }
        )

    # Check 5: get_actions() function exists (WARNING level - still passes)
    get_actions_func = _find_function(tree, "get_actions")
    if get_actions_func is not None:
        checks.append(
            {
                "name": "get_actions() function",
                "passed": True,
                "message": "get_actions() found (enables introspection)",
            }
        )
    else:
        # WARNING level - counts as passed but notes the recommendation
        checks.append(
            {
                "name": "get_actions() function",
                "passed": True,
                "message": "WARNING: get_actions() not found (recommended for discoverability)",
            }
        )

    # Calculate score
    passed_count = sum(1 for c in checks if c["passed"])
    total = len(checks)
    score = (passed_count / total * 100) if total > 0 else 0.0

    return {
        "passed": score >= 75,
        "checks": checks,
        "score": score,
        "standard": "SKILL_HANDLER",
    }
