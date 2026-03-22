# =================== AIPass ====================
# Name: test_coverage_check.py
# Description: Test Coverage Standards Checker Handler
# Version: 1.0.0
# Created: 2026-03-22
# Modified: 2026-03-22
# =============================================

"""
Test Coverage Standards Checker Handler

Branch-level checker that evaluates test coverage for a branch by:
- Discovering test files (tests/ directory and scattered test_*.py / *_test.py)
- Counting pytest-style test functions (def test_*)
- Mapping tested modules via import patterns
- Calculating module coverage (covered / total testable modules)

Extracted from devpulse test_scanner_v1 and wrapped as a seedgo checker.
"""

import re
from pathlib import Path

from aipass.seedgo.apps.handlers.json import json_handler

AUDIT_SCOPE = "branch_level"

# -- Directories to skip when scanning ----------------------------------------
SKIP_DIRS: set[str] = {
    "__pycache__", ".archive", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", ".venv", "venv", "node_modules", ".git",
    "site-packages", "logs", "tools", ".trinity", ".aipass",
    ".ai_mail.local", ".spawn", "backups", "reports", "docs",
    ".sorting_unprocessed",
}

# -- Test function pattern ----------------------------------------------------
RE_TEST_FUNC = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)", re.MULTILINE)

# -- Import patterns for mapping tests to modules ----------------------------
RE_IMPORT_FROM = re.compile(
    r"from\s+(?:aipass\.)?\w+\.apps\.(?:modules|handlers)[./]?([\w.]*)\s+import"
)
RE_IMPORT_DIRECT = re.compile(
    r"import\s+(?:aipass\.)?\w+\.apps\.(?:modules|handlers)[./]?([\w.]*)"
)


# =============================================
# BYPASS HELPER
# =============================================

def is_bypassed(
    file_path: str,
    standard: str,
    line: int | None = None,
    bypass_rules: list | None = None,
) -> bool:
    """Check if a violation should be bypassed."""
    if not bypass_rules:
        return False
    for rule in bypass_rules:
        if rule.get("standard") and rule.get("standard") != standard:
            continue
        rule_file = rule.get("file", "")
        if rule_file and rule_file not in file_path:
            continue
        rule_lines = rule.get("lines", [])
        if rule_lines and line is not None:
            if line in rule_lines:
                return True
        elif not rule_lines:
            return True
    return False


# =============================================
# FILE HELPERS
# =============================================

def _read_file_safe(path: Path) -> str:
    """Read a file, returning empty string on any error."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _should_skip_dir(name: str) -> bool:
    """Check if a directory name should be skipped."""
    return name in SKIP_DIRS or name.startswith(".")


# =============================================
# PHASE 1: DISCOVERY
# =============================================

def _find_test_files(branch_path: Path) -> list[Path]:
    """Find all test files for a branch.

    Looks in:
      - {branch_path}/tests/ (recursive)
      - Any file matching test_*.py or *_test.py elsewhere in the branch
    """
    test_files: list[Path] = []
    seen: set[Path] = set()

    # 1. Standard tests/ directory
    tests_dir = branch_path / "tests"
    if tests_dir.is_dir():
        for py_file in sorted(tests_dir.rglob("*.py")):
            if py_file.name in ("__init__.py", "conftest.py"):
                continue
            if "__pycache__" in py_file.parts:
                continue
            resolved = py_file.resolve()
            if resolved not in seen:
                seen.add(resolved)
                test_files.append(py_file)

    # 2. Scattered test_*.py or *_test.py anywhere in the branch
    for py_file in sorted(branch_path.rglob("*.py")):
        if any(_should_skip_dir(part) for part in py_file.relative_to(branch_path).parts):
            continue
        if py_file.name in ("__init__.py", "conftest.py"):
            continue
        if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
            resolved = py_file.resolve()
            if resolved not in seen:
                seen.add(resolved)
                test_files.append(py_file)

    return test_files


# =============================================
# PHASE 2: ANALYZE TEST FILES
# =============================================

def _analyze_test_file(test_file: Path) -> dict:
    """Analyze a single test file for test functions and module coverage.

    Returns:
        dict with keys: path, test_count, test_names, tested_modules
    """
    source = _read_file_safe(test_file)
    info: dict = {
        "path": test_file,
        "test_count": 0,
        "test_names": [],
        "tested_modules": set(),
    }

    if not source:
        return info

    # Count test functions
    for match in RE_TEST_FUNC.finditer(source):
        info["test_names"].append(match.group(1))
    info["test_count"] = len(info["test_names"])

    # Find which modules this test file covers via imports
    for match in RE_IMPORT_FROM.finditer(source):
        sub_path = match.group(1)
        if sub_path:
            first_segment = sub_path.split(".")[0]
            info["tested_modules"].add(first_segment)

    for match in RE_IMPORT_DIRECT.finditer(source):
        sub_path = match.group(1)
        if sub_path:
            first_segment = sub_path.split(".")[0]
            info["tested_modules"].add(first_segment)

    return info


# =============================================
# PHASE 3: COLLECT TESTABLE MODULES
# =============================================

def _collect_testable_modules(branch_path: Path) -> set[str]:
    """Collect module names from apps/modules/ and apps/handlers/.

    Returns set of module names:
    - apps/modules/*.py  -> file stem (e.g. "runner")
    - apps/handlers/*.py -> file stem (e.g. "audit")
    - apps/handlers/subdir/ -> directory name if it contains .py files
    """
    modules: set[str] = set()
    apps_dir = branch_path / "apps"
    if not apps_dir.is_dir():
        return modules

    # apps/modules/ -- flat .py files
    modules_dir = apps_dir / "modules"
    if modules_dir.is_dir():
        for item in sorted(modules_dir.iterdir()):
            if item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                modules.add(item.stem)

    # apps/handlers/ -- flat .py files OR subdirectories with .py files
    handlers_dir = apps_dir / "handlers"
    if handlers_dir.is_dir():
        for item in sorted(handlers_dir.iterdir()):
            if _should_skip_dir(item.name):
                continue
            if item.is_dir() and item.name != "__pycache__":
                has_py = any(
                    f.suffix == ".py" and f.name != "__init__.py"
                    for f in item.iterdir()
                    if f.is_file()
                )
                if has_py:
                    modules.add(item.name)
            elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                modules.add(item.stem)

    return modules


# =============================================
# PHASE 4: BRANCH-LEVEL CHECK
# =============================================

def check_branch(branch_path: str, bypass_rules: list | None = None) -> dict:
    """Run test coverage analysis on a branch.

    Args:
        branch_path: Path to branch root directory
        bypass_rules: Optional list of bypass rules

    Returns:
        dict: {passed, score, checks, standard: 'TEST_COVERAGE'}
    """
    checks: list[dict] = []
    bp = Path(branch_path)

    # Check if entire standard is bypassed
    if is_bypassed(branch_path, "test_coverage", bypass_rules=bypass_rules):
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
            "standard": "TEST_COVERAGE",
        }

    # Validate branch path exists
    if not bp.is_dir():
        return {
            "passed": False,
            "checks": [
                {
                    "name": "Branch exists",
                    "passed": False,
                    "message": f"Branch directory not found: {branch_path}",
                }
            ],
            "score": 0,
            "standard": "TEST_COVERAGE",
        }

    # Phase 1: Find test files
    test_files = _find_test_files(bp)

    # Phase 2: Analyze each test file
    total_tests = 0
    tested_modules: set[str] = set()
    for tf in test_files:
        info = _analyze_test_file(tf)
        total_tests += info["test_count"]
        tested_modules.update(info["tested_modules"])

    # Clear tested modules if no actual test functions found
    if total_tests == 0:
        tested_modules = set()

    # Phase 3: Collect all testable modules
    all_modules = _collect_testable_modules(bp)
    total_modules = len(all_modules)

    # Phase 4: Calculate coverage
    if total_modules > 0:
        covered_count = len(tested_modules & all_modules)
        coverage_pct = (covered_count / total_modules) * 100
    else:
        covered_count = 0
        coverage_pct = 0.0

    # -- Check 1: Test files exist --
    if test_files:
        checks.append({
            "name": "Test files",
            "passed": True,
            "message": f"Found {len(test_files)} test file(s)",
        })
    else:
        checks.append({
            "name": "Test files",
            "passed": False,
            "message": "No test files found (expected tests/ dir or test_*.py files)",
        })

    # -- Check 2: Test functions --
    if total_tests > 0:
        checks.append({
            "name": "Test functions",
            "passed": True,
            "message": f"Found {total_tests} test function(s)",
        })
    else:
        checks.append({
            "name": "Test functions",
            "passed": False,
            "message": "No test functions found (expected def test_* functions)",
        })

    # -- Check 3: Module coverage --
    # Lenient threshold: 25% -- most branches have no tests yet
    coverage_threshold = 25
    if total_modules == 0:
        checks.append({
            "name": "Module coverage",
            "passed": True,
            "message": "No testable modules found (nothing to test)",
        })
    elif coverage_pct >= coverage_threshold:
        checks.append({
            "name": "Module coverage",
            "passed": True,
            "message": f"{covered_count}/{total_modules} modules covered ({coverage_pct:.0f}%)",
        })
    else:
        checks.append({
            "name": "Module coverage",
            "passed": False,
            "message": (
                f"{covered_count}/{total_modules} modules covered ({coverage_pct:.0f}%) "
                f"-- below {coverage_threshold}% threshold"
            ),
        })

    # Calculate score
    # If branch has 0 testable modules, score = 100 (nothing to test)
    if total_modules == 0:
        score = 100
    else:
        score = int((covered_count / total_modules) * 100)

    # Overall pass at 75% score threshold
    overall_passed = score >= 75

    json_handler.log_operation(
        "check_completed",
        {
            "branch": branch_path,
            "score": score,
            "standard": "test_coverage",
            "total_tests": total_tests,
            "covered_modules": covered_count,
            "total_modules": total_modules,
        },
    )

    return {
        "passed": overall_passed,
        "score": score,
        "checks": checks,
        "standard": "TEST_COVERAGE",
    }
