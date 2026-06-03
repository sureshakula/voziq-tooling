# =================== AIPass ====================
# Name: branches_handler.py
# Description: Remote branches handler — list remote branches
# Version: 1.0.0
# Created: 2026-05-12
# Modified: 2026-05-12
# =============================================

"""Remote branches handler — list remote branches."""

from __future__ import annotations

import subprocess

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import find_repo_root


def list_remote_branches() -> dict:
    """List remote branches with origin/ prefix stripped.

    Returns:
        Dict with branches list, count, and message.
    """
    repo_root = find_repo_root()

    # Prune stale remote-tracking refs before listing
    try:
        prune = subprocess.run(
            ["git", "fetch", "--prune"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if prune.returncode != 0:
            logger.warning("git fetch --prune failed (listing stale refs): %s", prune.stderr.strip())
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("git fetch --prune unavailable (offline?), listing may include stale refs: %s", exc)

    try:
        result = subprocess.run(
            ["git", "branch", "-r"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git branch -r failed: %s", exc)
        return {"branches": [], "count": 0, "message": f"Failed to list branches: {exc}"}

    if result.returncode != 0:
        return {"branches": [], "count": 0, "message": f"git branch -r error: {result.stderr.strip()}"}

    branches = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if not name or " -> " in name:
            continue
        if name.startswith("origin/"):
            name = name[len("origin/") :]
        branches.append(name)

    json_handler.log_operation("list_remote_branches", {"count": len(branches)})
    logger.info("Listed %d remote branches", len(branches))

    return {"branches": branches, "count": len(branches), "message": f"{len(branches)} remote branches"}


def prune_temp_branches() -> dict:
    """Delete local and remote temp PR branches (citizen/*) that are already merged.

    Returns:
        Dict with pruned list, count, and message.
    """
    repo_root = find_repo_root()
    pruned: list[str] = []

    try:
        merged = subprocess.run(
            ["git", "branch", "--merged", "main"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if merged.returncode != 0:
            return {"pruned": [], "count": 0, "message": f"git branch --merged failed: {merged.stderr.strip()}"}

        for line in merged.stdout.splitlines():
            name = line.strip().lstrip("* ")
            if name.startswith("citizen/"):
                local_del = subprocess.run(
                    ["git", "branch", "-d", name],
                    capture_output=True,
                    text=True,
                    cwd=str(repo_root),
                )
                if local_del.returncode == 0:
                    pruned.append(name)
                    logger.info("Pruned merged temp branch: %s", name)
                else:
                    logger.warning("Failed to delete local branch %s: %s", name, local_del.stderr.strip())

    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("prune_temp_branches failed: %s", exc)
        return {"pruned": [], "count": 0, "message": f"Prune failed: {exc}"}

    json_handler.log_operation("prune_temp_branches", {"count": len(pruned)})
    msg = f"Pruned {len(pruned)} merged temp branch(es)" if pruned else "No merged temp branches to prune"
    return {"pruned": pruned, "count": len(pruned), "message": msg}
