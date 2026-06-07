# =================== AIPass ====================
# Name: json_ops.py
# Description: Shared JSON operations — deep merge and backup
# Version: 1.0.0
# Created: 2026-06-06
# Modified: 2026-06-06
# =============================================

"""Shared JSON operations — deep merge and backup utilities.

Dependency-free: uses only stdlib. Importable before drone/prax exist.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def deep_merge(template_data: Any, existing_data: Any) -> Any:
    """Recursively merge template structure with existing data.

    Merge strategy:
    - Both dicts: merge keys. Template defines structure, existing fills values.
    - Template has key that existing doesn't: add from template (default).
    - Existing has key that template doesn't: KEEP existing key (don't prune).
    - Both lists: keep existing list (don't overwrite user data).
    - Scalar values: keep existing value (don't overwrite).
    - If existing is None/empty but template has value: use template value.

    Args:
        template_data: Template structure (provides fields and defaults).
        existing_data: Existing data (provides values to preserve).

    Returns:
        Merged result combining template structure with existing values.
    """
    if existing_data is None:
        return template_data

    if template_data is None:
        return existing_data

    if isinstance(template_data, dict) and isinstance(existing_data, dict):
        result = {}

        for key in template_data:
            if key in existing_data:
                result[key] = deep_merge(template_data[key], existing_data[key])
            else:
                result[key] = template_data[key]

        for key in existing_data:
            if key not in result:
                result[key] = existing_data[key]

        return result

    if isinstance(template_data, list) and isinstance(existing_data, list):
        if len(existing_data) > 0:
            return existing_data
        if len(template_data) > 0:
            return template_data
        return []

    if existing_data is not None:
        if isinstance(existing_data, str) and existing_data == "" and template_data:
            return template_data
        return existing_data

    return template_data


def backup_json(file_path: Path) -> Path:
    """Create a timestamped backup of a JSON file.

    The backup is placed in a ``.recovery/`` directory alongside the file,
    named with a timestamp suffix.

    Args:
        file_path: Path to the JSON file to back up.

    Returns:
        Path to the backup file.

    Raises:
        FileNotFoundError: If the source file doesn't exist.
        IOError: If the backup copy fails.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Cannot backup — file not found: {file_path}")

    backup_dir = file_path.parent / ".recovery"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.name}.{timestamp}.backup"
    backup_path = backup_dir / backup_name

    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except (IOError, OSError) as exc:
        logger.error("Backup failed for %s: %s", file_path.name, exc)
        raise
