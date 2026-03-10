# =================== AIPass ====================
# Name: save.py
# Description: JSON Save Handler
# Version: 1.0.0
# Created: 2025-11-07
# Modified: 2026-03-09
# =============================================

"""
JSON Save Handler

Universal JSON saving utilities for 3-file pattern (config/data/log).
Provides standardized saving with automatic timestamp updates.

Features:
- Save config files with standard structure
- Save data files with standard structure
- Auto-update timestamps
- Create directories if missing
- Graceful error handling

Usage:
    from aipass.prax.apps.handlers.json.save import save_config, save_data

    save_config("my_module", json_dir, {"setting": "value"})
    save_data("my_module", json_dir, {"runtime": "data"})
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "json_save"

# =============================================
# HANDLER FUNCTIONS
# =============================================

def save_config(module_name: str, json_dir: Path, config_data: Dict[str, Any]) -> bool:
    """Save module config file with standard structure

    Args:
        module_name: Name of the module
        json_dir: Directory where JSON files are stored
        config_data: Config data dict (will be wrapped in standard structure)

    Returns:
        True if successful, False otherwise

    The config is saved with this structure:
    {
        "module_name": "...",
        "version": "1.0.0",
        "timestamp": "2025-11-07T...",
        "config": {...}  # your config_data goes here
    }

    Example:
        >>> settings = {"enabled": True, "max_items": 100}
        >>> success = save_config("my_module", json_dir, settings)
    """
    config_file = json_dir / f"{module_name}_config.json"

    try:
        # Ensure directory exists
        json_dir.mkdir(parents=True, exist_ok=True)

        # Wrap data in standard structure
        output = {
            "module_name": module_name,
            "version": config_data.get("version", "1.0.0"),
            "timestamp": datetime.now().isoformat(),
            "config": config_data
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False


def save_data(module_name: str, json_dir: Path, data: Dict[str, Any]) -> bool:
    """Save module data file with standard structure

    Args:
        module_name: Name of the module
        json_dir: Directory where JSON files are stored
        data: Data dict (will be wrapped in standard structure)

    Returns:
        True if successful, False otherwise

    The data is saved with this structure:
    {
        "module_name": "...",
        "timestamp": "2025-11-07T...",
        "data": {...}  # your data goes here
    }

    Example:
        >>> runtime_data = {"last_run": "2025-11-07", "count": 42}
        >>> success = save_data("my_module", json_dir, runtime_data)
    """
    data_file = json_dir / f"{module_name}_data.json"

    try:
        # Ensure directory exists
        json_dir.mkdir(parents=True, exist_ok=True)

        # Wrap data in standard structure
        output = {
            "module_name": module_name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False
