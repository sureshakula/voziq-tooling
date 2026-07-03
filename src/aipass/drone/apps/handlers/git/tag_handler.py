# =================== AIPass ====================
# Name: tag_handler.py
# Description: Tag handler — create, push, and list release tags
# Version: 1.0.0
# Created: 2026-07-02
# Modified: 2026-07-02
# =============================================

"""Tag handler — create, push, and list release tags."""

from __future__ import annotations

import re
import subprocess

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.git.lock_handler import find_repo_root

_VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")
_PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
_INIT_VERSION_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)


def tag_release(version: str) -> dict:
    """Create and push an annotated release tag."""
    if not _VERSION_RE.match(version):
        return {"success": False, "message": f"Invalid version format '{version}'. Expected vX.Y.Z (e.g. v2.6.1)."}

    bare_version = version[1:]  # strip leading 'v'
    repo_root = find_repo_root()

    # Fetch latest remote state
    try:
        result = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git fetch origin failed: %s", exc)
        return {"success": False, "message": f"Fetch failed: {exc}"}

    if result.returncode != 0:
        return {"success": False, "message": f"Fetch failed: {result.stderr.strip()}"}

    # VERSION GUARD — pyproject.toml
    try:
        result = subprocess.run(
            ["git", "show", "origin/main:pyproject.toml"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git show origin/main:pyproject.toml failed: %s", exc)
        return {"success": False, "message": f"Failed to read pyproject.toml from origin/main: {exc}"}

    if result.returncode != 0:
        return {"success": False, "message": f"Failed to read pyproject.toml from origin/main: {result.stderr.strip()}"}

    pyproject_match = _PYPROJECT_VERSION_RE.search(result.stdout)
    pyproject_version = pyproject_match.group(1) if pyproject_match else None

    # VERSION GUARD — __init__.py
    try:
        result = subprocess.run(
            ["git", "show", "origin/main:src/aipass/__init__.py"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git show origin/main:src/aipass/__init__.py failed: %s", exc)
        return {"success": False, "message": f"Failed to read __init__.py from origin/main: {exc}"}

    if result.returncode != 0:
        return {"success": False, "message": f"Failed to read __init__.py from origin/main: {result.stderr.strip()}"}

    init_match = _INIT_VERSION_RE.search(result.stdout)
    init_version = init_match.group(1) if init_match else None

    if pyproject_version != bare_version or init_version != bare_version:
        return {
            "success": False,
            "message": (
                f"Version mismatch — tag: {bare_version}, "
                f"pyproject.toml: {pyproject_version}, "
                f"__init__.py: {init_version}. "
                "All three must agree before tagging."
            ),
        }

    # EXISTS GUARD — local
    try:
        result = subprocess.run(
            ["git", "tag", "-l", version],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git tag -l %s failed: %s", version, exc)
        return {"success": False, "message": f"Tag check failed: {exc}"}

    if result.stdout.strip():
        return {"success": False, "message": f"Tag '{version}' already exists locally."}

    # EXISTS GUARD — remote
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "origin", f"refs/tags/{version}"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git ls-remote --tags origin %s failed: %s", version, exc)
        return {"success": False, "message": f"Remote tag check failed: {exc}"}

    if result.stdout.strip():
        return {"success": False, "message": f"Tag '{version}' already exists on remote."}

    # Resolve origin/main SHA
    try:
        result = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git rev-parse origin/main failed: %s", exc)
        return {"success": False, "message": f"Failed to resolve origin/main: {exc}"}

    if result.returncode != 0:
        return {"success": False, "message": f"Failed to resolve origin/main: {result.stderr.strip()}"}

    sha = result.stdout.strip()

    # Create annotated tag
    try:
        result = subprocess.run(
            ["git", "tag", "-a", version, "origin/main", "-m", f"Release {version}"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git tag -a %s failed: %s", version, exc)
        return {"success": False, "message": f"Tag creation failed: {exc}"}

    if result.returncode != 0:
        return {"success": False, "message": f"Tag creation failed: {result.stderr.strip()}"}

    # Push tag
    try:
        result = subprocess.run(
            ["git", "push", "origin", version],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git push origin %s failed: %s", version, exc)
        return {"success": False, "message": f"Tag push failed: {exc}"}

    if result.returncode != 0:
        return {"success": False, "message": f"Tag push failed: {result.stderr.strip()}"}

    json_handler.log_operation("tag_release", {"version": version, "sha": sha})
    logger.info("Tagged %s at %s", version, sha)

    return {"success": True, "message": f"Tagged {version} on origin/main ({sha})."}


def list_tags() -> dict:
    """List all tags sorted newest-first."""
    repo_root = find_repo_root()

    try:
        result = subprocess.run(
            ["git", "tag", "-l", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("git tag -l failed: %s", exc)
        return {"success": False, "tags": [], "message": f"Failed to list tags: {exc}"}

    if result.returncode != 0:
        return {"success": False, "tags": [], "message": f"Failed to list tags: {result.stderr.strip()}"}

    tags = [t for t in result.stdout.strip().splitlines() if t]

    return {"success": True, "tags": tags, "message": f"{len(tags)} tag(s) found."}
