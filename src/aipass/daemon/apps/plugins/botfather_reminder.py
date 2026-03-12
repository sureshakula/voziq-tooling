# =================== AIPass ====================
# Name: botfather_reminder.py
# Description: BotFather Reminder Plugin (DISABLED — Telegram stripped)
# Version: 2.0.0
# Created: 2026-02-26
# Modified: 2026-03-10
# =============================================

"""
BotFather Reminder Plugin — DISABLED.

Telegram was stripped from daemon. This plugin is no longer relevant.
Kept as placeholder; will be removed once action registry entry is cleaned.
"""

PLUGIN_CONFIG = {
    "name": "botfather_reminder",
    "schedule": "hourly",
    "time": "00",
    "interval_minutes": None,
    "enabled": False,
    "branch": "@dev_central",
    "fresh": False,
    "max_turns": 3,
    "prompt": "DISABLED — Telegram stripped from daemon",
}


def run() -> dict:
    """No-op — Telegram stripped."""
    return {"status": "resolved", "reason": "Telegram stripped from daemon — plugin disabled"}
