# =================== AIPass ====================
# Name: sync_handler.py
# Description: Safe main branch synchronization
# Version: 1.0.0
# Created: 2026-03-17
# Modified: 2026-03-17
# =============================================

"""
Branch synchronization — works on both main and dev.

On main: pulls latest from origin/main.
On dev: pulls origin/main into dev (realigns after PR merge).
From other branch: checks out main first, then pulls.
"""

from __future__ import annotations

import subprocess

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import find_repo_root


def sync_main(autostash: bool = False) -> dict:
    """Checkout main and pull latest changes.

    Args:
        autostash: If True, stash local changes before pull and restore after.
            Use when sync fails with 'unstaged changes' error.

    Returns:
        Dict with success (bool), message (str), and stdout (str).
    """
    repo_root = find_repo_root()
    stashed = False

    try:
        head = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        current_branch = head.stdout.strip() if head.returncode == 0 else ""

        if current_branch == "dev":
            return _sync_dev(repo_root, autostash)

        if current_branch != "main":
            checkout = subprocess.run(
                ["git", "checkout", "main"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
            if checkout.returncode != 0:
                msg = f"Failed to checkout main: {checkout.stderr.strip()}"
                logger.error(msg)
                return {"success": False, "message": msg, "stdout": checkout.stdout}

        if autostash:
            stash = subprocess.run(
                ["git", "stash"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
            stashed = "No local changes to save" not in stash.stdout

        # Fetch first to get latest remote state
        fetch = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if fetch.returncode != 0:
            msg = f"Failed to fetch: {fetch.stderr.strip()}"
            logger.error(msg)
            if stashed:
                subprocess.run(
                    ["git", "stash", "pop"],
                    capture_output=True,
                    text=True,
                    cwd=str(repo_root),
                )
            return {"success": False, "message": msg, "stdout": ""}

        # Check divergence to choose strategy
        rev_list = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "main...origin/main"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        ahead, behind = 0, 0
        if rev_list.returncode == 0:
            parts = rev_list.stdout.strip().split()
            ahead = int(parts[0]) if len(parts) >= 1 else 0
            behind = int(parts[1]) if len(parts) >= 2 else 0

        if ahead > 0 and behind > 0:
            # Diverged — merge instead of rebase
            result = subprocess.run(
                ["git", "merge", "origin/main", "--no-edit"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
            if result.returncode != 0:
                msg = f"Merge conflict (ahead={ahead}, behind={behind}): {result.stderr.strip()}"
                logger.error(msg)
                if stashed:
                    subprocess.run(
                        ["git", "stash", "pop"],
                        capture_output=True,
                        text=True,
                        cwd=str(repo_root),
                    )
                return {"success": False, "message": msg, "stdout": result.stdout}
            stdout = result.stdout.strip()
            msg = f"Synced main via merge (was ahead={ahead}, behind={behind}): {stdout}"
        else:
            # Normal — pull with rebase
            result = subprocess.run(
                ["git", "pull", "--rebase"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
            if result.returncode != 0:
                raw = result.stderr.strip()
                msg = f"Failed to pull: {raw}"
                if not autostash and ("unstaged changes" in raw or "uncommitted changes" in raw):
                    msg += "\n  Tip: retry with 'drone @git sync --autostash' to stash local changes first"
                logger.error(msg)
                if stashed:
                    subprocess.run(
                        ["git", "stash", "pop"],
                        capture_output=True,
                        text=True,
                        cwd=str(repo_root),
                    )
                return {"success": False, "message": msg, "stdout": result.stdout}
            stdout = result.stdout.strip()
            msg = f"Synced main: {stdout}"

        if stashed:
            pop = subprocess.run(
                ["git", "stash", "pop"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
            if pop.returncode != 0:
                logger.warning(
                    "sync_main: autostash pop failed (manual restore may be needed): %s",
                    pop.stderr.strip(),
                )

        json_handler.log_operation(
            "sync_main",
            {"result": stdout, "ahead": ahead, "behind": behind, "autostash": autostash},
        )
        logger.info(msg)
        return {"success": True, "message": msg, "stdout": stdout}

    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"Sync failed: {exc}"
        logger.error(msg)
        return {"success": False, "message": msg, "stdout": ""}


def _sync_dev(repo_root, autostash: bool = False) -> dict:
    """Pull origin/main into dev branch to realign after PR merge."""
    stashed = False

    if autostash:
        stash = subprocess.run(
            ["git", "stash"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        stashed = "No local changes to save" not in stash.stdout

    fetch = subprocess.run(
        ["git", "fetch", "origin", "--prune"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    if fetch.returncode != 0:
        if stashed:
            subprocess.run(["git", "stash", "pop"], capture_output=True, text=True, cwd=str(repo_root))
        return {"success": False, "message": f"Fetch failed: {fetch.stderr.strip()}", "stdout": ""}

    result = subprocess.run(
        ["git", "pull", "origin", "main", "--rebase"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    if stashed:
        subprocess.run(["git", "stash", "pop"], capture_output=True, text=True, cwd=str(repo_root))

    if result.returncode != 0:
        raw = result.stderr.strip()
        msg = f"Failed to sync dev from main: {raw}"
        if not autostash and ("unstaged changes" in raw or "uncommitted changes" in raw):
            msg += "\n  Tip: retry with 'drone @git sync --autostash'"
        return {"success": False, "message": msg, "stdout": result.stdout}

    stdout = result.stdout.strip()
    msg = f"Synced dev from origin/main: {stdout}"
    json_handler.log_operation("sync_dev", {"result": stdout, "autostash": autostash})
    logger.info(msg)
    return {"success": True, "message": msg, "stdout": stdout}
