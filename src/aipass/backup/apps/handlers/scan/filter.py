# =================== AIPass ====================
# Name: filter.py
# Description: Post-walk path filtering against ignore/whitelist/size rules
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""Path filter.

Applies ignore patterns, whitelist entries, and an upper size bound to a list
of candidate paths produced by the walker.
"""

import os

from aipass.prax import logger

from ..ignore.patterns import apply_ignore
from ..ignore.whitelist import is_whitelisted
from ..json import json_handler


def filter_paths(
    paths: list[tuple[str, str]],
    ignore_patterns: list[str],
    whitelist: list[str],
    max_size_mb: int,
) -> list[tuple[str, str]]:
    """Filter candidate paths for inclusion in a backup.

    Args:
        paths: List of (absolute_path, relative_path) tuples from the walker.
        ignore_patterns: Glob-style ignore patterns to reject matches.
        whitelist: Whitelist entries that override ignore matches.
        max_size_mb: Maximum per-file size in megabytes; larger files are skipped.

    Returns:
        Filtered list of (absolute_path, relative_path) tuples to back up.
    """
    max_bytes = max_size_mb * 1024 * 1024
    result = []
    skipped = 0

    for abs_path, rel_path in paths:
        if is_whitelisted(rel_path, whitelist):
            result.append((abs_path, rel_path))
            continue

        if apply_ignore(rel_path, ignore_patterns):
            skipped += 1
            continue

        try:
            size = os.path.getsize(abs_path)
        except OSError as e:
            logger.warning(f"Cannot stat {abs_path}: {e}")
            skipped += 1
            continue

        if size > max_bytes:
            skipped += 1
            continue

        result.append((abs_path, rel_path))

    json_handler.log_operation(
        "filter_paths",
        {"total": len(paths), "included": len(result), "skipped": skipped},
    )
    return result


# =============================================
