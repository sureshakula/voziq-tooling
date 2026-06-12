# =================== AIPass ====================
# Name: versioned.py
# Description: Versioned copy strategy — incremental timestamped copies
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Versioned copy handler.

Copies only files whose modification time exceeds their previously recorded
timestamp into a versioned (timestamped) destination directory.
"""

import os
import shutil

from aipass.prax import logger

from ..json import json_handler


def copy_versioned(
    files: list[tuple[str, str]],
    dest: str,
    previous_timestamps: dict,
    project_root: str,
    on_progress=None,
) -> dict:
    """Copy changed files into a versioned destination.

    Args:
        files: List of (absolute_path, relative_path) tuples.
        dest: Absolute destination directory for this version.
        previous_timestamps: Mapping of relative_path to last-known mtime.
        project_root: Project root for logging context.
        on_progress: Optional callback called after each file is processed.

    Returns:
        Dict with files_copied, bytes_copied, files_unchanged, errors, new_timestamps.
    """
    os.makedirs(dest, exist_ok=True)

    files_copied = 0
    files_unchanged = 0
    bytes_copied = 0
    errors = []
    new_timestamps = {}

    for abs_path, rel_path in files:
        try:
            current_mtime = os.path.getmtime(abs_path)
        except OSError as e:
            logger.warning(f"Cannot stat {rel_path}: {e}")
            errors.append(f"{rel_path}: {e}")
            if on_progress:
                on_progress()
            continue

        new_timestamps[rel_path] = current_mtime
        prev_mtime = previous_timestamps.get(rel_path, 0)

        if current_mtime <= prev_mtime:
            files_unchanged += 1
            if on_progress:
                on_progress()
            continue

        target = os.path.join(dest, rel_path)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(abs_path, target)
            bytes_copied += os.path.getsize(abs_path)
            files_copied += 1
        except OSError as e:
            logger.warning(f"Failed to copy {rel_path}: {e}")
            errors.append(f"{rel_path}: {e}")
        if on_progress:
            on_progress()

    result = {
        "files_copied": files_copied,
        "files_unchanged": files_unchanged,
        "bytes_copied": bytes_copied,
        "errors": errors,
        "new_timestamps": new_timestamps,
    }
    json_handler.log_operation(
        "copy_versioned",
        {
            "project_root": project_root,
            "files_copied": files_copied,
            "files_unchanged": files_unchanged,
        },
    )
    return result


# =============================================
