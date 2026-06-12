# =================== AIPass ====================
# Name: timestamps.py
# Description: Per-project last-backup timestamp persistence
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Timestamp state handler.

Persists per-file modification timestamps recorded at the last backup so the
versioned copy strategy can detect changes.
"""

from ..json import json_handler
from ..path import builder


def load_timestamps(project_root: str) -> dict:
    """Load the timestamp map for a project.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Mapping of relative_path to last recorded mtime (float seconds).
    """
    ts_path = str(builder.build_timestamps_path(project_root))
    data = json_handler.load_json(ts_path)
    json_handler.log_operation("load_timestamps", {"project_root": project_root, "count": len(data)})
    return data


def save_timestamps(project_root: str, data: dict) -> None:
    """Persist the timestamp map for a project.

    Args:
        project_root: Absolute path to the project root.
        data: Mapping of relative_path to mtime (float seconds).
    """
    ts_path = str(builder.build_timestamps_path(project_root))
    json_handler.save_json(ts_path, data)
    json_handler.log_operation("save_timestamps", {"project_root": project_root, "count": len(data)})


# =============================================
