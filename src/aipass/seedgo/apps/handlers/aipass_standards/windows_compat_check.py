# =================== AIPass ====================
# Name: windows_compat_check.py
# Description: Windows Compatibility Standards Checker Handler
# Version: 1.1.0
# Created: 2026-05-10
# Modified: 2026-05-14
# =============================================

"""Windows Compatibility Standards Checker Handler."""

import ast
from pathlib import Path
from typing import Dict

from aipass.prax import logger
from aipass.seedgo.apps.handlers.bypass.utils import is_bypassed
from aipass.seedgo.apps.handlers.json import json_handler

AUDIT_SCOPE = "all_files"

_POSIX_ONLY_MODULES = frozenset({"fcntl", "pwd", "grp", "termios", "resource"})

_POSIX_ONLY_OS_ATTRS = frozenset({"WNOHANG"})

_POSIX_ONLY_OS_CALLS = frozenset({"fork", "setpgid", "killpg", "getpgid", "waitpid"})

_GUARDED_EXCEPT_TYPES = frozenset(
    {
        "ImportError",
        "ModuleNotFoundError",
        "OSError",
        "PermissionError",
        "ProcessLookupError",
    }
)

_TEST_POSIX_CALLS: dict[tuple[str, str], str] = {
    ("os", "chmod"): "os.chmod() — Windows ignores permission bits",
    ("os", "symlink"): "os.symlink() — Windows needs privileges",
    ("os", "getuid"): "os.getuid() — not available on Windows",
    ("os", "getgid"): "os.getgid() — not available on Windows",
    ("os", "chown"): "os.chown() — not available on Windows",
    ("stat", "S_IMODE"): "stat.S_IMODE() — Unix permission assertion",
}


def _is_platform_guard(node: ast.expr) -> bool:
    """Return True if the test expression is a sys.platform or os.name comparison."""
    if isinstance(node, ast.Compare):
        left = node.left
        if isinstance(left, ast.Attribute) and isinstance(left.value, ast.Name):
            if left.value.id == "sys" and left.attr == "platform":
                return True
            if left.value.id == "os" and left.attr == "name":
                return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "hasattr":
            return True
    if isinstance(node, ast.BoolOp):
        return any(_is_platform_guard(v) for v in node.values)
    return False


def _collect_child_linenos(node: ast.AST) -> set[int]:
    """Walk all descendants and return line numbers where present."""
    lines: set[int] = set()
    for child in ast.walk(node):
        lineno = getattr(child, "lineno", None)
        if lineno is not None:
            lines.add(lineno)
    return lines


def _handler_catches_guarded_type(handler: ast.ExceptHandler) -> bool:
    """Return True if the except handler catches an import/OS error type."""
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name):
        return handler.type.id in _GUARDED_EXCEPT_TYPES
    if isinstance(handler.type, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id in _GUARDED_EXCEPT_TYPES for elt in handler.type.elts)
    return False


def _lines_in_guarded_blocks(tree: ast.Module) -> set[int]:
    """Collect line numbers inside platform guard blocks or try/except ImportError."""
    guarded: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_platform_guard(node.test):
            guarded.update(_collect_child_linenos(node))
        if isinstance(node, ast.Try):
            if any(_handler_catches_guarded_type(h) for h in node.handlers):
                guarded.update(_collect_child_linenos(node))

    return guarded


def _check_import_node(node: ast.Import, guarded: set[int]) -> list[tuple[int, str]]:
    """Check a single Import node for POSIX-only module names."""
    return [
        (node.lineno, f"import {alias.name}")
        for alias in node.names
        if alias.name in _POSIX_ONLY_MODULES and node.lineno not in guarded
    ]


def _find_posix_import_violations(tree: ast.Module, guarded: set[int]) -> list[tuple[int, str]]:
    """Find unguarded imports of POSIX-only modules."""
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(_check_import_node(node, guarded))
        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                continue
            if node.module.split(".")[0] in _POSIX_ONLY_MODULES and node.lineno not in guarded:
                violations.append((node.lineno, f"from {node.module} import ..."))
    return violations


def _find_posix_constant_violations(tree: ast.Module, guarded: set[int]) -> list[tuple[int, str]]:
    """Find unguarded references to POSIX-only constants like os.WNOHANG."""
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        if node.value.id == "os" and node.attr in _POSIX_ONLY_OS_ATTRS:
            if node.lineno not in guarded:
                violations.append((node.lineno, f"os.{node.attr}"))
        if node.value.id == "signal" and node.attr == "SIGPIPE":
            if node.lineno not in guarded:
                violations.append((node.lineno, "signal.SIGPIPE"))
    return violations


def _find_posix_call_violations(tree: ast.Module, guarded: set[int]) -> list[tuple[int, str]]:
    """Find unguarded calls to POSIX-only os functions."""
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
            continue
        if func.value.id == "os" and func.attr in _POSIX_ONLY_OS_CALLS:
            if node.lineno not in guarded:
                violations.append((node.lineno, f"os.{func.attr}()"))
    return violations


def _find_os_kill_violations(tree: ast.Module, guarded: set[int]) -> list[tuple[int, str]]:
    """Find os.kill() calls not inside a try/except that catches OSError."""
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
            and func.attr == "kill"
            and node.lineno not in guarded
        ):
            violations.append((node.lineno, "os.kill() without OSError handling"))
    return violations


def _is_test_file(path: Path) -> bool:
    return "tests" in path.parts or path.name.startswith("test_") or path.name.endswith("_test.py")


def _is_pytest_mark(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "mark"
        and isinstance(node.value, ast.Name)
        and node.value.id == "pytest"
    )


def _references_platform(node: ast.expr) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
            if (child.value.id == "sys" and child.attr == "platform") or (
                child.value.id == "os" and child.attr == "name"
            ):
                return True
    return False


def _has_platform_skipif(decorators: list[ast.expr]) -> bool:
    for dec in decorators:
        if isinstance(dec, ast.Attribute) and dec.attr == "skip" and _is_pytest_mark(dec.value):
            return True
        if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
            continue
        func = dec.func
        if func.attr == "skip" and _is_pytest_mark(func.value):
            return True
        if func.attr == "skipif" and _is_pytest_mark(func.value):
            if any(_references_platform(arg) for arg in dec.args):
                return True
    return False


def _match_posix_call(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if not isinstance(node.func.value, ast.Name):
        return None
    key = (node.func.value.id, node.func.attr)
    return _TEST_POSIX_CALLS.get(key)


def _match_stat_constant(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
        return None
    if node.value.id == "stat" and node.attr.startswith("S_I") and node.attr != "S_IMODE":
        return f"stat.{node.attr} — Unix permission constant"
    return None


def _scan_test_body(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    guarded: set[int],
    violations: list[tuple[int, str]],
) -> None:
    seen_lines: set[int] = set()
    for node in ast.walk(func_node):
        lineno = getattr(node, "lineno", None)
        if lineno is None or lineno in guarded or lineno in seen_lines:
            continue

        desc = _match_posix_call(node) or _match_stat_constant(node)
        if desc:
            violations.append((lineno, desc))
            seen_lines.add(lineno)


def _collect_unguarded_tests(
    parent: ast.Module | ast.ClassDef,
    class_skipif: bool = False,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    results: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.iter_child_nodes(parent):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if not class_skipif and not _has_platform_skipif(node.decorator_list):
            results.append(node)
    return results


def _find_test_platform_violations(
    tree: ast.Module,
    guarded: set[int],
) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    targets: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    targets.extend(_collect_unguarded_tests(tree))
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            targets.extend(_collect_unguarded_tests(node, _has_platform_skipif(node.decorator_list)))

    for func in targets:
        _scan_test_body(func, guarded, violations)

    return violations


def check_module(module_path: str, bypass_rules: list | None = None) -> Dict:
    """Check a Python file for Windows-incompatible patterns."""
    path = Path(module_path)

    if is_bypassed(module_path, "windows_compat", bypass_rules=bypass_rules):
        return {
            "passed": True,
            "checks": [
                {
                    "name": "Bypassed",
                    "passed": True,
                    "message": "Standard bypassed via .seedgo/bypass.json",
                }
            ],
            "score": 100,
            "standard": "WINDOWS_COMPAT",
        }

    if path.suffix != ".py" or path.name == "__init__.py":
        return {
            "passed": True,
            "checks": [
                {
                    "name": "Windows compat",
                    "passed": True,
                    "message": "File skipped (non-target)",
                }
            ],
            "score": 100,
            "standard": "WINDOWS_COMPAT",
        }

    if not path.exists():
        return {
            "passed": False,
            "checks": [
                {
                    "name": "File exists",
                    "passed": False,
                    "message": f"File not found: {module_path}",
                }
            ],
            "score": 0,
            "standard": "WINDOWS_COMPAT",
        }

    try:
        source = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.info("Cannot read %s: %s", path, e)
        return {
            "passed": False,
            "checks": [
                {
                    "name": "File readable",
                    "passed": False,
                    "message": f"Error reading file: {e}",
                }
            ],
            "score": 0,
            "standard": "WINDOWS_COMPAT",
        }

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        logger.info("Skipped %s: SyntaxError during parse", path)
        return {
            "passed": False,
            "checks": [
                {
                    "name": "File parseable",
                    "passed": False,
                    "message": f"Syntax error: {e}",
                }
            ],
            "score": 0,
            "standard": "WINDOWS_COMPAT",
        }

    guarded = _lines_in_guarded_blocks(tree)

    all_violations: list[tuple[int, str]] = []
    all_violations.extend(_find_posix_import_violations(tree, guarded))
    all_violations.extend(_find_posix_constant_violations(tree, guarded))
    all_violations.extend(_find_posix_call_violations(tree, guarded))
    all_violations.extend(_find_os_kill_violations(tree, guarded))

    if _is_test_file(path):
        all_violations.extend(_find_test_platform_violations(tree, guarded))

    non_bypassed = [
        (ln, desc) for ln, desc in all_violations if not is_bypassed(module_path, "windows_compat", ln, bypass_rules)
    ]
    non_bypassed.sort(key=lambda x: x[0])

    checks = []
    violation_count = len(non_bypassed)

    if violation_count == 0:
        checks.append(
            {
                "name": "Windows compat",
                "passed": True,
                "message": "No unguarded POSIX-only patterns found",
            }
        )
    else:
        previews = [f"L{ln}: {desc}" for ln, desc in non_bypassed[:3]]
        preview_str = "; ".join(previews)
        suffix = f" (and {violation_count - 3} more)" if violation_count > 3 else ""
        checks.append(
            {
                "name": "Windows compat",
                "passed": False,
                "message": f"{violation_count} unguarded POSIX pattern(s): {preview_str}{suffix}",
            }
        )

    passed_checks = sum(1 for c in checks if c["passed"])
    total_checks = len(checks)
    score = int((passed_checks / total_checks) * 100) if total_checks > 0 else 0
    overall_passed = score >= 75

    json_handler.log_operation(
        "check_completed",
        {"file": str(module_path), "score": score, "standard": "windows_compat"},
    )
    return {
        "passed": overall_passed,
        "checks": checks,
        "score": score,
        "standard": "WINDOWS_COMPAT",
    }
