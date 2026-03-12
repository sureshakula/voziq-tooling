# =================== AIPass ====================
# Name: assistant_notifier.py
# Description: Daemon Bot Notifications (Telegram stripped)
# Version: 2.0.0
# Created: 2026-02-15
# Modified: 2026-03-10
# =============================================

"""
Daemon bot notification stubs.

Telegram was stripped from daemon. These stubs remain so existing
imports don't break. Will be replaced by a skill-based notification
system later.
"""

from aipass.prax import logger


def notify_wakeup() -> bool:
    """Stub — Telegram removed."""
    logger.info("[assistant_notifier] notify_wakeup() — no-op, Telegram stripped")
    return False


def notify_report(summary: str) -> bool:
    """Stub — Telegram removed."""
    logger.info("[assistant_notifier] notify_report() — no-op, Telegram stripped")
    return False


def notify_error(error: str) -> bool:
    """Stub — Telegram removed."""
    logger.info("[assistant_notifier] notify_error() — no-op, Telegram stripped")
    return False
