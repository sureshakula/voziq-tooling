# =================== AIPass ====================
# Name: result.py
# Description: BackupResult dataclass — typed outcome container for backup runs
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Backup result dataclass.

Typed container returned by backup modules (snapshot, versioned)
describing what the run did. Consumed by the report formatter.
"""

from dataclasses import dataclass, field

from ..json import json_handler


@dataclass
class BackupResult:
    """Outcome of a single backup run."""

    mode: str
    project_root: str = ""
    files_copied: int = 0
    bytes_copied: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


def new_result(mode: str, project_root: str = "") -> BackupResult:
    """Construct an empty BackupResult for a given mode."""
    json_handler.log_operation("backup_result_created", {"mode": mode})
    return BackupResult(mode=mode, project_root=project_root)


# =============================================
