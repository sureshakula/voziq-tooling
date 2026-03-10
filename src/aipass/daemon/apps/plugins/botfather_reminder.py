# =================== AIPass ====================
# Name: botfather_reminder.py
# Description: Hourly reminder to create PATRICK_PRIVATE Telegram bot
# Version: 1.0.0
# Created: 2026-02-26
# Modified: 2026-02-26
# =============================================

"""
BotFather Reminder Plugin

Hourly reminder to create the PATRICK_PRIVATE Telegram bot via BotFather.
Self-resolves: checks if bot token is still placeholder. Once real token
is set in patrick_private.json, this plugin silently exits.

Delete this file once the bot is created and running.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

PLUGIN_CONFIG = {
    "name": "botfather_reminder",
    "schedule": "hourly",
    "time": "00",
    "interval_minutes": None,
    "enabled": True,
    "branch": "@dev_central",
    "fresh": False,
    "max_turns": 3,
    "prompt": "Reminder: create PATRICK_PRIVATE Telegram bot via BotFather",
}

BOT_CONFIG = Path.home() / ".aipass" / "telegram_bots" / "patrick_private.json"
NOT_BEFORE = datetime(2026, 2, 27, 9, 0, 0)


def run() -> dict:
    """Check if reminder is still needed, send email if so."""
    now = datetime.now()

    # Don't start until BotFather cooldown expires
    if now < NOT_BEFORE:
        return {"status": "waiting", "reason": f"cooldown until {NOT_BEFORE.isoformat()}"}

    # Check if token has been set (self-resolving)
    try:
        config = json.loads(BOT_CONFIG.read_text(encoding="utf-8"))
        token = config.get("bot_token", "")
        if token and token != "PASTE_TOKEN_HERE":
            return {"status": "resolved", "reason": "token already set -- delete this plugin"}
    except (json.JSONDecodeError, OSError):
        pass  # Config missing or broken -- still remind

    # Send reminder email
    subject = "REMINDER: Create PATRICK_PRIVATE Telegram bot"
    message = (
        "BotFather cooldown should be expired. Steps:\n"
        "1. Open Telegram -> @BotFather -> /newbot\n"
        "2. Pick a name (anything private, e.g. 'My Notes')\n"
        "3. Pick a username (must end in _bot)\n"
        "4. Paste the token into the DEV_CENTRAL chat\n"
        "5. Config ready at: ~/.aipass/telegram_bots/patrick_private.json\n\n"
        "This reminder repeats hourly until the token is set."
    )

    try:
        subprocess.run(
            [
                "drone", "@ai_mail", "send", "@dev_central",
                subject, message,
            ],
            capture_output=True, timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        pass  # Silent -- never crash scheduler

    return {"status": "reminded", "next_check": "1 hour"}
