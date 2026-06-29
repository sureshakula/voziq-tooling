# =================== AIPass ====================
# Name: presence.py
# Version: 1.0.0
# Description: Branch presence service — claim/release/refresh for .ai_central/PRESENCE.central.json
# Branch: hooks
# Layer: apps/modules
# Created: 2026-06-29
# Modified: 2026-06-29
# =============================================

"""Branch presence service for concurrent session detection.

Manages a shared PRESENCE.central.json in .ai_central/ at the AIPass project root.
Each branch can claim presence (one live session per branch), detect stale holders
via PID liveness + /proc/cwd verification, and release on exit.

File locking uses flock (POSIX) / msvcrt (Windows) to prevent concurrent corruption.
"""

import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from aipass.cli.apps.modules import err_console
from aipass.prax.apps.modules.logger import system_logger as logger

CONSOLE = err_console

# Cross-platform flock
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _find_ai_central() -> Path:
    """Walk up from this file to find the directory containing .ai_central/."""
    current = Path(__file__).resolve().parent
    for _ in range(20):  # safety cap
        candidate = current / ".ai_central"
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError("Cannot locate .ai_central/ directory from presence module")


_PRESENCE_FILE_NAME = "PRESENCE.central.json"
_LOCK_FILE_NAME = ".presence.lock"


def _presence_path() -> Path:
    """Return path to the PRESENCE.central.json file."""
    return _find_ai_central() / _PRESENCE_FILE_NAME


def _lock_path() -> Path:
    """Return path to the .presence.lock file."""
    return _find_ai_central() / _LOCK_FILE_NAME


# ---------------------------------------------------------------------------
# File locking context manager
# ---------------------------------------------------------------------------


def _release_lock_fd(lock_fd) -> None:
    """Release and close a lock file descriptor."""
    try:
        if sys.platform == "win32":
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()
    except Exception as exc:
        logger.warning("[PRESENCE] lock release failed: %s", exc)
        try:
            lock_fd.close()
        except Exception as close_exc:
            logger.warning("[PRESENCE] lock file close failed: %s", close_exc)


@contextmanager
def _presence_lock():
    """Acquire exclusive lock on the presence file for read-modify-write."""
    lock_file = _lock_path()
    lock_fd = None
    try:
        lock_fd = open(lock_file, "w", encoding="utf-8")
        if sys.platform == "win32":
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if lock_fd is not None:
            _release_lock_fd(lock_fd)


# ---------------------------------------------------------------------------
# JSON read/write helpers
# ---------------------------------------------------------------------------


def _read_presence() -> dict:
    """Read the presence JSON. Returns empty dict if missing or corrupt."""
    fp = _presence_path()
    if not fp.exists():
        return {}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("[PRESENCE] Failed to read %s: %s", fp, exc)
        return {}


def _write_presence(data: dict) -> None:
    """Write the presence JSON."""
    fp = _presence_path()
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Liveness detection
# ---------------------------------------------------------------------------


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID exists."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        logger.info("[PRESENCE] PID %d not found (dead)", pid)
        return False
    except PermissionError:
        # Process exists but we can't signal it — treat as alive
        logger.info("[PRESENCE] PID %d exists but permission denied — treating as alive", pid)
        return True
    except OSError as exc:
        logger.info("[PRESENCE] PID %d os.kill failed: %s — treating as dead", pid, exc)
        return False


def _cwd_matches(pid: int, expected_dir: str) -> bool:
    """Check if the process CWD matches the expected branch directory.

    Linux only — reads /proc/<pid>/cwd.
    On non-Linux platforms, returns True (skip the check, rely on os.kill alone).
    """
    if sys.platform != "linux":
        return True
    try:
        actual_cwd = os.readlink(f"/proc/{pid}/cwd")
        return str(Path(actual_cwd).resolve()) == str(Path(expected_dir).resolve())
    except (OSError, PermissionError):
        # Cannot read /proc — be conservative, treat as NOT matching (stale)
        logger.info("[PRESENCE] Cannot read /proc/%d/cwd — treating as stale", pid)
        return False


def _is_holder_alive(entry: dict) -> bool:
    """Determine if the holder recorded in the presence entry is still alive.

    A holder is alive if:
      1. The PID exists (os.kill signal 0)
      2. AND the PID's CWD matches the branch work_dir (Linux /proc check)

    If either check fails, the holder is stale and can be reclaimed.
    """
    pid = entry.get("pid")
    if pid is None:
        return False
    if not _is_pid_alive(pid):
        return False
    work_dir = entry.get("work_dir", "")
    if not work_dir:
        return False
    return _cwd_matches(pid, work_dir)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def claim(
    branch: str,
    session_id: str = "",
    session_type: str = "interactive",
    attach_handle: str = "",
) -> dict:
    """Claim presence for a branch.

    Returns:
        {"status": "ACQUIRED"} on success, or
        {"status": "OCCUPIED", "pid": N, "session_id": "...",
         "work_dir": "...", "session_type": "..."}
        when a live session already owns the branch.
    """
    my_pid = os.getpid()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    cwd = os.getcwd()

    with _presence_lock():
        data = _read_presence()
        existing = data.get(branch)

        if existing:
            result = _handle_existing(data, existing, branch, my_pid, now, session_id)
            if result is not None:
                return result

        # No existing entry or stale holder — write the new entry
        data[branch] = {
            "pid": my_pid,
            "session_id": session_id,
            "work_dir": cwd,
            "session_type": session_type,
            "attach_handle": attach_handle,
            "started": now,
            "last_seen": now,
        }
        _write_presence(data)
        logger.info("[PRESENCE] Acquired %s (PID %d)", branch, my_pid)
        return {"status": "ACQUIRED"}


def _handle_existing(
    data: dict,
    existing: dict,
    branch: str,
    my_pid: int,
    now: str,
    session_id: str,
) -> dict | None:
    """Handle an existing presence entry. Returns a result dict or None to proceed."""
    holder_pid = existing.get("pid")

    # Re-entry: same PID already holds it
    if holder_pid == my_pid:
        existing["last_seen"] = now
        existing["session_id"] = session_id or existing.get("session_id", "")
        _write_presence(data)
        logger.info("[PRESENCE] Re-entry for %s (PID %d)", branch, my_pid)
        return {"status": "ACQUIRED"}

    # Check if the holder is still alive
    if _is_holder_alive(existing):
        logger.info(
            "[PRESENCE] %s occupied by PID %d (session_type=%s)",
            branch,
            holder_pid,
            existing.get("session_type", "unknown"),
        )
        return {
            "status": "OCCUPIED",
            "pid": holder_pid,
            "session_id": existing.get("session_id", ""),
            "work_dir": existing.get("work_dir", ""),
            "session_type": existing.get("session_type", ""),
        }

    # Stale holder — let caller reclaim
    logger.info(
        "[PRESENCE] Stale holder for %s (PID %d) — reclaiming",
        branch,
        holder_pid,
    )
    return None


def release(branch: str) -> bool:
    """Release presence for a branch. Only the holder PID can release its own entry."""
    my_pid = os.getpid()
    with _presence_lock():
        data = _read_presence()
        if branch not in data:
            return False
        if data[branch].get("pid") != my_pid:
            logger.info(
                "[PRESENCE] Release skipped for %s — not our PID (ours=%d, holder=%d)",
                branch,
                my_pid,
                data[branch].get("pid", 0),
            )
            return False
        del data[branch]
        _write_presence(data)
        logger.info("[PRESENCE] Released %s (PID %d)", branch, my_pid)
        return True


def refresh(branch: str) -> None:
    """Update last_seen timestamp for the branch entry."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with _presence_lock():
        data = _read_presence()
        if branch in data:
            data[branch]["last_seen"] = now
            _write_presence(data)
            logger.info("[PRESENCE] Refreshed %s", branch)


def read_all() -> dict:
    """Return the full presence JSON (all branches)."""
    return _read_presence()


# =============================================================================
# MODULE INTERFACE (drone @hooks routing)
# =============================================================================


def print_introspection() -> None:
    """Print presence state for drone routing."""
    CONSOLE.print("[bold cyan]presence[/bold cyan] Module")
    try:
        data = _read_presence()
        if not data:
            CONSOLE.print("  No branches currently present")
        else:
            for branch, entry in data.items():
                pid = entry.get("pid", "?")
                stype = entry.get("session_type", "unknown")
                last = entry.get("last_seen", "?")
                alive = _is_holder_alive(entry)
                status = "[green]live[/green]" if alive else "[dim]stale[/dim]"
                CONSOLE.print(f"  {branch}: PID {pid}  type={stype}  last_seen={last}  {status}")
    except FileNotFoundError as exc:
        logger.info("[PRESENCE] introspection: %s", exc)
        CONSOLE.print("  .ai_central/ not found")


def handle_command(command: str, args: list) -> bool:
    """Route presence commands from drone @hooks."""
    if command in ("--help", "-h", "help"):
        CONSOLE.print("[bold cyan]presence[/bold cyan] — Branch presence claim/release service")
        CONSOLE.print()
        CONSOLE.print("  drone @hooks presence    Show current presence state for all branches")
        return True

    if command == "presence":
        if not args:
            print_introspection()
            return True
    return False
