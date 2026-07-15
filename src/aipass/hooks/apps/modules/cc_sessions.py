# =================== AIPass ====================
# Name: cc_sessions.py
# Version: 3.0.0
# Description: CC-native session discovery, listing, and reclaim
# Branch: hooks
# Layer: apps/modules
# Created: 2026-06-30
# Modified: 2026-07-14
# =============================================

"""Read Claude Code native session files (~/.claude/sessions/<pid>.json).

CC maintains one JSON file per running session at ~/.claude/sessions/<pid>.json.
These are resume-aware (sessionId updated on /resume), exit-aware (deleted on
clean exit, stale-swept by CC itself), and the authoritative source of which
sessions are live for a given working directory.

Used by presence_gate to source truth instead of PRESENCE.central.json.

Exposed as `drone @hooks sessions` (list) and
`drone @hooks sessions reclaim [@branch]` (proper-stop cleanup).
"""

import json
import os
import signal
import sys
from pathlib import Path

from aipass.cli.apps.modules import err_console
from aipass.prax.apps.modules.logger import system_logger as logger

CONSOLE = err_console

CC_SESSIONS_DIR = Path.home() / ".claude" / "sessions"

HELP_COMMANDS = [
    ("sessions", "List all CC sessions (PID · branch · short-id · kind · age)"),
    ("sessions reclaim [@branch]", "Properly stop sessions — clean slate"),
]


def _pid_alive_windows(pid: int) -> bool:
    """Windows-safe liveness check via OpenProcess + GetExitCodeProcess."""
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]  # Windows-only
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID exists."""
    if pid <= 1:
        return False
    if sys.platform == "win32":
        try:
            return _pid_alive_windows(pid)
        except Exception as exc:
            logger.info("[CC_SESSIONS] PID %d Windows check failed (assuming alive): %s", pid, exc)
            return True
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


def _format_age(session: dict) -> str:
    """Format session age from its start time."""
    started = session.get("startedAt") or session.get("started", "")
    if not started:
        return "?"
    try:
        from datetime import datetime, timezone

        if isinstance(started, (int, float)):
            start_dt = datetime.fromtimestamp(started / 1000, tz=timezone.utc)
        else:
            start_dt = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        delta = datetime.now(tz=timezone.utc) - start_dt
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    except Exception as exc:
        logger.info("[CC_SESSIONS] age format error: %s", exc)
        return "?"


def _session_branch(session: dict) -> str:
    """Extract the branch name from a session's cwd."""
    cwd = session.get("cwd", "")
    return Path(cwd).name if cwd else "?"


def _session_short_id(session: dict) -> str:
    """Extract short session ID (first 8 chars of sessionId)."""
    return str(session.get("sessionId", ""))[:8]


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


def _stop_session(session: dict) -> str:
    """Stop a session. Returns description of action taken.

    bg sessions: no per-job stop exists in the CLI. Returns an honest
    message — never SIGTERMs bg (daemon respawns it).
    """
    pid = session.get("pid")
    kind = session.get("kind", "unknown")
    branch = _session_branch(session)

    if kind in ("bg", "background"):
        logger.info("[CC_SESSIONS] Cannot stop bg PID %s — no per-job stop in CLI", pid)
        return f"PID {pid} ({branch}): bg session — no per-job stop available"

    if pid and _is_pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            logger.warning("[CC_SESSIONS] Failed to SIGTERM PID %d: %s", pid, exc)
            return f"PID {pid} ({branch}): SIGTERM failed ({exc})"
        return f"PID {pid} ({branch}): sent SIGTERM to {kind} session"
    return f"PID {pid} ({branch}): already dead"


def reclaim(branch_filter: str | None = None) -> list[str]:
    """Properly stop sessions, optionally filtered to a branch. Returns action log."""
    actions = []
    for session in read_all_sessions():
        pid = session.get("pid")
        if not pid or not _is_pid_alive(pid):
            continue
        if branch_filter and _session_branch(session) != branch_filter:
            continue
        action = _stop_session(session)
        actions.append(action)
        logger.info("[CC_SESSIONS] reclaim: %s", action)
    return actions


# =============================================================================
# MODULE INTERFACE (drone @hooks routing)
# =============================================================================


def _print_sessions_list():
    """Print all CC sessions in P6 format: PID · branch · short-id · kind · age."""
    sessions = read_all_sessions()
    if not sessions:
        CONSOLE.print("  No CC session files found")
        return
    for s in sessions:
        pid = s.get("pid", "?")
        branch = _session_branch(s)
        short_id = _session_short_id(s)
        kind = s.get("kind", "?")
        age = _format_age(s)
        alive = _is_pid_alive(pid) if isinstance(pid, int) else False
        status = "[green]live[/green]" if alive else "[dim]stale[/dim]"
        CONSOLE.print(f"  PID {pid} · {branch} · {short_id} · {kind} · {age}  {status}")


def print_introspection():
    """Print CC session state for drone routing."""
    CONSOLE.print("[bold cyan]sessions[/bold cyan] — CC session listing & reclaim")
    CONSOLE.print(f"  Sessions dir: {CC_SESSIONS_DIR}")
    _print_sessions_list()


def handle_command(command: str, args: list) -> bool:
    """Route sessions/cc_sessions commands from drone @hooks."""
    if command in ("--help", "-h", "help"):
        CONSOLE.print("[bold cyan]sessions[/bold cyan] — CC session listing & reclaim")
        CONSOLE.print()
        CONSOLE.print("  drone @hooks sessions                  List all CC sessions")
        CONSOLE.print("  drone @hooks sessions reclaim          Stop all live sessions")
        CONSOLE.print("  drone @hooks sessions reclaim @branch  Stop sessions for a branch")
        CONSOLE.print()
        CONSOLE.print("  drone @hooks cc_sessions               (legacy alias for sessions)")
        return True

    if command in ("sessions", "cc_sessions"):
        if not args:
            print_introspection()
            return True

        if args[0] == "reclaim":
            branch_filter = None
            if len(args) > 1:
                branch_filter = args[1].lstrip("@")
            CONSOLE.print(f"[bold cyan]sessions reclaim[/bold cyan]{f' @{branch_filter}' if branch_filter else ''}")
            actions = reclaim(branch_filter)
            if not actions:
                CONSOLE.print("  No live sessions to reclaim")
            else:
                for action in actions:
                    CONSOLE.print(f"  {action}")
            return True

    return False
