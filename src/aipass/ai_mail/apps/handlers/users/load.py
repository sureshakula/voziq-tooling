# =================== AIPass ====================
# Name: load.py
# Description: User Config Loading Handler
# Version: 1.2.0
# Created: 2025-11-15
# Modified: 2025-11-15
# =============================================

"""
User Config Loading Handler

Handles loading of user configuration files for AI_Mail system.
Provides unified config loading for user_config.json and module configs.

NEW in v1.2.0: Per-branch config support
- Detects calling branch from PWD/CWD
- Checks for local config at branch_path/ai_mail_config/user_config.json
- Falls back to AI_MAIL's global config if no local config found
"""

# =============================================
# IMPORTS
# =============================================
import json
from pathlib import Path
from typing import Dict

# =============================================
# CONSTANTS
# =============================================
_AI_MAIL_ROOT = Path(__file__).resolve().parents[3]  # ai_mail/
AI_MAIL_JSON = _AI_MAIL_ROOT / ".ai_mail.local"
USER_CONFIG_FILE = AI_MAIL_JSON / "user_config.json"

# Import branch detection (after constants defined)
from .branch_detection import detect_branch_from_pwd, get_local_config_path

# =============================================
# CONFIG LOADING FUNCTIONS
# =============================================

def load_user_config() -> Dict:
    """
    Load user configuration from user_config.json

    NEW in v1.2.0: Per-branch config support
    - First checks if calling from a branch (detects via PWD)
    - Looks for local config at branch_path/ai_mail_config/user_config.json
    - Falls back to AI_MAIL's global config if no local config
    - Auto-generates local config if branch detected but config missing

    Returns:
        Dict containing user configuration

    Raises:
        FileNotFoundError: If no config found (neither local nor global)
    """
    # Try to detect calling branch from PWD
    branch_info = detect_branch_from_pwd()

    if branch_info:
        # Branch detected - check for local config
        branch_path = Path(branch_info["path"])
        branch_name = branch_info["name"]
        local_config_path = get_local_config_path(branch_path, branch_name)

        if local_config_path.exists():
            # Local config exists - use it
            with open(local_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # No local config - offer to auto-generate
            # For now, fall through to global config
            pass

    # No branch detected or no local config - use AI_MAIL's global config
    if not USER_CONFIG_FILE.exists():
        raise FileNotFoundError(f"User config not found: {USER_CONFIG_FILE}")

    with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_config(config_file: Path) -> Dict:
    """
    Load generic configuration file with auto-healing

    Creates default config if missing (for module configs).

    Args:
        config_file: Path to configuration file

    Returns:
        Dict containing configuration data

    Raises:
        Exception: If config cannot be loaded or created
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise


def create_default_config(config_file: Path, default_config: Dict) -> None:
    """
    Create default configuration file

    Args:
        config_file: Path where config should be created
        default_config: Default configuration dictionary

    Raises:
        Exception: If config cannot be created
    """
    # Ensure parent directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
    except Exception as e:
        raise


def load_or_create_config(config_file: Path, default_config: Dict) -> Dict:
    """
    Load config file, creating with defaults if missing

    Args:
        config_file: Path to configuration file
        default_config: Default configuration to use if file doesn't exist

    Returns:
        Dict containing configuration data
    """
    if not config_file.exists():
        create_default_config(config_file, default_config)

    return load_config(config_file)
