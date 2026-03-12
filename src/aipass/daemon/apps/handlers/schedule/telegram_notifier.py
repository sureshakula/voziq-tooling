# =================== AIPass ====================
# Name: telegram_notifier.py
# Description: DAEMON Scheduler Notifications (Telegram stripped)
# Version: 2.0.0
# Created: 2026-02-15
# Modified: 2026-03-10
# =============================================

"""
Scheduler notification stubs.

Telegram was stripped from daemon. These stubs remain so existing
imports don't break. Will be replaced by a skill-based notification
system later.
"""

from aipass.prax import logger


def notify_triggered(event_name: str) -> bool:
    """Stub — Telegram removed."""
    logger.info(f"[telegram_notifier] notify_triggered({event_name}) — no-op, Telegram stripped")
    return False


def notify_complete(event_name: str, summary: str) -> bool:
    """Stub — Telegram removed."""
    logger.info(f"[telegram_notifier] notify_complete({event_name}) — no-op, Telegram stripped")
    return False


def notify_error(event_name: str, error: str) -> bool:
    """Stub — Telegram removed."""
    logger.info(f"[telegram_notifier] notify_error({event_name}) — no-op, Telegram stripped")
    return False
