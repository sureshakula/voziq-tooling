# =================== AIPass ====================
# Name: presence_gate.py
# Version: 1.0.0
# Description: Single-session gate — blocks duplicate Claude runtimes per branch
# Branch: hooks
# Layer: apps/handlers/security
# Created: 2026-06-29
# Modified: 2026-06-29
# =============================================

"""Single-session gate — blocks duplicate Claude runtimes per branch.

Fires on UserPromptSubmit: calls presence.claim(). If OCCUPIED by a live PID,
blocks the prompt. If free or stale, acquires and proceeds.

Fires on Stop: calls presence.release() to clean up.

Skips sub-agents and dispatched/daemon session types.
"""

import importlib
import json
import os
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

_ALLOW = {"exit_code": 0, "stdout": ""}
_NON_BLOCKING_SESSION_TYPES = frozenset({"dispatched", "daemon"})


def _resolve_branch(hook_data: dict) -> str:
    """Resolve the branch name from hook_data's cwd (session dir, not process cwd)."""
    cwd = hook_data.get("cwd", "") or str(Path.cwd())
    search = Path(cwd).resolve()
    while search.parent != search:
        if (search / ".trinity").is_dir() or (search / "apps").is_dir():
            return search.name
        if (search / "pyproject.toml").exists() or (search / ".git").is_dir():
            break
        search = search.parent
    return Path(cwd).name


def handle(hook_data: dict) -> dict:
    """UserPromptSubmit gate — enforce one live session per branch.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (block JSON or empty) and exit_code.
    """
    try:
        agent_type = hook_data.get("agent_type", "")
        if agent_type and agent_type != "main":
            return _ALLOW

        session_type = os.environ.get("AIPASS_SESSION_TYPE", "interactive")
        if session_type in _NON_BLOCKING_SESSION_TYPES:
            return _ALLOW

        branch = _resolve_branch(hook_data)
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")

        presence = importlib.import_module("aipass.hooks.apps.modules.presence")
        result = presence.claim(
            branch=branch,
            session_id=session_id,
            session_type=session_type,
        )

        if result["status"] == "ACQUIRED":
            return _ALLOW

        pid = result.get("pid", "?")
        holder_type = result.get("session_type", "unknown")
        reason = f"{branch} already live at PID {pid} (session_type: {holder_type}) — attach, do not spawn."
        logger.warning("[presence_gate] BLOCKED: %s", reason)
        return {
            "exit_code": 2,
            "stdout": json.dumps({"decision": "block", "reason": reason}),
            "sound": "presence gate",
        }
    except Exception as exc:
        logger.warning("[presence_gate] gate error (allowing): %s", exc)
        return _ALLOW


def handle_stop(hook_data: dict) -> dict:
    """No-op on Stop. Presence is NOT released per-turn.

    Stop fires at the end of every assistant turn, not just session end.
    Releasing each turn would create a gap where a 2nd session wouldn't be blocked.
    Stale detection (dead claude PID) handles cleanup when the session truly exits.
    """
    return _ALLOW
