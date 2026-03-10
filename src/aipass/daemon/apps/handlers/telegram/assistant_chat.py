# =================== AIPass ====================
# Name: assistant_chat.py
# Description: Daemon Bot Telegram Launcher
# Version: 2.0.0
# Created: 2026-02-15
# Modified: 2026-02-15
# =============================================

"""
Daemon Bot Telegram Launcher (@aipass_assistant_bot)

Thin wrapper around the shared direct_chat module. All chat logic,
command handling, tmux management, and polling lives in direct_chat.py.
This file only provides the daemon-specific configuration.
"""

import sys
from pathlib import Path

from aipass.prax import logger
# logger imported from aipass.prax

try:
    from api.apps.modules.telegram_chat import run_direct_chat
    TELEGRAM_CHAT_AVAILABLE = True
except ImportError:
    TELEGRAM_CHAT_AVAILABLE = False
    run_direct_chat = None

_DAEMON_ROOT = Path(__file__).resolve().parents[3]  # src/aipass/daemon/

if not TELEGRAM_CHAT_AVAILABLE:
    logger.error("[assistant_chat] telegram_chat module not available, exiting")
    sys.exit(1)

sys.exit(run_direct_chat(
    branch_name="daemon",
    session_name="telegram-daemon",
    config_path=Path.home() / ".aipass" / "assistant_bot_config.json",
    work_dir=_DAEMON_ROOT,
    log_dir=_DAEMON_ROOT / "logs",
    data_dir=_DAEMON_ROOT / "daemon_json",
    bot_name="AIPass Assistant Bot",
))
