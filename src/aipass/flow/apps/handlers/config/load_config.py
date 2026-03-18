# =================== AIPass ====================
# Name: load_config.py
# Description: Load Config Handler
# Version: 1.1.0
# Created: 2025-11-07
# Modified: 2025-11-07
# =============================================

"""
Load Config Handler

Loads module configuration from JSON config file with auto-creation.

Features:
- Loads config from flow_json/ directory
- Auto-creates default config if missing
- Graceful error handling with fallback
- Reusable across Flow modules

Usage:
    from aipass.flow.apps.handlers.config.load_config import load_config

    config = load_config("registry_monitor")
    enabled = config.get("config", {}).get("enabled", True)
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

from aipass.flow.apps.handlers.json import json_handler

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[4]
FLOW_ROOT = _PKG_ROOT / "flow"

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "load_config"
FLOW_JSON_DIR = FLOW_ROOT / "flow_json"

# =============================================
# HANDLER FUNCTIONS
# =============================================

def create_default_config(config_file: Path, module_name: str, default_settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Create default config file if it doesn't exist

    Args:
        config_file: Path to config file
        module_name: Name of the module (for metadata)
        default_settings: Optional dict of default config values

    Returns:
        Default config structure
    """
    if config_file.exists():
        return {}

    default_config = {
        "module_name": module_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": default_settings or {"enabled": True}
    }

    try:
        FLOW_JSON_DIR.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config
    except Exception:
        return default_config


def load_config(module_name: str, default_settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Load module configuration with auto-creation of defaults

    Args:
        module_name: Name of the module (e.g., "registry_monitor")
        default_settings: Optional dict of default config values

    Returns:
        Config dictionary with structure:
        {
            "module_name": str,
            "timestamp": str,
            "config": {...}
        }

    Example:
        >>> config = load_config("registry_monitor", {"enabled": True, "scan_on_startup": True})
        >>> enabled = config.get("config", {}).get("enabled", True)
    """
    config_file = FLOW_JSON_DIR / f"{module_name}_config.json"

    # Create config if it doesn't exist
    create_default_config(config_file, module_name, default_settings)

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        json_handler.log_operation("config_loaded", {
            "module": module_name,
            "config_file": config_file.name,
            "success": True,
        })
        return data
    except Exception:
        return {"config": default_settings or {"enabled": True}}
