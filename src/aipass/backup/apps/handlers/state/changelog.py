# =================== AIPass ====================
# Name: changelog.py
# Description: Per-project backup changelog append/read
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Changelog state handler.

Appends and reads structured changelog entries describing each backup run
for a project. Stored at .backup/changelog.json.
"""

from ..json import json_handler
from ..path import builder


def append_changelog(project_root: str, entry: dict) -> None:
    """Append a changelog entry for a project.

    Args:
        project_root: Absolute path to the project root.
        entry: Entry payload (timestamp, mode, summary, etc.).
    """
    cl_path = str(builder.build_changelog_path(project_root))
    data = json_handler.load_json(cl_path)
    if "entries" not in data:
        data["entries"] = []
    data["entries"].append(entry)
    json_handler.save_json(cl_path, data)
    json_handler.log_operation("append_changelog", {"project_root": project_root})


def load_changelog(project_root: str) -> list[dict]:
    """Load changelog entries for a project.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Chronological list of entry dicts.
    """
    cl_path = str(builder.build_changelog_path(project_root))
    data = json_handler.load_json(cl_path)
    entries = data.get("entries", [])
    json_handler.log_operation("load_changelog", {"project_root": project_root, "count": len(entries)})
    return entries


# =============================================
