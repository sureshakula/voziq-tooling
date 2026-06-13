# =================== AIPass ====================
# Name: todo_section.py
# Description: Todo section builder for devpulse dashboard
# Version: 1.0.0
# Created: 2026-06-07
# Modified: 2026-06-07
# =============================================

"""Todo section builder for devpulse dashboard plugin.

Reads todos[] from .trinity/local.json and writes a 'todo' section
(managed_by: devpulse, todo_count, todos) via write_section().
"""

import json
from pathlib import Path
from typing import Dict

from aipass.prax.apps.modules.dashboard import write_section
from aipass.prax.apps.modules.logger import system_logger as logger


def build_todo_section(branch_path: Path) -> bool:
    """Build todo section data and write to dashboard.

    Args:
        branch_path: Path to devpulse branch root.

    Returns:
        True if write_section succeeded, False otherwise.
    """
    local_json_path = branch_path / ".trinity" / "local.json"

    if not local_json_path.exists():
        section_data: Dict = {
            "managed_by": "devpulse",
            "todo_count": 0,
        }
        return write_section(branch_path, "todo", section_data)

    try:
        data = json.loads(local_json_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read local.json at %s: %s", local_json_path, exc)
        section_data = {
            "managed_by": "devpulse",
            "todo_count": 0,
        }
        return write_section(branch_path, "todo", section_data)

    todos = data.get("todos", [])

    section_data = {
        "managed_by": "devpulse",
        "todo_count": len(todos),
        # "todos": todos,  # bodies live in .trinity/local.json — count-only here
    }

    return write_section(branch_path, "todo", section_data)
