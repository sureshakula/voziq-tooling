# =================== AIPass ====================
# Name: telegram_notifier.py
# Description: DAEMON Scheduler Telegram Notifications
# Version: 1.0.0
# Created: 2026-02-15
# Modified: 2026-02-15
# =============================================

"""
Handler for sending Telegram notifications via the scheduler bot.

Reusable notification layer for scheduled events. Uses the dedicated
scheduler bot (separate from bridge bot) to notify Patrick of
triggered events, completions, and errors.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict
from urllib.request import Request, urlopen
from urllib.error import URLError

from aipass.prax import logger
# logger imported from aipass.prax

# =============================================
# CONSTANTS
# =============================================

CONFIG_PATH = Path(os.environ.get('AIPASS_DAEMON_CONFIG', Path.home() / '.aipass' / 'daemon_config.json'))


# =============================================
# CONFIG
# =============================================

def load_config() -> Dict[str, str]:
    """
    Load scheduler bot config from daemon_config.json.

    Returns:
        Dict with 'bot_token' and 'chat_id' keys

    Raises:
        FileNotFoundError: If config file is missing
        KeyError: If required keys are absent
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return {
        "bot_token": raw["telegram_bot_token"],
        "chat_id": raw["telegram_chat_id"],
    }


# =============================================
# SEND
# =============================================

def send_notification(message: str) -> bool:
    """
    Send a message to Patrick via the scheduler bot.

    Args:
        message: Text to send (plain text, supports emoji)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        config = load_config()
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"[telegram_notifier] Config error: {e}")
        return False

    url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
    payload = {
        "chat_id": config["chat_id"],
        "text": message,
    }

    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return True
            logger.error(f"[telegram_notifier] API error: {result.get('description')}")
            return False
    except URLError as e:
        logger.error(f"[telegram_notifier] Send failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[telegram_notifier] Unexpected error: {e}")
        return False


# =============================================
# NOTIFICATION HELPERS
# =============================================

def notify_triggered(event_name: str) -> bool:
    """
    Notify that a scheduled event was triggered.

    Args:
        event_name: Name of the event that fired

    Returns:
        True if notification sent, False otherwise
    """
    now = datetime.now().strftime("%H:%M:%S")
    message = f"\U0001f514 Scheduler: {event_name} triggered at {now}"
    return send_notification(message)


def notify_complete(event_name: str, summary: str) -> bool:
    """
    Notify that a scheduled event completed successfully.

    Args:
        event_name: Name of the event that completed
        summary: Brief summary of what happened

    Returns:
        True if notification sent, False otherwise
    """
    message = f"\u2705 Scheduler: {event_name} complete\n{summary}"
    return send_notification(message)


def notify_error(event_name: str, error: str) -> bool:
    """
    Notify that a scheduled event failed.

    Args:
        event_name: Name of the event that failed
        error: Error description

    Returns:
        True if notification sent, False otherwise
    """
    message = f"\u274c Scheduler: {event_name} failed\n{error}"
    return send_notification(message)


# =============================================
# MAIN - Testing
# =============================================

if __name__ == "__main__":
    print("telegram_notifier.py - manual test")
    print(f"Config path: {CONFIG_PATH}")

    try:
        cfg = load_config()
        print(f"Bot token: {cfg['bot_token'][:12]}...")
        print(f"Chat ID: {cfg['chat_id']}")
    except Exception as e:
        print(f"Config load failed: {e}")

    print("\nSending test notification...")
    ok = send_notification("Test from telegram_notifier.py handler")
    print(f"Result: {'OK' if ok else 'FAILED'}")
