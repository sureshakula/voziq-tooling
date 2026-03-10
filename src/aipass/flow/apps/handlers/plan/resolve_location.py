# =================== AIPass ====================
# Name: resolve_location.py
# Description: Plan Location Resolution Handler
# Version: 1.0.0
# Created: 2025-11-29
# Modified: 2025-11-29
# =============================================

"""
Plan Location Resolution Handler

Resolves plan locations for explicit paths.
@ symbols are pre-resolved by Drone before Flow receives args.
Handles absolute paths, relative paths, and defaults to cwd.
"""

from pathlib import Path
from typing import Tuple


def resolve_plan_location(
    location: str | None,
    ecosystem_root: Path
) -> Tuple[bool, Path, str]:
    """
    Resolve plan location for explicit paths

    Handles two location types:
    1. Explicit path: Resolved to absolute path
    2. None: Defaults to current working directory

    Note: @ symbols are pre-resolved by Drone before Flow receives args.
    Flow only handles absolute/relative paths.

    Validates that resolved directory exists.

    Args:
        location: Target location (absolute/relative path, or None for cwd)
        ecosystem_root: Root directory (kept for API compatibility, not used)

    Returns:
        Tuple of (success, resolved_path, error_message)
        - success: False if directory doesn't exist
        - resolved_path: Absolute path to directory (or Path.cwd() on error)
        - error_message: Empty string on success, error details on failure

    Examples:
        >>> resolve_plan_location("/repo/src/aipass/flow", Path("/repo/src/aipass"))
        (True, Path("/repo/src/aipass/flow"), "")

        >>> resolve_plan_location(None, Path("/repo/src/aipass"))
        (True, Path.cwd(), "")

        >>> resolve_plan_location("/nonexistent", Path("/repo/src/aipass"))
        (False, Path.cwd(), "Directory /nonexistent does not exist")
    """
    # Determine target directory
    if location:
        # Handle explicit path
        target_dir = Path(location).resolve()
    else:
        # Default to current working directory
        target_dir = Path.cwd()

    # Validate directory exists
    if not target_dir.exists():
        return False, Path.cwd(), f"Directory {target_dir} does not exist"

    return True, target_dir, ""
