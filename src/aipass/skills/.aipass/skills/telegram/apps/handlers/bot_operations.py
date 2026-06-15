# =================== AIPass ====================
# Name: bot_operations.py - Bot operation handlers for multi-bot module
# Date: 2026-02-24
# Version: 1.0.0
# Category: api/handlers/telegram
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-02-24): Initial - start, stop, status, list operations for multi-bot system
#
# CODE STANDARDS:
#   - Pure functions with proper error handling (graceful - never raise)
#   - No Prax imports (handler tier 3)
#   - Stdlib only (subprocess for systemd)
#   - Returns values for caller to log/display - no handler-level logging
# =============================================

"""
Bot Operation Handlers for Multi-Bot Architecture

Implementation logic for bot lifecycle operations:
- start_bot: load config and run polling loop
- stop_bot: stop systemd service
- get_status: query registry for bot status
- get_all_bots: list all registered bots
- format_bot_details: format a bot entry for display

Called by the telegram_bot module (thin orchestration layer).
All functions return values - the module layer handles logging and display.
"""

# Standard library
import subprocess
from pathlib import Path

# Internal handler imports
from .base_bot import BaseBot
from .branch_plugin import BranchPlugin
from .bot_registry import list_bots, get_bot
from .config import load_bot_config

# =============================================
# BOT OPERATIONS
# =============================================


def start_bot(bot_id: str) -> int | None:
    """
    Load config and start a bot's polling loop.

    Loads config from ~/.aipass/telegram_bots/{bot_id}.json.
    If config has "branch_name", creates a BranchPlugin, else a BaseBot.
    Calls bot.run() which blocks until terminated.

    Args:
        bot_id: Bot identifier to start

    Returns:
        Bot exit code, or None if config loading failed.
    """
    config = load_bot_config(bot_id)
    if not config:
        return None

    bot_token = config.get("bot_token")
    if not bot_token:
        return None

    work_dir = Path(config.get("work_dir", str(Path.home())))
    bot_name = config.get("bot_name", f"AIPass {bot_id} Bot")
    allowed_user_ids = config.get("allowed_user_ids", [])
    branch_name = config.get("branch_name")

    if branch_name:
        bot = BranchPlugin(
            branch_name=branch_name,
            bot_id=bot_id,
            bot_token=bot_token,
            work_dir=work_dir,
            bot_name=bot_name,
            allowed_user_ids=allowed_user_ids,
        )
    else:
        bot = BaseBot(
            bot_id=bot_id,
            bot_token=bot_token,
            work_dir=work_dir,
            bot_name=bot_name,
            allowed_user_ids=allowed_user_ids,
        )

    return bot.run()


def stop_bot(bot_id: str) -> tuple[bool, str]:
    """
    Stop a bot's systemd service.

    Args:
        bot_id: Bot identifier to stop

    Returns:
        Tuple of (success, message).
    """
    service_name = f"telegram-bot@{bot_id}"

    try:
        result = subprocess.run(
            ["systemctl", "--user", "stop", service_name],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return True, f"Stopped {service_name}"

        return False, f"Failed to stop {service_name}: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return False, f"Timeout stopping {service_name}"
    except OSError as e:
        return False, f"Error stopping {service_name}: {e}"


def get_status(bot_id: str | None = None) -> list[dict]:
    """
    Get bot status entries. If no bot_id, returns all bots.

    Args:
        bot_id: Specific bot to check, or None for all bots

    Returns:
        List of bot entry dicts. Empty list if not found.
    """
    if bot_id:
        bot = get_bot(bot_id)
        return [bot] if bot else []

    return list_bots()


def get_all_bots() -> list[dict]:
    """
    Get all registered bots.

    Returns:
        List of bot entry dicts.
    """
    return list_bots()


def format_bot_details(bot: dict) -> list[str]:
    """
    Format a single bot entry into display lines.

    Args:
        bot: Bot entry dict from registry.

    Returns:
        List of formatted strings for display.
    """
    bot_id = bot.get("bot_id", "?")
    username = bot.get("username", "?")
    branch = bot.get("branch_name") or "none (base bot)"
    work_dir = bot.get("work_dir", "?")
    status = bot.get("status", "?")
    service = bot.get("service_name", f"telegram-bot@{bot_id}")

    return [
        f"Bot ID:      {bot_id}",
        f"Username:    @{username}",
        f"Branch:      {branch}",
        f"Work Dir:    {work_dir}",
        f"Status:      {status}",
        f"Service:     {service}",
    ]


def format_bot_table(bots: list[dict]) -> list[str]:
    """
    Format a list of bots into table rows.

    Args:
        bots: List of bot entry dicts.

    Returns:
        List of formatted strings (header + separator + rows + total).
    """
    lines = []
    lines.append(f"  {'Bot ID':<18} {'Branch':<16} {'Username':<24} {'Status':<10}")
    lines.append(f"  {'---' * 6:<18} {'---' * 5:<16} {'---' * 8:<24} {'---' * 3:<10}")

    for bot in bots:
        bot_id = bot.get("bot_id", "?")
        branch = bot.get("branch_name") or "-"
        username = f"@{bot.get('username', '?')}"
        status = bot.get("status", "?")
        lines.append(f"  {bot_id:<18} {branch:<16} {username:<24} {status}")

    lines.append(f"  Total: {len(bots)} bot(s)")
    return lines


def parse_create_args(args: list) -> dict | None:
    """
    Parse create command arguments.

    Args:
        args: Arguments after 'create' (bot_id, token, [--branch name], [--work-dir path])

    Returns:
        Dict with parsed values, or None if args are insufficient.
    """
    if len(args) < 2:
        return None

    result = {
        "bot_id": args[0],
        "bot_token": args[1],
        "branch_name": None,
        "work_dir": None,
    }

    i = 2
    while i < len(args):
        if args[i] == "--branch" and i + 1 < len(args):
            result["branch_name"] = args[i + 1]
            i += 2
        elif args[i] == "--work-dir" and i + 1 < len(args):
            result["work_dir"] = args[i + 1]
            i += 2
        else:
            i += 1

    return result
