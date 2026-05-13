# =================== AIPass ====================
# Name: checkout_handler.py
# Description: Branch checkout handler with hard guard
# Version: 1.0.0
# Created: 2026-05-12
# Modified: 2026-05-12
# =============================================

"""Branch checkout handler with hard guard."""

from __future__ import annotations

import subprocess

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import find_repo_root

_ALLOWED_TARGETS = ("main", "dev")


def checkout_branch(target: str) -> dict:
    """Switch to target branch (main or dev only)."""
    if target not in _ALLOWED_TARGETS:
        allowed = ", ".join(_ALLOWED_TARGETS)
        return {
            "stdout": "",
            "stderr": f"Checkout denied: only {allowed} branches are allowed. Got '{target}'.",
            "exit_code": 1,
            "current_branch": "",
        }

    repo_root = find_repo_root()

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if status.stdout.strip():
            return {
                "stdout": "",
                "stderr": "Cannot checkout: uncommitted changes in working tree. Commit or stash first.",
                "exit_code": 1,
                "current_branch": "",
            }
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git status check failed: %s", exc)
        return {
            "stdout": "",
            "stderr": f"Failed to check working tree status: {exc}",
            "exit_code": 1,
            "current_branch": "",
        }

    try:
        result = subprocess.run(
            ["git", "checkout", target],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if result.returncode != 0 and "did not match" in result.stderr:
            result = subprocess.run(
                ["git", "checkout", "-b", target],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git checkout failed: %s", exc)
        return {
            "stdout": "",
            "stderr": f"git checkout failed: {exc}",
            "exit_code": 1,
            "current_branch": "",
        }

    json_handler.log_operation(
        "checkout_branch",
        {"target": target, "exit_code": result.returncode},
    )

    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "exit_code": result.returncode,
        "current_branch": target if result.returncode == 0 else "",
    }
