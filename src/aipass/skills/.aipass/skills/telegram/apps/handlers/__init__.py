# =================== AIPass ====================
# Name: __init__.py
# Description: Telegram handlers package — multi-bot public API surface
# Version: 1.1.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================

"""
Telegram Handlers Package

Provides Telegram bot integration for AIPass multi-bot architecture:
- config.py: Token and per-bot configuration loading
- bot_registry.py: Central bot registry CRUD
- bot_factory.py: Bot lifecycle (create, delete, enable, disable)
- notifier.py: Scheduler push notifications
- tmux_manager.py: tmux session management for Claude sessions
"""

from .config import (
    load_bot_config,
    load_telegram_config,
    get_bot_token,
    get_bot_username,
    list_bot_configs,
    validate_bot_config,
)
from .bot_registry import (
    get_bot,
    list_bots,
    register_bot,
    update_bot,
    deregister_bot,
    get_bot_by_branch,
)
from .bot_factory import (
    create_bot,
    delete_bot,
    validate_token,
    validate_branch,
    enable_service,
    disable_service,
)
from .notifier import send_telegram_notification

__all__ = [
    # config
    "load_bot_config",
    "load_telegram_config",
    "get_bot_token",
    "get_bot_username",
    "list_bot_configs",
    "validate_bot_config",
    # bot_registry
    "get_bot",
    "list_bots",
    "register_bot",
    "update_bot",
    "deregister_bot",
    "get_bot_by_branch",
    # bot_factory
    "create_bot",
    "delete_bot",
    "validate_token",
    "validate_branch",
    "enable_service",
    "disable_service",
    # notifier
    "send_telegram_notification",
]
