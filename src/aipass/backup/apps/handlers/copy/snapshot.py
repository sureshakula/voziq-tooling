# =================== AIPass ====================
# Name: snapshot.py
# Description: Snapshot copy strategy — mirror destination tree
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Snapshot copy handler.

Copies filtered files to the snapshot destination, mirroring the current
project state. Clears the previous snapshot before copying.
"""

import os
import shutil

from aipass.prax import logger

from ..json import json_handler


def copy_snapshot(
    files: list[tuple[str, str]],
    dest: str,
    project_root: str,
    on_progress=None,
) -> dict:
    """Copy files into a snapshot destination.

    Args:
        files: List of (absolute_path, relative_path) tuples.
        dest: Absolute destination directory path (.backup_system/snapshots/).
        project_root: Project root for logging context.
        on_progress: Optional callback called after each file is processed.

    Returns:
        Dict with files_copied, bytes_copied, errors.
    """
    dest_path = os.path.realpath(dest)
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
    os.makedirs(dest_path, exist_ok=True)

    files_copied = 0
    bytes_copied = 0
    errors = []

    for abs_path, rel_path in files:
        target = os.path.join(dest_path, rel_path)
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
        "bytes_copied": bytes_copied,
        "errors": errors,
    }
    json_handler.log_operation(
        "copy_snapshot",
        {
            "project_root": project_root,
            "files_copied": files_copied,
            "bytes_copied": bytes_copied,
        },
    )
    return result


# =============================================
