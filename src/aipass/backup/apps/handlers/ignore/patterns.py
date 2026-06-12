# =================== AIPass ====================
# Name: patterns.py
# Description: Ignore pattern loader and path matcher
# Version: 1.0.0
# Created: 2026-04-17
# Modified: 2026-06-12
# =============================================

"""Ignore patterns handler.

Loads .backupignore from the project root and matches paths against
glob-style patterns (same format as .gitignore).
"""

import fnmatch
from pathlib import Path

from ..json import json_handler
from ..path import builder

BUILTIN_IGNORES = [
    ".backup_system/",
    ".git/",
    ".svn/",
    ".hg/",
    "__pycache__/",
    ".pytest_cache/",
    "*.pyc",
    "*.pyo",
    "*.egg-info/",
    ".venv/",
    "venv/",
    ".tox/",
    "node_modules/",
    ".vscode/",
    ".idea/",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "Thumbs.db",
    "build/",
    "dist/",
    "*.log",
]

IGNORE_EXCEPTIONS = [
    "templates/**",
    ".github/**",
    "*.md",
]


def load_patterns(project_root: str) -> list[str]:
    """Load ignore patterns from .backupignore at the project root.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        List of glob-style ignore pattern strings.
    """
    patterns = list(BUILTIN_IGNORES)
    ignore_path = builder.build_ignore_path(project_root)

    if ignore_path.exists():
        with open(ignore_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)

    json_handler.log_operation("load_patterns", {"project_root": project_root, "count": len(patterns)})
    return patterns


def apply_ignore(rel_path: str, patterns: list[str]) -> bool:
    """Check whether a relative path matches any ignore pattern.

    Args:
        rel_path: Path relative to the project root.
        patterns: Glob-style ignore patterns.

    Returns:
        True when the path should be ignored.
    """
    rel = rel_path.replace("\\", "/")
    parts = Path(rel).parts

    for pattern in patterns:
        pat = pattern.rstrip("/")
        is_dir_pattern = pattern.endswith("/")

        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "/*"):
            return True

        for part in parts:
            if is_dir_pattern and fnmatch.fnmatch(part, pat):
                return True
            if fnmatch.fnmatch(part, pat):
                return True

        if is_dir_pattern:
            for i, part in enumerate(parts):
                if fnmatch.fnmatch(part, pat):
                    return True

    return False


def is_exception(rel_path: str, exceptions: list[str] | None = None) -> bool:
    """Check if a path matches an ignore exception (should be preserved).

    Args:
        rel_path: Path relative to the project root.
        exceptions: Exception patterns. Defaults to IGNORE_EXCEPTIONS.

    Returns:
        True if the path should be preserved even if ignored.
    """
    if exceptions is None:
        exceptions = IGNORE_EXCEPTIONS
    rel = rel_path.replace("\\", "/")
    for pattern in exceptions:
        pat = pattern.rstrip("/")
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "/*"):
            return True
        for part in Path(rel).parts:
            if fnmatch.fnmatch(part, pat):
                return True
    return False


# =============================================
