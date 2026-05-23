# =================== AIPass ====================
# Name: rollover.py
# Version: 1.0.0
# Description: Checks branch memory files and runs rollover if overdue (PreCompact)
# Branch: hooks
# Layer: apps/handlers/lifecycle
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Scans all branches for over-limit memory files and triggers rollover via drone."""

import json
import os
import subprocess
from pathlib import Path

from aipass.hooks.apps.sound import speak
from aipass.prax.apps.modules.logger import system_logger as logger


def _find_repo_root() -> Path | None:
    aipass_home = os.environ.get("AIPASS_HOME", "")
    if aipass_home:
        p = Path(aipass_home)
        if (p / "AIPASS_REGISTRY.json").exists():
            return p
    cwd = Path.cwd()
    for parent in [cwd, *list(cwd.parents)]:
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return None


def _read_registry(repo_root: Path) -> list[dict]:
    registry_path = repo_root / "AIPASS_REGISTRY.json"
    if not registry_path.exists():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        branches = data.get("branches", [])
        for branch in branches:
            raw_path = branch.get("path", "")
            resolved = Path(raw_path)
            if not resolved.is_absolute():
                resolved = repo_root / raw_path
            branch["_resolved_path"] = resolved
        return branches
    except Exception as exc:
        logger.info("[HOOKS] rollover: registry read failed: %s", exc)
        return []


def _check_file(file_path: Path) -> tuple[bool, str]:
    if not file_path.is_file():
        return False, ""
    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as exc:
        logger.info("[HOOKS] rollover: file parse failed %s: %s", file_path, exc)
        return False, ""

    limits = data.get("document_metadata", {}).get("limits", {})

    has_v2_limits = any(k in limits for k in ("max_sessions", "max_key_learnings", "max_observations"))
    if has_v2_limits:
        reasons: list[str] = []
        max_sessions = limits.get("max_sessions")
        if max_sessions is not None:
            sessions = data.get("sessions", [])
            if isinstance(sessions, list) and len(sessions) >= max_sessions:
                reasons.append(f"{len(sessions)}/{max_sessions} sessions")

        max_key_learnings = limits.get("max_key_learnings")
        if max_key_learnings is not None:
            key_learnings = data.get("key_learnings", {})
            if isinstance(key_learnings, dict) and len(key_learnings) >= max_key_learnings:
                reasons.append(f"{len(key_learnings)}/{max_key_learnings} learnings")

        max_observations = limits.get("max_observations")
        if max_observations is not None:
            observations = data.get("observations", [])
            if isinstance(observations, list) and len(observations) >= max_observations:
                reasons.append(f"{len(observations)}/{max_observations} observations")

        if reasons:
            return True, ", ".join(reasons)
        return False, ""

    max_lines = limits.get("max_lines", 600)
    current_lines = raw.count("\n") + 1
    if current_lines >= max_lines:
        return True, f"{current_lines}/{max_lines} lines"
    return False, ""


def _find_overdue(repo_root: Path) -> list[tuple[str, str, str]]:
    branches = _read_registry(repo_root)
    overdue: list[tuple[str, str, str]] = []
    for branch in branches:
        name = branch.get("name", "unknown")
        branch_path = branch.get("_resolved_path")
        if not branch_path or not branch_path.is_dir():
            continue
        for memory_type in ("local", "observations"):
            file_path = branch_path / ".trinity" / f"{memory_type}.json"
            is_overdue, reason = _check_file(file_path)
            if is_overdue:
                overdue.append((name, memory_type, reason))
    return overdue


def _run_rollover(repo_root: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["drone", "@memory", "rollover", "run"],
            capture_output=True,
            text=True,
            timeout=110,
            cwd=str(repo_root),
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        logger.info("[HOOKS] rollover: drone rollover timed out (110s)")
        return False, "Rollover timed out (110s)"
    except Exception as exc:
        logger.info("[HOOKS] rollover: drone rollover failed: %s", exc)
        return False, str(exc)


def handle(hook_data: dict) -> dict:
    """Check memory files for overflow and trigger rollover if needed."""
    speak("pre compact rollover")

    try:
        repo_root = _find_repo_root()
        if not repo_root:
            return {"stdout": "", "exit_code": 0}

        overdue = _find_overdue(repo_root)
        if not overdue:
            return {"stdout": "", "exit_code": 0}

        summary = "; ".join(f"{name}.{mtype} ({reason})" for name, mtype, reason in overdue)
        logger.info("[HOOKS] rollover: %d overdue — %s", len(overdue), summary)

        success, output = _run_rollover(repo_root)
        if success:
            logger.info("[HOOKS] rollover: complete (%d files processed)", len(overdue))
        else:
            logger.info("[HOOKS] rollover: failed — %s", output[:200])

        return {"stdout": "", "exit_code": 0}

    except Exception as exc:
        logger.info("[HOOKS] rollover: unexpected error: %s", exc)
        return {"stdout": "", "exit_code": 0}
