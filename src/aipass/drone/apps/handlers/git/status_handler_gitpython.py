# =================== AIPass ====================
# Name: status_handler_gitpython.py
# Description: GitPython prototype for scoped git status (DPLAN-0140 Phase 1)
# Version: 0.1.0
# Created: 2026-04-21
# Modified: 2026-04-21
# =============================================

"""
GitPython prototype for scoped git status -- DPLAN-0140 Phase 1.

Drop-in replacement for status_handler.py that uses GitPython's ``Repo``
object instead of ``subprocess.run(["git", "status", "--porcelain"])``.

The return dict format is identical to the subprocess version::

    {
        "files": [{"status": str, "path": str}, ...],
        "total": int,
        "message": str,
    }

Status codes mapped from GitPython change_type:
    M  modified (staged or unstaged)
    A  added / new in index
    D  deleted
    R  renamed
    ?  untracked (working-tree new, not staged)

Design note (two-library split):
    GitHub CLI interactions (gh pr create, gh pr list, gh pr merge) are kept
    as subprocess calls because they require the gh binary's authentication
    context and REST logic.  GitPython covers all *local* git operations.
    This split is intentional and documented in the Phase 1 investigation
    report at docs.local/gitpython_investigation_2026-04-20.md.
"""

from __future__ import annotations

from pathlib import Path

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import find_repo_root

try:
    import git as _git_module
    _GITPYTHON_AVAILABLE = True
except ImportError:
    _GITPYTHON_AVAILABLE = False


# Map GitPython diff change_type codes to porcelain-compatible single letters.
_STAGED_STATUS_MAP: dict[str, str] = {
    "A": "A",
    "D": "D",
    "M": "M",
    "R": "R",
    "C": "C",
    "T": "T",
    "U": "U",
}

_UNSTAGED_STATUS_MAP: dict[str, str] = {
    "D": "D",
    "M": "M",
    "R": "R",
    "A": "A",
}


def _collect_staged(repo: "_git_module.Repo", rel_prefix: str, rel_dir: str) -> list[dict]:
    """Return staged changes that fall under the branch directory."""
    files: list[dict] = []
    try:
        staged_diffs = repo.head.commit.diff()
    except Exception as exc:  # empty repo or detached HEAD
        logger.debug("status_handler_gitpython: could not get staged diffs: %s", exc)
        return files

    for diff in staged_diffs:
        path = diff.b_path or diff.a_path
        if not path:
            continue
        if not (path.startswith(rel_prefix) or path == rel_dir):
            continue
        code = _STAGED_STATUS_MAP.get(diff.change_type, diff.change_type)
        files.append({"status": code, "path": path})
    return files


def _collect_unstaged(repo: "_git_module.Repo", rel_prefix: str, rel_dir: str) -> list[dict]:
    """Return unstaged working-tree changes that fall under the branch directory."""
    files: list[dict] = []
    for diff in repo.index.diff(None):
        path = diff.b_path or diff.a_path
        if not path:
            continue
        if not (path.startswith(rel_prefix) or path == rel_dir):
            continue
        code = _UNSTAGED_STATUS_MAP.get(diff.change_type, diff.change_type)
        files.append({"status": code, "path": path})
    return files


def _collect_untracked(repo: "_git_module.Repo", rel_prefix: str, rel_dir: str) -> list[dict]:
    """Return untracked files that fall under the branch directory."""
    files: list[dict] = []
    for upath in repo.untracked_files:
        if upath.startswith(rel_prefix) or upath == rel_dir:
            files.append({"status": "?", "path": upath})
    return files


def get_branch_status(branch_dir: Path) -> dict:
    """Get git status filtered to files under branch_dir using GitPython.

    This is a drop-in replacement for status_handler.get_branch_status().
    The return format is identical; callers do not need to change.

    Args:
        branch_dir: Absolute path to the branch directory to scope output to.

    Returns:
        Dict with:
            files  -- list of {"status": str, "path": str} dicts
            total  -- int count of changed files
            message -- human-readable summary string
    """
    if not _GITPYTHON_AVAILABLE:
        logger.error(
            "status_handler_gitpython: GitPython is not installed. "
            "Run: pip install gitpython"
        )
        return {
            "files": [],
            "total": 0,
            "message": "GitPython not available -- install with: pip install gitpython",
        }

    repo_root = find_repo_root()

    try:
        repo = _git_module.Repo(str(repo_root))
    except _git_module.InvalidGitRepositoryError as exc:
        logger.error("status_handler_gitpython: not a git repository at %s: %s", repo_root, exc)
        return {"files": [], "total": 0, "message": f"Not a git repository: {exc}"}
    except _git_module.GitCommandNotFound as exc:
        logger.error("status_handler_gitpython: git not found: %s", exc)
        return {"files": [], "total": 0, "message": f"git not found: {exc}"}

    # Compute relative scope for filtering -- identical logic to subprocess version.
    try:
        rel_dir = branch_dir.resolve().relative_to(repo_root.resolve())
    except ValueError:
        logger.warning(
            "get_branch_status: branch_dir %s not relative to repo root %s, using absolute",
            branch_dir,
            repo_root,
        )
        rel_dir = branch_dir

    rel_prefix = str(rel_dir) + "/"
    rel_dir_str = str(rel_dir)

    files: list[dict] = []
    files.extend(_collect_staged(repo, rel_prefix, rel_dir_str))
    files.extend(_collect_unstaged(repo, rel_prefix, rel_dir_str))
    files.extend(_collect_untracked(repo, rel_prefix, rel_dir_str))

    total = len(files)
    message = f"{total} file(s) changed under {rel_dir}"
    json_handler.log_operation(
        "get_branch_status_gitpython",
        {"branch_dir": str(branch_dir), "total": total},
    )
    logger.info(message)

    return {"files": files, "total": total, "message": message}
