# =================== AIPass ====================
# Name: skip_dirs.py
# Description: Shared source-skip directories for branch-tree-scanning checkers
# Version: 1.0.0
# Created: 2026-06-10
# Modified: 2026-06-10
# =============================================

"""Shared skip-directory set for checkers that rglob branch trees.

Single source of truth so per-checker lists cannot drift.
Output dirs (artifacts, dropbox, docs.local, system_logs) are runtime
products, not committed source — scanning them causes local-vs-CI
audit divergence (FPLAN-0261).
"""

DISABLED_FILE_MARKER = "(disabled)"


def is_disabled_file(name: str) -> bool:
    """Return True if filename contains the (disabled) convention marker."""
    return DISABLED_FILE_MARKER in name


SOURCE_SKIP_DIRS: frozenset[str] = frozenset(
    {
        # Build / cache
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        # Environment
        ".venv",
        "venv",
        "node_modules",
        ".git",
        "site-packages",
        # Archive / staging
        ".archive",
        ".sorting_unprocessed",
        # Project infrastructure (not auditable source)
        ".trinity",
        ".aipass",
        ".ai_mail.local",
        ".spawn",
        # Output / runtime (gitignored — causes local-vs-CI divergence)
        "artifacts",
        "dropbox",
        "docs.local",
        "system_logs",
        # Data / non-source
        "logs",
        "tools",
        "backups",
        "reports",
        "docs",
    }
)
