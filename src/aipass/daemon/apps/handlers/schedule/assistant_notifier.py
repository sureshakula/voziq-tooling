# =================== AIPass ====================
# Name: assistant_notifier.py
# Description: Daemon Bot Telegram Notifications
# Version: 1.0.0
# Created: 2026-02-15
# Modified: 2026-02-15
# =============================================

"""
Handler for sending Telegram notifications via the daemon bot.

Patrick's direct line to daemon. Uses the dedicated daemon bot
(separate from scheduler and bridge bots) to notify Patrick of
wake-up events, email reports, and errors.
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
    Load daemon bot config from daemon_config.json.

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
    Send a message to Patrick via the daemon bot.

    Args:
        message: Text to send (plain text, supports emoji)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        config = load_config()
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"[daemon_notifier] Config error: {e}")
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
            logger.error(f"[daemon_notifier] API error: {result.get('description')}")
            return False
    except URLError as e:
        logger.error(f"[daemon_notifier] Send failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[daemon_notifier] Unexpected error: {e}")
        return False


# =============================================
# NOTIFICATION HELPERS
# =============================================

def notify_wakeup() -> bool:
    """
    Notify that daemon is waking up.

    Returns:
        True if notification sent, False otherwise
    """
    now = datetime.now().strftime("%H:%M:%S")
    message = "\U0001f916 Daemon waking up at " + now
    return send_notification(message)


def notify_report(summary: str) -> bool:
    """
    Send daemon's wake-up report.

    Args:
        summary: Report content (email counts, listings, etc.)

    Returns:
        True if notification sent, False otherwise
    """
    message = "\U0001f4cb Daemon Report:\n" + summary
    return send_notification(message)


def notify_error(error: str) -> bool:
    """
    Notify that an error occurred during wake-up.

    Args:
        error: Error description

    Returns:
        True if notification sent, False otherwise
    """
    message = "\u274c Daemon Error:\n" + error
    return send_notification(message)


# =============================================
# MAIN - Testing
# =============================================

if __name__ == "__main__":
    print("assistant_notifier.py - manual test")
    print(f"Config path: {CONFIG_PATH}")

    try:
        cfg = load_config()
        print(f"Bot token: {cfg['bot_token'][:12]}...")
        print(f"Chat ID: {cfg['chat_id']}")
    except Exception as e:
        print(f"Config load failed: {e}")

    print("\nSending test notification...")
    ok = send_notification("Test from assistant_notifier.py handler")
    print(f"Result: {'OK' if ok else 'FAILED'}")
