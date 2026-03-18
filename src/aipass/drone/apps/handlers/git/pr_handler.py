# =================== AIPass ====================
# Name: pr_handler.py
# Description: Full PR workflow with atomic lockfile
# Version: 1.0.0
# Created: 2026-03-17
# Modified: 2026-03-17
# =============================================

"""
Full PR workflow with atomic lockfile.

Orchestrates the complete PR creation lifecycle: lock acquisition,
branch creation, scoped staging, commit, push, PR creation via gh,
and cleanup (checkout main + release lock) in a finally block.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import (
    acquire_lock,
    find_repo_root,
    release_lock,
)


def _slugify(text: str, max_length: int = 40) -> str:
    """Convert text to a URL-safe slug for branch names.

    Lowercase, replace spaces with hyphens, strip non-alphanumeric
    (keeping hyphens), truncate to max_length.
    """
    slug = text.lower().strip()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)  # collapse multiple hyphens
    slug = slug.strip("-")
    return slug[:max_length]


def create_pr(branch_name: str, description: str, branch_dir: Path) -> dict:
    """Execute the full PR creation workflow.

    Steps:
        1. Verify we are on main
        2. Acquire lock
        3. Create feature branch
        4. Stage only files under branch_dir
        5. Check if anything staged
        6. Commit
        7. Push
        8. Create PR via gh
        9. Checkout main (finally)
        10. Release lock (finally)

    Args:
        branch_name: The calling branch name (e.g. "api").
        description: Short description for the PR.
        branch_dir: Absolute path to the caller's branch directory.

    Returns:
        Dict with success, pr_url, feature_branch, and message.
    """
    repo_root = find_repo_root()
    slug = _slugify(description)
    feature_branch = f"feat/{branch_name}-{slug}"
    lock_acquired = False

    result = {
        "success": False,
        "pr_url": "",
        "feature_branch": feature_branch,
        "message": "",
    }

    try:
        # Step 1: Check we're on main
        current = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        if current.stdout.strip() != "main":
            result["message"] = (
                f"Not on main branch (currently on {current.stdout.strip()}). "
                "Checkout main before creating a PR."
            )
            logger.error(result["message"])
            return result

        # Step 2: Acquire lock
        lock_result = acquire_lock(branch_name)
        if not lock_result["success"]:
            result["message"] = lock_result["message"]
            return result
        lock_acquired = True

        # Step 3: Create feature branch
        checkout = subprocess.run(
            ["git", "checkout", "-b", feature_branch],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        if checkout.returncode != 0:
            result["message"] = f"Failed to create branch: {checkout.stderr.strip()}"
            logger.error(result["message"])
            return result

        # Step 4: Stage only files under branch_dir
        try:
            rel_dir = branch_dir.resolve().relative_to(repo_root.resolve())
        except ValueError:
            rel_dir = branch_dir

        add_result = subprocess.run(
            ["git", "add", str(rel_dir) + "/"],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        if add_result.returncode != 0:
            result["message"] = f"Failed to stage files: {add_result.stderr.strip()}"
            logger.error(result["message"])
            return result

        # Step 5: Check if anything was staged
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        if diff_check.returncode == 0:
            # Nothing staged
            result["message"] = "Nothing to commit: no changes staged under branch directory"
            logger.warning(result["message"])
            return result

        # Step 6: Commit
        commit_msg = (
            f"feat({branch_name}): {description}\n\n"
            f"Co-Authored-By: @{branch_name} <{branch_name}@aipass>"
        )
        commit = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        if commit.returncode != 0:
            result["message"] = f"Commit failed: {commit.stderr.strip()}"
            logger.error(result["message"])
            return result

        # Step 7: Push
        push = subprocess.run(
            ["git", "push", "-u", "origin", feature_branch],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        if push.returncode != 0:
            result["message"] = f"Push failed: {push.stderr.strip()}"
            logger.error(result["message"])
            return result

        # Step 8: Create PR via gh
        pr_body = (
            f"## Summary\n\n"
            f"- {description}\n\n"
            f"## Branch\n\n"
            f"Created by @{branch_name} via `drone @git pr`\n"
        )
        pr_create = subprocess.run(
            [
                "gh", "pr", "create",
                "--title", f"feat({branch_name}): {description}",
                "--body", pr_body,
            ],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        if pr_create.returncode != 0:
            result["message"] = f"PR creation failed: {pr_create.stderr.strip()}"
            logger.error(result["message"])
            return result

        pr_url = pr_create.stdout.strip()
        result["success"] = True
        result["pr_url"] = pr_url
        result["message"] = f"PR created: {pr_url}"
        json_handler.log_operation(
            "create_pr",
            {"branch": branch_name, "feature_branch": feature_branch, "pr_url": pr_url},
        )
        logger.info(result["message"])
        return result

    except (OSError, subprocess.SubprocessError) as exc:
        result["message"] = f"PR workflow error: {exc}"
        logger.error(result["message"])
        return result

    finally:
        # Step 9: Always checkout main
        try:
            subprocess.run(
                ["git", "checkout", "main"],
                capture_output=True, text=True, cwd=str(repo_root),
            )
            subprocess.run(
                ["git", "pull"],
                capture_output=True, text=True, cwd=str(repo_root),
            )
        except (OSError, subprocess.SubprocessError):
            logger.warning("Failed to checkout main during cleanup")

        # Step 10: Always release lock
        if lock_acquired:
            release_lock(force=True)
