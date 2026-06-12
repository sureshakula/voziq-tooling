# =================== AIPass ====================
# Name: generator.py
# Description: Unified diff generator for file-pair comparison
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Diff generator.

Produces a unified diff between two files so the backup system can annotate
versioned copies with the change set they introduce.
"""

import difflib

from aipass.prax import logger

from ..json import json_handler


def generate_diff(old_path: str, new_path: str) -> str:
    """Generate a unified diff between two files.

    Args:
        old_path: Absolute path of the previous version.
        new_path: Absolute path of the new version.

    Returns:
        Unified diff as a string. Empty string if files are identical or unreadable.
    """
    try:
        with open(old_path, encoding="utf-8", errors="replace") as f:
            old_lines = f.readlines()
        with open(new_path, encoding="utf-8", errors="replace") as f:
            new_lines = f.readlines()
    except OSError as e:
        logger.warning(f"Diff failed for {old_path} -> {new_path}: {e}")
        json_handler.log_operation(
            "generate_diff_failed",
            {"old_path": old_path, "new_path": new_path, "error": str(e)},
        )
        return ""

    diff = difflib.unified_diff(old_lines, new_lines, fromfile=old_path, tofile=new_path)
    result = "".join(diff)
    json_handler.log_operation("generate_diff", {"old_path": old_path, "new_path": new_path})
    return result


# =============================================
