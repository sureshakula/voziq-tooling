# =================== AIPass ====================
# Name: commit_handler.py
# Description: Commit handler with scoped staging
# Version: 1.0.0
# Created: 2026-05-12
# Modified: 2026-05-12
# =============================================

"""Commit handler with scoped staging."""

from __future__ import annotations

import subprocess
from pathlib import Path

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import find_repo_root


def stage_branch_dir(branch_dir: Path, repo_root: Path | None = None) -> dict:
    """Stage all changes under branch_dir.

    Shared utility used by both commit_handler and pr_handler.
    """
    if repo_root is None:
        repo_root = find_repo_root()

    try:
        rel_dir = branch_dir.resolve().relative_to(repo_root.resolve())
    except ValueError:
        logger.warning(
            "stage_branch_dir: branch_dir %s not relative to repo root %s",
            branch_dir,
            repo_root,
        )
        rel_dir = branch_dir

    add_result = subprocess.run(
        ["git", "add", str(rel_dir) + "/"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    if add_result.returncode != 0:
        return {
            "success": False,
            "rel_dir": rel_dir,
            "message": f"Failed to stage files: {add_result.stderr.strip()}",
        }

    return {"success": True, "rel_dir": rel_dir, "message": f"Staged files under {rel_dir}"}


def commit_changes(
    message: str,
    branch_dir: Path | None = None,
    all_files: bool = False,
    files: list[str] | None = None,
) -> dict:
    """Commit changes. With --all, stages the entire repo (not CWD-scoped).

    Post-DPLAN-0173: only devpulse commits, agents don't PR. Repo-wide
    staging is the correct default since dispatched agents work across
    multiple branch directories.

    With file paths, stages only those specific files (selective commit).
    """
    repo_root = find_repo_root()

    if files:
        add_result = subprocess.run(
            ["git", "add", "--"] + files,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if add_result.returncode != 0:
            return {"stdout": "", "stderr": f"Failed to stage: {add_result.stderr.strip()}", "exit_code": 1}
    elif all_files:
        import shutil

        ruff_bin = shutil.which("ruff")
        if not ruff_bin:
            venv_ruff = repo_root / ".venv" / "bin" / "ruff"
            if venv_ruff.exists():
                ruff_bin = str(venv_ruff)
        if ruff_bin:
            subprocess.run(
                [ruff_bin, "check", "--fix", "src/", "tests/"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
            subprocess.run(
                [ruff_bin, "format", "src/", "tests/"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
        add_result = subprocess.run(
            ["git", "add", "-A"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        if add_result.returncode != 0:
            return {"stdout": "", "stderr": f"Failed to stage: {add_result.stderr.strip()}", "exit_code": 1}

    diff_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    if diff_check.returncode == 0:
        return {
            "stdout": "",
            "stderr": "Nothing to commit: no changes staged",
            "exit_code": 1,
        }

    try:
        cmd = ["git", "commit", "-m", message]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git commit failed: %s", exc)
        return {"stdout": "", "stderr": f"git commit failed: {exc}", "exit_code": 1}

    json_handler.log_operation(
        "commit_changes",
        {"message": message, "all_files": all_files, "files": files, "exit_code": result.returncode},
    )

    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "exit_code": result.returncode,
    }
