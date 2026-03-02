"""
Seed Go Plugin: file-structure

Enforces directory conventions for Python projects. This is Seed Go's killer
feature — no traditional linter (ruff, pylint, flake8) checks WHERE files are
placed. They only check file contents.

Checks performed:
  a. Test files (test_*.py or *_test.py) should be in a tests/ directory,
     not placed directly at the project root.
  b. Python source files should not live directly at the project root
     (except for well-known root-level files like setup.py, conftest.py).
  c. Source packages (directories with .py files) should have __init__.py.

Config example:
    {
        "plugins": {
            "config": {
                "file-structure": {
                    "allowed_root_files": ["setup.py", "conftest.py", "manage.py"]
                }
            }
        }
    }

Note: This plugin receives one file at a time from the runner. It checks the
given file's placement relative to the project root, which it infers from the
path. For checks that require directory context (like __init__.py presence),
it inspects the file's parent directory.
"""

from pathlib import Path

from seedgo.models import CheckItem, CheckResult, Severity

PLUGIN_NAME = "file-structure"
PLUGIN_DESCRIPTION = "Enforce directory conventions: test placement, root files, package __init__.py."
FILE_TYPES = ["*.py"]
PLUGIN_VERSION = "1.0.0"

# Files commonly allowed at the project root
DEFAULT_ALLOWED_ROOT_FILES = [
    "setup.py",
    "conftest.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "fabfile.py",
    "noxfile.py",
    "tasks.py",
]

# Directories that are considered "test directories" — test files are OK here
TEST_DIR_NAMES = {"tests", "test", "testing", "spec"}

# Directories that should never trigger root-file violations even if named differently
SKIP_DIR_NAMES = {
    ".seedgo",
    ".git",
    "__pycache__",
    "node_modules",
    ".tox",
    ".venv",
    "venv",
    "env",
    ".eggs",
    "dist",
    "build",
}


def check(file_path: str, config: dict | None = None) -> CheckResult:
    """Check a Python file's placement against project directory conventions.

    Inspects the file path relative to the inferred project root and flags
    violations of standard Python project structure conventions.

    Args:
        file_path: Absolute path to the Python file to check.
        config: Optional dict. Supported keys:
                  - "allowed_root_files": list[str] of filenames OK at root.

    Returns:
        CheckResult with ERROR-severity items for structural violations.
    """

    cfg = config or {}
    allowed_root_files: list[str] = cfg.get("allowed_root_files", DEFAULT_ALLOWED_ROOT_FILES)

    path = Path(file_path).resolve()

    # Skip files that don't exist (e.g., deleted during scan)
    if not path.exists():
        return CheckResult(
            plugin=PLUGIN_NAME,
            passed=True,
            checks=[],
            file_path=file_path,
            metadata={"skipped": True, "reason": "file_not_found"},
        )

    # Skip files in ignored directories
    for part in path.parts:
        if part in SKIP_DIR_NAMES:
            return CheckResult(
                plugin=PLUGIN_NAME,
                passed=True,
                checks=[],
                file_path=file_path,
                metadata={"skipped": True, "reason": "excluded_directory"},
            )

    violations: list[CheckItem] = []
    file_name = path.name
    parent_dir = path.parent
    parent_name = parent_dir.name

    # -------------------------------------------------------------------
    # Infer project root: walk up to find a known project root marker.
    # Markers: .seedgo/, setup.py, pyproject.toml, setup.cfg, .git/
    # -------------------------------------------------------------------
    project_root = _find_project_root(path)

    if project_root is None:
        # Cannot determine project root — skip structural checks
        return CheckResult(
            plugin=PLUGIN_NAME,
            passed=True,
            checks=[],
            file_path=file_path,
            metadata={"skipped": True, "reason": "no_project_root_found"},
        )

    try:
        rel_path = path.relative_to(project_root)
    except ValueError:
        return CheckResult(
            plugin=PLUGIN_NAME,
            passed=True,
            checks=[],
            file_path=file_path,
            metadata={"skipped": True, "reason": "path_outside_project_root"},
        )

    rel_parts = rel_path.parts  # e.g., ("src", "mypackage", "module.py")
    is_at_root = len(rel_parts) == 1  # file is directly in project root

    # -------------------------------------------------------------------
    # Check A: Test files should be in a tests/ directory
    # -------------------------------------------------------------------
    is_test_file = file_name.startswith("test_") or file_name.endswith("_test.py")

    if is_test_file:
        # Check if ANY parent directory (relative to project root) is a test dir
        parent_dirs = {part.lower() for part in rel_parts[:-1]}
        in_test_dir = bool(parent_dirs & TEST_DIR_NAMES)

        if not in_test_dir:
            violations.append(CheckItem(
                name="test-file-placement",
                passed=False,
                message=(
                    f"Test file `{rel_path}` is not inside a tests/ directory. "
                    f"Test files should be grouped under tests/ for discoverability."
                ),
                severity=Severity.ERROR,
                line=None,
                fix_hint=f"Move `{file_name}` into a `tests/` directory.",
            ))

    # -------------------------------------------------------------------
    # Check B: Non-special Python files should not be at project root
    # -------------------------------------------------------------------
    if is_at_root and not is_test_file:
        if file_name not in allowed_root_files and not file_name.startswith("_"):
            violations.append(CheckItem(
                name="root-python-file",
                passed=False,
                message=(
                    f"Python file `{file_name}` is at the project root. "
                    f"Source files should be inside a package directory (e.g., src/)."
                ),
                severity=Severity.ERROR,
                line=None,
                fix_hint=(
                    f"Move `{file_name}` into a source package directory, "
                    f"or add it to `allowed_root_files` in plugin config."
                ),
            ))

    # -------------------------------------------------------------------
    # Check C: Source packages should have __init__.py
    # -------------------------------------------------------------------
    # Only check non-root, non-test, non-hidden directories
    if not is_at_root and not is_test_file:
        # Check if the file's parent directory is a Python package
        # (i.e., contains .py files but no __init__.py)
        if _is_missing_init(parent_dir, project_root):
            violations.append(CheckItem(
                name="missing-init-py",
                passed=False,
                message=(
                    f"Directory `{parent_name}/` contains Python files but has no `__init__.py`. "
                    f"Add `__init__.py` to make it a proper Python package."
                ),
                severity=Severity.ERROR,
                line=None,
                fix_hint=f"Create an empty `{parent_dir / '__init__.py'}` file.",
            ))

    if violations:
        passed = False
        checks = violations
    else:
        passed = True
        checks = [
            CheckItem(
                name="file-structure",
                passed=True,
                message=f"File `{rel_path}` follows project structure conventions.",
                severity=Severity.ERROR,
            )
        ]

    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=passed,
        checks=checks,
        file_path=file_path,
        metadata={"violations_found": len(violations)},
    )


def _find_project_root(file_path: Path) -> Path | None:
    """Walk up from file_path to find the project root.

    Looks for markers: .seedgo/, .git/, pyproject.toml, setup.py, setup.cfg.

    Args:
        file_path: Absolute path to a file within the project.

    Returns:
        Path to the project root directory, or None if not found.
    """
    markers = {".seedgo", ".git", "pyproject.toml", "setup.py", "setup.cfg"}
    current = file_path.parent

    for directory in [current, *current.parents]:
        for marker in markers:
            if (directory / marker).exists():
                return directory

    return None


def _is_missing_init(directory: Path, project_root: Path) -> bool:
    """Return True if a directory has Python files but no __init__.py.

    Only checks non-hidden, non-special directories that are inside the
    project root (to avoid checking installed packages, virtualenvs, etc.).

    Args:
        directory: Directory to check.
        project_root: Project root — only check directories within this.

    Returns:
        True if __init__.py is absent and the directory has .py source files.
    """
    # Skip if directory is not within project root
    try:
        directory.relative_to(project_root)
    except ValueError:
        return False

    # Skip special/hidden/generated directories
    dir_name = directory.name
    if dir_name.startswith(".") or dir_name.startswith("_") or dir_name in SKIP_DIR_NAMES:
        return False

    # Skip test directories — they typically don't need __init__.py
    if dir_name.lower() in TEST_DIR_NAMES:
        return False

    # Check for __init__.py
    if (directory / "__init__.py").exists():
        return False

    # Check if there are any .py source files (that aren't __init__.py)
    py_files = [
        f for f in directory.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
    ]

    return len(py_files) > 0
