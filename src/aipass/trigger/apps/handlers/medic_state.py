# =================== AIPass ====================
# Name: medic_state.py
# Description: Medic state persistence and status collection handler
# Version: 1.1.0
# Created: 2026-02-12
# Modified: 2026-02-12
# =============================================

"""
Medic State Handler - Persistence and status for Medic toggle

Reads/writes medic_enabled flag and muted_branches list in trigger_config.json.
Collects status data from suppression logs and rate limit logs.

Architecture:
    Module (medic.py) orchestrates, this handler manages state.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from aipass.prax.apps.modules.logger import get_direct_logger
from aipass.trigger.apps.config import TRIGGER_ROOT, atomic_write_json, json_file_lock
from aipass.trigger.apps.handlers.json import json_handler

logger = get_direct_logger()

TRIGGER_CONFIG_FILE = TRIGGER_ROOT / "trigger_json" / "trigger_config.json"
MEDIC_SUPPRESSED_LOG = TRIGGER_ROOT / "logs" / "medic_suppressed.jsonl"
RATE_LIMITED_LOG = TRIGGER_ROOT / "logs" / "rate_limited.jsonl"

_DURATION_RE = re.compile(r"^(\d+)(h|d)$")

DEFAULT_MUTE_SECONDS = 86400  # 24 hours
DEFAULT_OFF_SECONDS = 86400  # 24 hours


def parse_duration(duration_str: str) -> Optional[float]:
    """Parse a duration string like '24h', '48h', '7d' into seconds.

    Args:
        duration_str: Duration with unit suffix (h=hours, d=days)

    Returns:
        Seconds as float, or None if unparseable
    """
    m = _DURATION_RE.match(duration_str.strip())
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    if unit == "h":
        return float(value * 3600)
    return float(value * 86400)


def _is_mute_active(entry, now: datetime) -> bool:
    """Check if a single mute entry is still active."""
    if isinstance(entry, str):
        return True
    if not isinstance(entry, dict):
        return False
    expires_at = entry.get("expires_at")
    if expires_at is None:
        return True
    return datetime.fromisoformat(expires_at) > now


def _clean_expired_mutes(data: dict) -> None:
    """Remove expired mute entries from config data in-place."""
    config = data.get("config", {})
    muted = config.get("muted_branches", [])
    if not muted:
        return
    now = datetime.now()
    config["muted_branches"] = [e for e in muted if _is_mute_active(e, now)]


def read_config() -> dict:
    """
    Read trigger_config.json.

    Returns:
        Parsed config dict, or empty dict on failure
    """
    try:
        if TRIGGER_CONFIG_FILE.exists():
            return json.loads(TRIGGER_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("read_config failed: %s", exc)
        return {}
    return {}


def write_config(data: dict) -> bool:
    """
    Write trigger_config.json. Cleans expired mute entries before writing.

    Args:
        data: Config dict to persist

    Returns:
        True on success, False on failure
    """
    try:
        _clean_expired_mutes(data)
        atomic_write_json(TRIGGER_CONFIG_FILE, data)
        return True
    except Exception as exc:
        logger.warning("write_config failed: %s", exc)
        return False


def is_enabled() -> bool:
    """
    Check if Medic is currently enabled.

    If disabled with a TTL (medic_disabled_until), treats an expired
    TTL as enabled — evaluate on read, no timers.

    Returns:
        True if medic_enabled is True or its TTL has expired
    """
    data = read_config()
    config = data.get("config", {})
    enabled = bool(config.get("medic_enabled", True))
    if not enabled:
        disabled_until = config.get("medic_disabled_until")
        if disabled_until:
            if datetime.fromisoformat(disabled_until) <= datetime.now():
                return True
    return enabled


def get_disabled_until() -> Optional[str]:
    """Get the medic_disabled_until timestamp if set.

    Returns:
        ISO timestamp string, or None if not set or permanent off
    """
    data = read_config()
    return data.get("config", {}).get("medic_disabled_until")


def set_enabled(enabled: bool, duration_seconds: Optional[float] = None) -> bool:
    """
    Set medic_enabled flag in config.

    When disabling with a duration, stores medic_disabled_until so the
    off state auto-expires. When enabling, clears any stored expiry.

    Args:
        enabled: True to enable, False to disable
        duration_seconds: TTL in seconds for disable (None = permanent)

    Returns:
        True on success
    """
    with json_file_lock(TRIGGER_CONFIG_FILE):
        data = read_config()
        if "config" not in data:
            data["config"] = {}
        data["config"]["medic_enabled"] = enabled
        if not enabled and duration_seconds is not None:
            expires = datetime.now() + timedelta(seconds=duration_seconds)
            data["config"]["medic_disabled_until"] = expires.isoformat()
        else:
            data["config"].pop("medic_disabled_until", None)
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d")

        if write_config(data):
            json_handler.log_operation("state_persisted", {"key": "medic_enabled", "value": enabled})
            return True
    return False


def _normalize_branch_name(name: str) -> str:
    """
    Normalize a branch name - strip @, extract from path if needed.

    Args:
        name: Raw branch name (could be path, @-prefixed, etc.)

    Returns:
        Lowercase branch name (e.g., 'speakeasy')
    """
    cleaned = name.lstrip("@")
    if "/" in cleaned:
        cleaned = Path(cleaned).name
    return cleaned.lower()


def get_muted_branches() -> List[str]:
    """
    Get list of currently active muted branch names.

    Evaluates TTL expiry on read — expired mutes are filtered out.

    Returns:
        List of muted branch names (lowercase, e.g., ['speakeasy', 'api'])
    """
    data = read_config()
    raw = data.get("config", {}).get("muted_branches", [])
    now = datetime.now()
    result = []
    for entry in raw:
        if isinstance(entry, str):
            result.append(_normalize_branch_name(entry))
        elif isinstance(entry, dict):
            expires_at = entry.get("expires_at")
            if expires_at is None or datetime.fromisoformat(expires_at) > now:
                result.append(_normalize_branch_name(entry.get("name", "")))
    return result


def get_muted_branches_detail() -> List[Dict[str, Any]]:
    """
    Get muted branches with expiry info for status display.

    Returns active mutes only (expired ones filtered out).

    Returns:
        List of dicts with 'name' and 'expires_at' (None = permanent)
    """
    data = read_config()
    raw = data.get("config", {}).get("muted_branches", [])
    now = datetime.now()
    result = []
    for entry in raw:
        if isinstance(entry, str):
            result.append({"name": _normalize_branch_name(entry), "expires_at": None})
        elif isinstance(entry, dict):
            expires_at = entry.get("expires_at")
            if expires_at is None or datetime.fromisoformat(expires_at) > now:
                result.append(
                    {
                        "name": _normalize_branch_name(entry.get("name", "")),
                        "expires_at": expires_at,
                    }
                )
    return result


def _mute_entry_name(entry) -> str:
    """Extract the normalized branch name from a mute entry (string or dict)."""
    if isinstance(entry, str):
        return _normalize_branch_name(entry)
    if isinstance(entry, dict):
        return _normalize_branch_name(entry.get("name", ""))
    return ""


def mute_branch(branch_name: str, duration_seconds: Optional[float] = None) -> bool:
    """
    Add a branch to the muted list with optional TTL.

    Muted branches will have errors detected but NOT dispatched.
    Persists in trigger_config.json.

    Args:
        branch_name: Branch name (with or without @)
        duration_seconds: TTL in seconds (None = permanent/forever)

    Returns:
        True on success
    """
    clean = _normalize_branch_name(branch_name)
    with json_file_lock(TRIGGER_CONFIG_FILE):
        data = read_config()
        if "config" not in data:
            data["config"] = {}
        raw_muted = data["config"].get("muted_branches", [])
        new_muted = [e for e in raw_muted if _mute_entry_name(e) != clean]
        if duration_seconds is not None:
            expires = datetime.now() + timedelta(seconds=duration_seconds)
            new_muted.append({"name": clean, "expires_at": expires.isoformat()})
        else:
            new_muted.append({"name": clean, "expires_at": None})
        data["config"]["muted_branches"] = new_muted
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d")
        return write_config(data)


def unmute_branch(branch_name: str) -> bool:
    """
    Remove a branch from the muted list.

    Args:
        branch_name: Branch name (with or without @)

    Returns:
        True on success
    """
    clean = _normalize_branch_name(branch_name)
    with json_file_lock(TRIGGER_CONFIG_FILE):
        data = read_config()
        if "config" not in data:
            data["config"] = {}
        raw_muted = data["config"].get("muted_branches", [])
        data["config"]["muted_branches"] = [e for e in raw_muted if _mute_entry_name(e) != clean]
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d")
        return write_config(data)


def get_suppression_stats() -> Dict[str, Any]:
    """
    Get suppression log statistics.

    Returns:
        Dict with suppressed_count and last_suppressed timestamp
    """
    suppressed_count = 0
    last_suppressed = "never"
    try:
        if MEDIC_SUPPRESSED_LOG.exists():
            lines = MEDIC_SUPPRESSED_LOG.read_text(encoding="utf-8").strip().splitlines()
            suppressed_count = len(lines)
            if lines:
                entry = json.loads(lines[-1])
                last_suppressed = entry.get("ts", "unknown")
    except Exception as exc:
        logger.warning("get_suppression_stats failed: %s", exc)
        return {"suppressed_count": 0, "last_suppressed": "error reading log"}

    return {
        "suppressed_count": suppressed_count,
        "last_suppressed": last_suppressed,
    }


def get_rate_limit_stats() -> Dict[str, Any]:
    """
    Get rate limit log statistics.

    Returns:
        Dict with rate_limited_count and last_rate_limited timestamp
    """
    dispatch_count = 0
    last_dispatch = "never"
    try:
        if RATE_LIMITED_LOG.exists():
            lines = RATE_LIMITED_LOG.read_text(encoding="utf-8").strip().splitlines()
            dispatch_count = len(lines)
            if lines:
                entry = json.loads(lines[-1])
                last_dispatch = entry.get("ts", "unknown")
    except Exception as exc:
        logger.warning("get_rate_limit_stats failed: %s", exc)
        return {"rate_limited_count": 0, "last_rate_limited": "error reading log"}

    return {
        "rate_limited_count": dispatch_count,
        "last_rate_limited": last_dispatch,
    }
