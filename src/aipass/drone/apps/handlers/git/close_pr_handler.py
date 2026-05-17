# =================== AIPass ====================
# Name: close_pr_handler.py
# Description: Close PR handler — close a GitHub pull request by number
# Version: 1.0.0
# Created: 2026-05-16
# Modified: 2026-05-16
# =============================================

"""Close PR handler — close a GitHub pull request by number."""

from __future__ import annotations

import subprocess

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import find_repo_root


def close_pr(pr_number: str) -> dict:
    """Close a GitHub pull request by number.

    Returns:
        Dict with success and message keys.
    """
    if not pr_number.isdigit():
        return {"success": False, "message": f"Invalid PR number: '{pr_number}'. Must be a positive integer."}

    repo_root = find_repo_root()

    try:
        result = subprocess.run(
            ["gh", "pr", "close", pr_number],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except FileNotFoundError as exc:
        logger.warning("gh CLI not found: %s", exc)
        return {"success": False, "message": "gh CLI not found. Install: https://cli.github.com/"}
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("gh pr close %s failed: %s", pr_number, exc)
        return {"success": False, "message": f"Close failed: {exc}"}

    if result.returncode != 0:
        return {"success": False, "message": f"Close failed: {result.stderr.strip()}"}

    json_handler.log_operation("close_pr", {"pr_number": pr_number})
    logger.info("Closed PR #%s", pr_number)

    return {"success": True, "message": f"Closed PR #{pr_number}."}
