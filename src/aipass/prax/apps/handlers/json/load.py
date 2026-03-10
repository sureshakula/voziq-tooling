# =================== AIPass ====================
# Name: load.py
# Description: JSON Load Handler
# Version: 1.0.0
# Created: 2025-11-07
# Modified: 2026-03-09
# =============================================

"""
JSON Load Handler

Universal JSON loading utilities for 3-file pattern (config/data/log).
Provides standardized loading with graceful degradation.

Features:
- Load config files with standard structure
- Load data files with standard structure
- Graceful fallback to defaults on error
- Auto-creates default structure if missing

Usage:
    from aipass.prax.apps.handlers.json.load import load_config, load_data

    config = load_config("my_module", json_dir)
    data = load_data("my_module", json_dir)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "json_load"

# Standard JSON structures
DEFAULT_CONFIG_STRUCTURE = {
    "module_name": "",
    "version": "1.0.0",
    "timestamp": "",
    "config": {}
}

DEFAULT_DATA_STRUCTURE = {
    "module_name": "",
    "timestamp": "",
    "data": {}
}

# =============================================
# HANDLER FUNCTIONS
# =============================================

def load_config(module_name: str, json_dir: Path) -> Dict[str, Any]:
    """Load module config file with standard structure

    Args:
        module_name: Name of the module (e.g., "branch_create")
        json_dir: Directory where JSON files are stored

    Returns:
        Config dict with standard structure:
        {
            "module_name": "...",
            "version": "1.0.0",
            "timestamp": "2025-11-07T...",
            "config": {...}
        }

        Returns default structure if file doesn't exist or on error.

    Example:
        >>> config = load_config("my_module", Path("/path/to/json"))
        >>> settings = config.get("config", {})
    """
    config_file = json_dir / f"{module_name}_config.json"

    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Return default structure if file doesn't exist
            default = DEFAULT_CONFIG_STRUCTURE.copy()
            default["module_name"] = module_name
            default["timestamp"] = datetime.now().isoformat()
            return default
    except Exception:
        default = DEFAULT_CONFIG_STRUCTURE.copy()
        default["module_name"] = module_name
        default["timestamp"] = datetime.now().isoformat()
        return default


def load_data(module_name: str, json_dir: Path) -> Dict[str, Any]:
    """Load module data file with standard structure

    Args:
        module_name: Name of the module
        json_dir: Directory where JSON files are stored

    Returns:
        Data dict with standard structure:
        {
            "module_name": "...",
            "timestamp": "2025-11-07T...",
            "data": {...}
        }

        Returns default structure if file doesn't exist or on error.

    Example:
        >>> data = load_data("my_module", Path("/path/to/json"))
        >>> runtime_data = data.get("data", {})
    """
    data_file = json_dir / f"{module_name}_data.json"

    try:
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Return default structure
            default = DEFAULT_DATA_STRUCTURE.copy()
            default["module_name"] = module_name
            default["timestamp"] = datetime.now().isoformat()
            return default
    except Exception:
        default = DEFAULT_DATA_STRUCTURE.copy()
        default["module_name"] = module_name
        default["timestamp"] = datetime.now().isoformat()
        return default
