# =================== AIPass ====================
# Name: cc_sessions.py
# Version: 1.0.0
# Description: Read CC-native session files for active-session discovery
# Branch: hooks
# Layer: apps/modules
# Created: 2026-06-30
# Modified: 2026-06-30
# =============================================

"""Read Claude Code native session files (~/.claude/sessions/<pid>.json).

CC maintains one JSON file per running session at ~/.claude/sessions/<pid>.json.
These are resume-aware (sessionId updated on /resume), exit-aware (deleted on
clean exit, stale-swept by CC itself), and the authoritative source of which
sessions are live for a given working directory.

Used by presence_gate to source truth instead of PRESENCE.central.json.
"""

import json
import os
from pathlib import Path

from aipass.cli.apps.modules import err_console
from aipass.prax.apps.modules.logger import system_logger as logger

CONSOLE = err_console

CC_SESSIONS_DIR = Path.home() / ".claude" / "sessions"


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID exists."""
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        logger.info("[CC_SESSIONS] PID %d not found (dead)", pid)
        return False
    except PermissionError:
        logger.info("[CC_SESSIONS] PID %d exists but permission denied — treating as alive", pid)
        return True
    except OSError as exc:
        logger.info("[CC_SESSIONS] PID %d os.kill failed: %s — treating as dead", pid, exc)
        return False


def read_all_sessions() -> list[dict]:
    """Read all CC session PID files. Returns list of session dicts."""
    if not CC_SESSIONS_DIR.is_dir():
        return []
    sessions = []
    for f in CC_SESSIONS_DIR.iterdir():
        if not f.name.endswith(".json") or not f.stem.isdigit():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.info("[CC_SESSIONS] Failed to read %s: %s", f, exc)
    return sessions


def find_live_for_cwd(cwd: str) -> list[dict]:
    """Find all live CC sessions whose cwd matches the given directory.

    Compares resolved paths for robustness (symlinks, trailing slashes).
    Only returns sessions whose PID is still alive.
    """
    target = str(Path(cwd).resolve())
    live = []
    for session in read_all_sessions():
        session_cwd = session.get("cwd", "")
        if not session_cwd:
            continue
        if str(Path(session_cwd).resolve()) != target:
            continue
        pid = session.get("pid")
        if pid and _is_pid_alive(pid):
            live.append(session)
        else:
            logger.info(
                "[CC_SESSIONS] Stale session file for PID %s at %s",
                pid,
                session_cwd,
            )
    return live


def find_occupant(cwd: str, exclude_pid: int | None = None) -> dict | None:
    """Find a live CC session occupying the given cwd, excluding our own PID.

    Returns the first occupant session dict, or None if the branch is free.
    This is resume-aware: /resume keeps the same PID, so exclude_pid correctly
    identifies re-entry.
    """
    for session in find_live_for_cwd(cwd):
        if exclude_pid is not None and session.get("pid") == exclude_pid:
            continue
        return session
    return None


# =============================================================================
# MODULE INTERFACE (drone @hooks routing)
# =============================================================================


def print_introspection():
    """Print CC session state for drone routing."""
    CONSOLE.print("[bold cyan]cc_sessions[/bold cyan] Module")
    CONSOLE.print(f"  Sessions dir: {CC_SESSIONS_DIR}")
    try:
        sessions = read_all_sessions()
        if not sessions:
            CONSOLE.print("  No CC session files found")
        else:
            for s in sessions:
                pid = s.get("pid", "?")
                cwd = s.get("cwd", "?")
                kind = s.get("kind", "?")
                name = s.get("name", "")
                alive = _is_pid_alive(pid) if isinstance(pid, int) else False
                status = "[green]live[/green]" if alive else "[dim]stale[/dim]"
                label = f" ({name})" if name else ""
                CONSOLE.print(f"  PID {pid}{label}: {Path(cwd).name}  kind={kind}  {status}")
    except Exception as exc:
        logger.info("[CC_SESSIONS] introspection error: %s", exc)
        CONSOLE.print(f"  Error reading sessions: {exc}")


def handle_command(command: str, args: list) -> bool:
    """Route cc_sessions commands from drone @hooks."""
    if command in ("--help", "-h", "help"):
        CONSOLE.print("[bold cyan]cc_sessions[/bold cyan] — CC-native session file reader")
        CONSOLE.print()
        CONSOLE.print("  drone @hooks cc_sessions    Show live CC sessions")
        return True

    if command == "cc_sessions":
        if not args:
            print_introspection()
            return True

    return False
