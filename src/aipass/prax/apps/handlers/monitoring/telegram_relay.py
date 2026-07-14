# =================== AIPass ====================
# Name: telegram_relay.py
# Description: Telegram relay for prax monitor feed
# Version: 1.0.0
# Created: 2026-06-24
# Modified: 2026-06-24
# =============================================

"""
Telegram relay for prax monitor — mirrors the live console feed to a Telegram chat.

Buffers events in a thread-safe list, flushes every 5s via a daemon thread.
Activation requires --relay flag or AIPASS_PRAX_MONITOR_RELAY=1, plus a valid
bot config passed by the module layer (monitor.py loads from @api secrets).
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen as _http_fetch

from aipass.prax.apps.modules.logger import get_direct_logger
from aipass.prax.apps.handlers.json import json_handler
from aipass.prax.apps.handlers.monitoring import instance_lock

logger = get_direct_logger()

BATCH_INTERVAL = 5.0
TELEGRAM_MAX_LENGTH = 4000
FLOOD_CAP = 150

CONTROL_FILE = Path.home() / ".aipass" / "telegram_bots" / "prax_monitor_control.json"
_ERROR_MARKERS = ("WARNING", "ERROR", "CRITICAL")

_lock = threading.Lock()
_buffer: list[str] = []
_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_bot_token: Optional[str] = None
_chat_id: Optional[int] = None
_RELAY_ACTIVE = False
_control_mtime: float = 0.0
_control_cache: dict = {}


def init_relay(enabled: bool, config: Optional[dict] = None) -> None:
    """Start the relay if enabled and config is valid. Safe no-op otherwise.

    Args:
        enabled: Whether the relay flag is set.
        config: Bot config dict with 'bot_token' and 'chat_id' keys.
               Loaded by the module layer from @api secrets.
    """
    global _RELAY_ACTIVE, _bot_token, _chat_id, _thread

    if not enabled:
        return

    json_handler.log_operation("relay_init", {"enabled": enabled, "has_config": config is not None})

    if config is None:
        logger.info("[telegram_relay] No config provided — relay inactive")
        return

    token = config.get("bot_token", "")
    chat = config.get("chat_id")
    if not token or not chat:
        logger.info("[telegram_relay] Incomplete config (missing bot_token or chat_id) — relay inactive")
        return

    if not instance_lock.try_acquire():
        logger.info("[telegram_relay] Another process owns the TG relay — viewer-only mode")
        return

    _bot_token = token
    _chat_id = int(chat)
    _RELAY_ACTIVE = True

    _stop_event.clear()
    _thread = threading.Thread(target=_flush_loop, name="telegram-relay", daemon=True)
    _thread.start()
    logger.info("[telegram_relay] Relay started (chat_id=%s)", _chat_id)


def relay_event(event) -> None:
    """Format a MonitoringEvent and buffer for Telegram delivery. No-op when inactive."""
    if not _RELAY_ACTIVE:
        return

    line = _format_event(event)
    if not line:
        return

    with _lock:
        _buffer.append(line)


def stop_relay() -> None:
    """Final flush and thread shutdown. Safe no-op when inactive."""
    global _RELAY_ACTIVE, _thread

    if not _RELAY_ACTIVE:
        return

    _RELAY_ACTIVE = False
    _stop_event.set()

    _flush_buffer()

    if _thread is not None:
        _thread.join(timeout=BATCH_INTERVAL + 2)
        _thread = None

    instance_lock.release()
    json_handler.log_operation("relay_stopped", {})
    logger.info("[telegram_relay] Relay stopped")


def _format_event(event) -> Optional[str]:
    """Format a MonitoringEvent as a plain-text line (no Rich markup)."""
    ts = datetime.now().strftime("%H:%M:%S")

    if event.event_type == "command":
        parts = [f"▶ {event.message}"]
        caller = getattr(event, "caller", None)
        target = None
        if hasattr(event, "action") and event.action and ":" in event.action:
            action_parts = event.action.split(":", 1)
            if len(action_parts) == 2 and action_parts[1]:
                target = action_parts[1]
        if caller and caller.upper() != "UNKNOWN":
            attr = caller
            if target:
                attr = f"{caller} → {target}"
            parts.insert(0, f"  {attr}")
        return "\n".join(parts)

    if event.event_type == "hook":
        action = getattr(event, "action", "unknown")
        if action == "fired":
            return f"⚡ HOOK {event.message}"
        if action == "skipped":
            return f"· HOOK {event.message}"
        return f"? HOOK {event.message}"

    branch_label = event.branch.upper()
    pid = getattr(event, "pid", None)
    if pid:
        branch_label = f"{branch_label}:{pid}"
    return f"[{ts}] [{branch_label}] {event.message}"


def _read_control() -> dict:
    """Read the control file, caching by mtime. Returns defaults on missing/invalid file."""
    global _control_mtime, _control_cache

    try:
        stat = CONTROL_FILE.stat()
    except OSError:
        logger.info("[telegram_relay] Control file not found, using defaults")
        return {}

    if stat.st_mtime == _control_mtime:
        return _control_cache

    try:
        data = json.loads(CONTROL_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not a dict")
        _control_mtime = stat.st_mtime
        _control_cache = data
        return data
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        logger.warning("[telegram_relay] Control file parse error, using defaults: %s", exc)
        _control_mtime = stat.st_mtime
        _control_cache = {}
        return {}


def _flush_buffer() -> None:
    """Drain buffer, apply control-file pause/filter, and send to Telegram.

    Control semantics (written by the @skills TG bot):
    - paused=true: buffer is discarded, nothing sent.
    - level="errors": only lines containing WARNING/ERROR/CRITICAL are sent.
    - level="all" (default): everything is sent.
    """
    with _lock:
        if not _buffer:
            return
        lines = list(_buffer)
        _buffer.clear()

    if not _bot_token or not _chat_id:
        return

    ctrl = _read_control()

    if ctrl.get("paused", False):
        return

    level = ctrl.get("level", "all")
    if level == "errors":
        lines = [ln for ln in lines if any(m in ln for m in _ERROR_MARKERS)]
        if not lines:
            return

    if len(lines) > FLOOD_CAP:
        suppressed = len(lines) - FLOOD_CAP
        lines = lines[:FLOOD_CAP]
        lines.append(f"…({suppressed} more suppressed)")

    _send_batched(lines)


def _flush_loop() -> None:
    """Background thread: flush buffer every BATCH_INTERVAL seconds."""
    while not _stop_event.is_set():
        _stop_event.wait(BATCH_INTERVAL)
        if _buffer:
            _flush_buffer()


def _send_batched(lines: list[str]) -> None:
    """Split lines into ≤4000-char chunks and POST each to Telegram."""
    if not lines:
        return

    batch: list[str] = []
    batch_len = 0

    for line in lines:
        line_len = len(line) + (1 if batch else 0)
        if batch_len + line_len > TELEGRAM_MAX_LENGTH and batch:
            _send_message("\n".join(batch))
            batch = []
            batch_len = 0
        batch.append(line)
        batch_len += line_len

    if batch:
        _send_message("\n".join(batch))


def _send_message(text: str) -> bool:
    """POST a single message to the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{_bot_token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": _chat_id,
            "text": text,
            "disable_notification": True,
        }
    ).encode("utf-8")
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with _http_fetch(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("ok", False)
    except (URLError, Exception) as e:
        logger.warning("[telegram_relay] Send failed: %s", e)
        return False


def is_relay_enabled_by_env() -> bool:
    """Check if the relay is enabled via environment variable."""
    return os.environ.get("AIPASS_PRAX_MONITOR_RELAY", "").strip() in ("1", "true", "yes")
