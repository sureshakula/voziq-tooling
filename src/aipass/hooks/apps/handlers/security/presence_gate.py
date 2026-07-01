# =================== AIPass ====================
# Name: presence_gate.py
# Version: 2.0.0
# Description: Single-session gate — blocks duplicate Claude runtimes per branch
# Branch: hooks
# Layer: apps/handlers/security
# Created: 2026-06-29
# Modified: 2026-06-30
# =============================================

"""Single-session gate — blocks duplicate Claude runtimes per branch.

Sources truth from CC-native ~/.claude/sessions/<pid>.json (resume-aware,
exit-aware) instead of PRESENCE.central.json. Resume-aware because /resume
keeps the same PID; exit-aware because CC deletes the file on clean exit.

Fires on UserPromptSubmit: checks CC sessions for another live brain in the
same branch. If occupied by a different PID, blocks. If free, allows.

handle_stop is a no-op (Stop fires every turn, not just session end; CC-native
session files handle cleanup on exit).

Skips sub-agents and dispatched/daemon session types.

PRESENCE.central.json + presence.py are preserved (not deleted) but the guard
no longer sources truth from them.
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

    Sources truth from CC-native ~/.claude/sessions/<pid>.json.
    Resume-aware: /resume keeps the same PID, so exclude_pid correctly
    identifies re-entry. Exit-aware: CC deletes the file on clean exit.
    """
    try:
        agent_type = hook_data.get("agent_type", "")
        if agent_type and agent_type != "main":
            return _ALLOW

        session_type = os.environ.get("AIPASS_SESSION_TYPE", "interactive")
        if session_type in _NON_BLOCKING_SESSION_TYPES:
            return _ALLOW

        branch = _resolve_branch(hook_data)
        branch_cwd = hook_data.get("cwd", "") or str(Path.cwd())

        presence = importlib.import_module("aipass.hooks.apps.modules.presence")
        our_pid = presence._resolve_session_pid()

        cc_sessions = importlib.import_module("aipass.hooks.apps.modules.cc_sessions")
        occupant = cc_sessions.find_occupant(branch_cwd, exclude_pid=our_pid)

        if occupant is None:
            return _ALLOW

        occ_pid = occupant.get("pid", "?")
        occ_name = occupant.get("name", "")
        reason = f"{branch} already live at PID {occ_pid}{f' ({occ_name})' if occ_name else ''} — attach, do not spawn."
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
    """No-op on Stop. CC-native session files handle cleanup on exit."""
    return _ALLOW
