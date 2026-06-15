# Standard library
import json
import subprocess
from pathlib import Path
from typing import Optional, List

# Logging
from aipass.prax import logger

# =============================================
# CONSTANTS
# =============================================

REQUIRED_BOT_FIELDS = ("bot_id", "bot_token")

# =============================================
# SECRETS ACCESS (via drone @api)
# =============================================


def _get_secret(bot_id: str) -> dict | None:
    """
    Retrieve bot config from the API secrets store.

    Calls `drone @api get-secret telegram/<bot_id> --json` via subprocess
    and returns the parsed JSON config dict.

    Args:
        bot_id: Bot identifier to look up.

    Returns:
        Config dict or None if the call fails or returns no data.
    """
    try:
        result = subprocess.run(
            ["drone", "@api", "get-secret", f"telegram/{bot_id}", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning(f"drone @api get-secret telegram/{bot_id} failed: {result.stderr.strip()}")
            return None

        raw = result.stdout.strip()
        if not raw:
            return None

        config = json.loads(raw)
        if not isinstance(config, dict):
            return None

        return config

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout fetching secret for bot_id={bot_id}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from get-secret telegram/{bot_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching secret for bot_id={bot_id}: {e}")
        return None


# =============================================
# LEGACY SINGLE-BOT HELPERS (rewired to @api)
# =============================================


def load_telegram_config() -> Optional[dict]:
    """
    Load Telegram configuration via the API secrets store.

    Fetches the default bot config (bot_id="default").

    Returns:
        Configuration dict or None if load fails.
    """
    return _get_secret("default")


def get_bot_token() -> Optional[str]:
    """
    Get Telegram bot token from the default bot config.

    Returns:
        Bot token string or None if not found.
    """
    config = load_telegram_config()
    if not config:
        return None

    token = config.get("bot_token") or config.get("telegram_bot_token")
    if not token:
        return None

    return token


def get_bot_username() -> Optional[str]:
    """
    Get Telegram bot username from the default bot config.

    Returns:
        Bot username string or None if not found.
    """
    config = load_telegram_config()
    if not config:
        return None

    username = config.get("bot_username") or config.get("telegram_bot_username")
    if not username:
        return None

    return username


def get_allowed_user_ids() -> List[int]:
    """
    Get list of allowed Telegram user IDs from the default bot config.

    Returns:
        List of allowed user IDs. Empty list means allow all (for testing).
    """
    config = load_telegram_config()
    if not config:
        return []

    allowed = config.get("allowed_user_ids", [])
    if not isinstance(allowed, list):
        return []

    return [int(uid) for uid in allowed if isinstance(uid, (int, str))]


def validate_config() -> bool:
    """
    Validate that the default Telegram bot configuration is complete.

    Returns:
        True if config is valid, False otherwise.
    """
    config = load_telegram_config()
    if not config:
        return False

    if not (config.get("bot_token") or config.get("telegram_bot_token")):
        return False

    return True


# =============================================
# MULTI-BOT CONFIGURATION (per-bot configs)
# =============================================


def load_bot_config(bot_id: str) -> dict | None:
    """
    Load per-bot config from the API secrets store.

    Fetches `drone @api get-secret telegram/<bot_id> --json`.

    Config format:
    {
        "bot_id": "dev_central",
        "bot_token": "123:ABC...",
        "bot_name": "AIPass Dev Central Bot",
        "branch_name": "dev_central",  // null for base bot
        "work_dir": "/path/to/branch/work_dir",
        "allowed_user_ids": [7235222625]
    }

    Args:
        bot_id: Bot identifier to fetch.

    Returns:
        Config dict or None if not found/invalid.
    """
    return _get_secret(bot_id)


def list_bot_configs() -> list[str]:
    """
    List all registered bot IDs via the API secrets store.

    Calls `drone @api get-secret telegram --list` and parses the output
    as a JSON list of bot_id strings.

    Returns:
        List of bot_id strings, or empty list on failure.
    """
    try:
        result = subprocess.run(
            ["drone", "@api", "get-secret", "telegram", "--list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning(f"drone @api get-secret telegram --list failed: {result.stderr.strip()}")
            return []

        raw = result.stdout.strip()
        if not raw:
            return []

        bot_ids = json.loads(raw)
        if not isinstance(bot_ids, list):
            return []

        return [str(b) for b in bot_ids]

    except subprocess.TimeoutExpired:
        logger.error("Timeout listing telegram bot secrets")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from get-secret telegram --list: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error listing telegram bot secrets: {e}")
        return []


def validate_bot_config(config: object) -> tuple[bool, str]:
    """
    Validate a bot config dict.

    Checks for required fields and basic type correctness.
    Pure function — no I/O.

    Args:
        config: Bot config dict to validate.

    Returns:
        Tuple of (valid, error_message). error_message is empty on success.
    """
    if not isinstance(config, dict):
        return False, "Config must be a dict"

    # Check required fields
    for field in REQUIRED_BOT_FIELDS:
        if not config.get(field):
            return False, f"Missing required field: {field}"

    # Type checks
    bot_token = config.get("bot_token", "")
    if not isinstance(bot_token, str) or ":" not in bot_token:
        return False, "bot_token must be a string in format 'id:hash'"

    if "work_dir" in config and config["work_dir"] is not None:
        work_dir = Path(config["work_dir"])
        if not work_dir.is_absolute():
            return False, "work_dir must be an absolute path"

    if "allowed_user_ids" in config:
        allowed = config["allowed_user_ids"]
        if not isinstance(allowed, list):
            return False, "allowed_user_ids must be a list"

    return True, ""
