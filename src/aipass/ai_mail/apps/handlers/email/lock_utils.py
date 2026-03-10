# =================== AIPass ====================
# Name: lock_utils.py
# Description: Dispatch Lock Handler
# Version: 1.1.0
# Created: 2026-02-09
# Modified: 2026-02-09
# =============================================

"""
Dispatch Lock Handler

PID-based single instance lock per branch.
Prevents multiple dispatch agents from spawning concurrently at the same branch.
Uses atomic file creation (O_CREAT|O_EXCL) to avoid race conditions.
"""

import os
import json
from pathlib import Path
from datetime import datetime

# Standard logging

# Lock file name - placed in branch's .ai_mail.local/ directory
LOCK_FILENAME = ".dispatch.lock"

# Stale lock timeout in seconds (10 minutes)
STALE_LOCK_TIMEOUT = 600


def _get_lock_path(branch_path: Path) -> Path:
    """Get the lock file path for a branch."""
    if branch_path == Path("/"):
        return Path.cwd() / ".ai_mail.local" / LOCK_FILENAME
    return branch_path / ".ai_mail.local" / LOCK_FILENAME


def _is_pid_running(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # Process exists but we don't have permission to signal it
        return True
    except ProcessLookupError:
        return False


def _is_lock_stale(lock_data: dict) -> bool:
    """
    Check if a lock is stale (process dead or timeout exceeded).

    Returns True if the lock should be considered stale and can be removed.
    """
    pid = lock_data.get("pid")
    timestamp = lock_data.get("timestamp")

    # No PID = stale
    if pid is None:
        return True

    # Process no longer running = stale
    if not _is_pid_running(pid):
        return True  # Process no longer running - stale

    # Timeout check - if lock is older than STALE_LOCK_TIMEOUT, consider stale
    if timestamp:
        try:
            lock_time = datetime.fromisoformat(timestamp)
            elapsed = (datetime.now() - lock_time).total_seconds()
            if elapsed > STALE_LOCK_TIMEOUT:
                return True  # Timeout exceeded - stale
        except (ValueError, TypeError) as e:
            pass  # Unparseable timestamp - ignore

    return False


def acquire_lock(branch_path: Path, pid: int) -> tuple[bool, str]:
    """
    Attempt to acquire a dispatch lock for a branch.

    Uses atomic file creation to prevent race conditions.

    Args:
        branch_path: Path to the target branch
        pid: PID of the agent being spawned

    Returns:
        Tuple of (acquired: bool, message: str)
        If not acquired, message contains reason (e.g., existing PID info)
    """
    lock_path = _get_lock_path(branch_path)

    # Ensure parent directory exists
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for existing lock first
    if lock_path.exists():
        try:
            with open(lock_path, 'r', encoding='utf-8') as f:
                existing_lock = json.load(f)

            if _is_lock_stale(existing_lock):
                # Remove stale lock and try again
                lock_path.unlink(missing_ok=True)  # Remove stale lock
            else:
                # Active lock exists - bounce
                existing_pid = existing_lock.get("pid", "unknown")
                existing_sender = existing_lock.get("sender", "unknown")
                existing_time = existing_lock.get("timestamp", "unknown")
                msg = f"Branch already has active dispatch agent (PID: {existing_pid}, sender: {existing_sender}, since: {existing_time})"
                return False, msg

        except (json.JSONDecodeError, OSError) as e:
            # Corrupted lock file - remove it
            lock_path.unlink(missing_ok=True)  # Corrupted lock - remove it

    # Create lock file atomically using O_CREAT|O_EXCL
    lock_data = {
        "pid": pid,
        "timestamp": datetime.now().isoformat(),
        "branch": str(branch_path)
    }

    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            os.write(fd, json.dumps(lock_data, indent=2).encode('utf-8'))
        finally:
            os.close(fd)

        return True, "Lock acquired"

    except FileExistsError:
        # Race condition - another process created the lock between our check and create
        msg = "Lock acquisition failed - another dispatch just started"
        return False, msg


def release_lock(branch_path: Path, pid: int | None = None) -> bool:
    """
    Release a dispatch lock for a branch.

    Args:
        branch_path: Path to the target branch
        pid: If provided, only release if lock belongs to this PID (safety check)

    Returns:
        True if lock was released, False if not found or owned by different PID
    """
    lock_path = _get_lock_path(branch_path)

    if not lock_path.exists():
        return True  # No lock = already released

    # If PID specified, verify ownership before releasing
    if pid is not None:
        try:
            with open(lock_path, 'r', encoding='utf-8') as f:
                lock_data = json.load(f)
            if lock_data.get("pid") != pid:
                return False  # Lock owned by different PID
        except (json.JSONDecodeError, OSError) as e:
            pass  # Corrupted lock file during release - continue anyway

    try:
        lock_path.unlink(missing_ok=True)
        return True
    except OSError as e:
        return False  # Failed to release lock


def check_lock(branch_path: Path) -> dict | None:
    """
    Check if a branch has an active dispatch lock.

    Returns:
        Lock data dict if active lock exists, None otherwise.
        Automatically cleans up stale locks.
    """
    lock_path = _get_lock_path(branch_path)

    if not lock_path.exists():
        return None

    try:
        with open(lock_path, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)

        if _is_lock_stale(lock_data):
            # Auto-cleanup stale lock
            lock_path.unlink(missing_ok=True)  # Auto-cleaned stale lock
            return None

        return lock_data

    except (json.JSONDecodeError, OSError):
        # Corrupted - clean up
        lock_path.unlink(missing_ok=True)
        return None
