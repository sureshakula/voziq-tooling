# =================== AIPass ====================
# Name: setup.py
# Description: Project setup handler — scaffold .backup_system/ directory in target
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Project setup handler.

Creates the ``.backup_system/`` scaffold (config, snapshots/, versions/, logs/)
inside a target project path, and a ``.backupignore`` at the project root.
"""

from datetime import datetime, timezone
from pathlib import Path

from ..ignore.patterns import BUILTIN_IGNORES
from ..json import json_handler
from ..path import builder


def _build_backupignore() -> str:
    """Generate .backupignore content from BUILTIN_IGNORES."""
    lines = [
        "# Backup System ignore patterns (gitignore-style)",
        "# Lines starting with # are comments. Blank lines are ignored.",
        "# Edit this file to customize. Source defaults: handlers/ignore/patterns.py",
        "",
    ]
    for pattern in BUILTIN_IGNORES:
        lines.append(pattern)
    return "\n".join(lines) + "\n"


DEFAULT_CONFIG = {
    "version": "1.0.0",
    "backup_mode": "snapshot",
    "max_versions": 10,
    "max_file_size_mb": 100,
    "auto_ignore_git": True,
    "drive_sync": False,
    "whitelist": [],
}


def create_backup_dir(project_path: str) -> Path | None:
    """Create the ``.backup_system/`` scaffold inside a project path.

    Args:
        project_path: Absolute filesystem path to the target project.

    Returns:
        Path to the created ``.backup_system/`` directory, or None on failure.
    """
    root = Path(project_path)
    if not root.is_dir():
        json_handler.log_operation("setup_failed", {"project_path": project_path, "reason": "not a directory"})
        return None

    backup_dir = builder.backup_root(project_path)
    subdirs = [
        backup_dir / "snapshots",
        backup_dir / "versions",
        backup_dir / "logs",
    ]

    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)

    config_path = builder.build_config_path(project_path)
    if not config_path.exists():
        config = {
            **DEFAULT_CONFIG,
            "project_name": root.name,
            "project_path": str(root),
            "created": datetime.now(timezone.utc).isoformat(),
        }
        json_handler.save_json(str(config_path), config)

    ignore_path = builder.build_ignore_path(project_path)
    if not ignore_path.exists():
        with open(ignore_path, "w", encoding="utf-8") as f:
            f.write(_build_backupignore())

    json_handler.log_operation("setup_complete", {"project_path": project_path})
    return backup_dir


# =============================================
