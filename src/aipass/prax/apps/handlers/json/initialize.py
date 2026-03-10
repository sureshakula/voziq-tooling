# =================== AIPass ====================
# Name: initialize.py
# Description: JSON Structure Initialization Handler
# Version: 1.0.0
# Created: 2025-11-07
# Modified: 2026-03-09
# =============================================

"""
JSON Structure Initialization Handler

Initializes complete 3-file JSON structure for a module.
Creates config, data, and log files with standard structure.

Features:
- Create all 3 JSON files at once
- Accept optional initial config and data
- Creates initial log entry
- Returns success status

Usage:
    from aipass.prax.apps.handlers.json.initialize import initialize_json_structure

    initial_config = {"enabled": True, "max_items": 100}
    initial_data = {"count": 0, "last_run": None}

    success = initialize_json_structure("my_module", json_dir, initial_config, initial_data)
"""

from pathlib import Path
from typing import Dict, Any, Optional

# Import other JSON handlers
from aipass.prax.apps.handlers.json.save import save_config, save_data
from aipass.prax.apps.handlers.json.log import log_operation

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "json_initialize"

# =============================================
# HANDLER FUNCTION
# =============================================

def initialize_json_structure(
    module_name: str,
    json_dir: Path,
    initial_config: Optional[Dict[str, Any]] = None,
    initial_data: Optional[Dict[str, Any]] = None
) -> bool:
    """Initialize complete 3-file JSON structure for a module

    Args:
        module_name: Name of the module
        json_dir: Directory where JSON files are stored
        initial_config: Initial config data (optional, uses empty dict if None)
        initial_data: Initial data (optional, uses empty dict if None)

    Returns:
        True if initialization successful, False otherwise

    Creates:
    - {module_name}_config.json with standard structure
    - {module_name}_data.json with standard structure
    - {module_name}_log.json with initialization entry

    Example:
        >>> config = {"enabled": True, "debug": False}
        >>> data = {"counter": 0, "items": []}
        >>> success = initialize_json_structure("my_module", json_dir, config, data)
        >>> if success:
        >>>     print("Module JSON structure initialized")
    """
    try:
        # Create config
        if initial_config:
            save_config(module_name, json_dir, initial_config)
        else:
            save_config(module_name, json_dir, {})

        # Create data
        if initial_data:
            save_data(module_name, json_dir, initial_data)
        else:
            save_data(module_name, json_dir, {})

        # Create initial log entry
        log_operation(module_name, json_dir, "Module initialized", True, {"status": "ready"})

        return True

    except Exception as e:
        return False
