# =================== AIPass ====================
# Name: response_router.py
# Description: CWD-safe response routing for multi-bot architecture
# Version: 1.0.0
# Created: 2026-02-24
# Modified: 2026-06-15
# =============================================

"""
CWD-Safe Response Routing for Multi-Bot Architecture

Fixes the CWD mismatch bug in the Stop hook. When Claude fires the Stop hook,
the working directory may be a subdirectory of the branch root rather than the
branch root itself. The old logic used Path.cwd().name which fails in
subdirectories.

New logic uses cwd.relative_to(work_dir) which succeeds if CWD is ANYWHERE
in the bot's directory tree.

Pending file naming:
- v2 (new): bot-{bot_id}.json
- v1 (legacy): telegram-{branch_name}.json
Both formats are supported during the transition period.
"""

# Standard library
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

# Logging (Prax system_logger — FPLAN-0382)
from aipass.prax import logger

# JSON handler (seedgo standard)
from aipass.skills.apps.handlers.json import json_handler  # noqa: F401

# =============================================
# CONSTANTS
# =============================================

PENDING_DIR = Path.home() / ".aipass" / "telegram_pending"
PENDING_TTL = 3600  # 1 hour


# =============================================
# DIRECTORY TREE MATCHING
# =============================================


def is_cwd_in_tree(cwd: Path, work_dir) -> bool:
    """
    Check if cwd is within work_dir's directory tree using relative_to().

    This is the core fix for the CWD mismatch bug. Instead of comparing
    directory names (which fails in subdirectories), we check if cwd is
    a child of work_dir at any depth.

    Args:
        cwd: Current working directory to check.
        work_dir: Bot's configured working directory (str or Path).

    Returns:
        True if cwd is within work_dir's tree, False otherwise.
    """
    try:
        cwd.relative_to(Path(work_dir))
        return True
    except ValueError:
        logger.info("CWD %s is not within work_dir %s", cwd, work_dir)
        return False


# =============================================
# TMUX SESSION CHECKING
# =============================================


def is_tmux_alive(session_name: str) -> bool:
    """
    Check if a tmux session exists.

    Args:
        session_name: Name of the tmux session to check.

    Returns:
        True if the session exists, False otherwise.
    """
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("tmux check failed for session %s: %s", session_name, e)
        return False


# =============================================
# PENDING FILE EXPIRY
# =============================================


def is_pending_expired(pending_data: dict) -> bool:
    """
    Check if a pending file is expired.

    A pending file is considered expired only when BOTH conditions are met:
    1. The timestamp is older than PENDING_TTL seconds
    2. The associated tmux session is no longer alive

    This prevents premature cleanup of pending files for long-running sessions.

    Args:
        pending_data: Parsed contents of a pending file.

    Returns:
        True if the pending file should be cleaned up, False otherwise.
    """
    # Condition 1: Check TTL
    timestamp = pending_data.get("timestamp", 0)
    if isinstance(timestamp, str):
        try:
            timestamp = float(timestamp)
        except ValueError:
            timestamp = 0

    if time.time() - timestamp <= PENDING_TTL:
        return False  # Still within TTL, not expired

    # Condition 2: Check tmux session
    # Derive session name from bot_id or branch_name
    bot_id = pending_data.get("bot_id", "")
    branch_name = pending_data.get("branch_name", "")

    # Try the bot_id-based tmux session name first (v2)
    if bot_id:
        if is_tmux_alive(f"telegram-{bot_id}"):
            return False  # Session alive, not expired

    # Try the branch-based tmux session name (v1)
    if branch_name and branch_name != bot_id:
        if is_tmux_alive(f"telegram-{branch_name}"):
            return False  # Session alive, not expired

    # Past TTL AND no tmux session alive
    return True


# =============================================
# PENDING FILE LOADING
# =============================================


def _load_pending_file(pending_path: Path) -> Optional[dict]:
    """
    Load and parse a pending file from disk.

    Args:
        pending_path: Path to the pending JSON file.

    Returns:
        Parsed dict with "pending_path" key added, or None on error.
    """
    try:
        data = json.loads(pending_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        data["pending_path"] = str(pending_path)
        return data
    except (json.JSONDecodeError, OSError):
        return None


# =============================================
# MAIN ROUTING LOGIC
# =============================================


def find_pending_bot(
    cwd: Optional[Path] = None,
    session_id: Optional[str] = None,
    env_bot_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Find which bot's pending file matches the current context.

    Uses a priority-based matching strategy:

    Priority 1: AIPASS_BOT_ID env var (set in tmux session by BaseBot)
        Direct match: look for bot-{env_bot_id}.json

    Priority 2: cwd.relative_to(work_dir) - CWD anywhere in bot's directory tree
        Load each pending file, check if cwd is within its work_dir

    Priority 3: session_id match - fallback for legacy compatibility
        Check session_id field in each pending file

    Args:
        cwd: Current working directory. Defaults to Path.cwd().
        session_id: Claude Code session ID for fallback matching.
        env_bot_id: Bot ID from environment. Defaults to AIPASS_BOT_ID env var.

    Returns:
        Pending file data dict with "pending_path" key, or None if no match.
    """
    if not PENDING_DIR.exists():
        return None

    if cwd is None:
        try:
            cwd = Path.cwd()
        except OSError:
            cwd = Path.home()

    if env_bot_id is None:
        env_bot_id = os.environ.get("AIPASS_BOT_ID")

    # Priority 1: Direct match via AIPASS_BOT_ID env var
    if env_bot_id:
        # v2 naming: bot-{bot_id}.json
        PENDING_V2 = PENDING_DIR / f"bot-{env_bot_id}.json"
        if PENDING_V2.exists():
            data = _load_pending_file(PENDING_V2)
            if data and not is_pending_expired(data):
                logger.info("Matched pending by AIPASS_BOT_ID: %s", env_bot_id)
                return data

        # Also check v1 naming for this bot_id
        PENDING_V1 = PENDING_DIR / f"telegram-{env_bot_id}.json"
        if PENDING_V1.exists():
            data = _load_pending_file(PENDING_V1)
            if data and not is_pending_expired(data):
                logger.info("Matched pending by AIPASS_BOT_ID (v1 naming): %s", env_bot_id)
                return data

    # Priority 2: CWD directory tree matching
    # Check all pending files and see if CWD is within any bot's work_dir
    ALL_PENDING = list(PENDING_DIR.glob("bot-*.json")) + list(PENDING_DIR.glob("telegram-*.json"))

    for pending_path in ALL_PENDING:
        data = _load_pending_file(pending_path)
        if not data:
            continue

        if is_pending_expired(data):
            continue

        work_dir = data.get("work_dir", "")
        if work_dir and is_cwd_in_tree(cwd, work_dir):
            logger.info("Matched pending by CWD tree: cwd=%s within work_dir=%s", cwd, work_dir)
            return data

        # Legacy v1 files may not have work_dir - try branch_name directory matching
        branch_name = data.get("branch_name", "")
        if branch_name and not work_dir:
            # CWD's directory name or any parent matches branch_name
            path_cursor = cwd
            while path_cursor != path_cursor.parent:
                if path_cursor.name == branch_name:
                    logger.info("Matched pending by branch name in CWD path: %s", branch_name)
                    return data
                path_cursor = path_cursor.parent

    # Priority 3: Session ID fallback
    if session_id:
        for pending_path in ALL_PENDING:
            data = _load_pending_file(pending_path)
            if not data:
                continue

            if is_pending_expired(data):
                continue

            if data.get("session_id") == session_id:
                logger.info("Matched pending by session_id: %s", session_id[:8])
                return data

    return None


# =============================================
# CLEANUP
# =============================================


def clean_expired_pending() -> int:
    """
    Remove all expired pending files from the pending directory.

    A file is expired when it is past TTL AND its tmux session is dead.

    Returns:
        Number of expired files removed.
    """
    if not PENDING_DIR.exists():
        return 0

    REMOVED_COUNT = 0
    ALL_PENDING = list(PENDING_DIR.glob("bot-*.json")) + list(PENDING_DIR.glob("telegram-*.json"))

    for pending_path in ALL_PENDING:
        data = _load_pending_file(pending_path)
        if not data:
            # Corrupt or unreadable file - remove it
            try:
                pending_path.unlink(missing_ok=True)
                REMOVED_COUNT += 1
                logger.info("Removed corrupt pending file: %s", pending_path.name)
            except OSError as e:
                logger.warning("Failed to remove corrupt pending file %s: %s", pending_path.name, e)
            continue

        if is_pending_expired(data):
            try:
                pending_path.unlink(missing_ok=True)
                REMOVED_COUNT += 1
                logger.info("Removed expired pending file: %s", pending_path.name)
            except OSError as e:
                logger.warning("Failed to remove expired pending file %s: %s", pending_path.name, e)

    if REMOVED_COUNT > 0:
        logger.info("Cleaned %d expired pending file(s)", REMOVED_COUNT)

    return REMOVED_COUNT
