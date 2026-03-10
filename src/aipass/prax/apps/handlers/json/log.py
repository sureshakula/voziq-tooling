# =================== AIPass ====================
# Name: log.py
# Description: JSON Log Handler
# Version: 1.0.0
# Created: 2025-11-07
# Modified: 2026-03-09
# =============================================

"""
JSON Log Handler

Universal logging utility for module operations.
Maintains last 100 log entries per module in JSON format.

Features:
- Log module operations to _log.json file
- Keep last 100 entries (newest first)
- Include timestamp, operation, success, details, error
- Graceful error handling

Usage:
    from aipass.prax.apps.handlers.json.log import log_operation

    log_operation("my_module", json_dir, "save_config", success=True, details="Config saved")
    log_operation("my_module", json_dir, "load_data", success=False, error="File not found")
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "json_log"
MAX_LOG_ENTRIES = 100

# =============================================
# HANDLER FUNCTION
# =============================================

def log_operation(
    module_name: str,
    json_dir: Path,
    operation: str,
    success: bool = True,
    details: Any = None,
    error: Optional[str] = None
) -> bool:
    """Log module operation to log file

    Args:
        module_name: Name of the module
        json_dir: Directory where JSON files are stored
        operation: Operation description (e.g., "save_config", "load_data")
        success: Whether operation succeeded (default True)
        details: Additional details (any JSON-serializable data)
        error: Error message if failed (optional)

    Returns:
        True if log successful, False otherwise

    Log entries are stored as array in {module_name}_log.json:
    [
        {
            "timestamp": "2025-11-07T...",
            "operation": "save_config",
            "success": true,
            "details": "Config saved successfully",
            "error": null
        },
        ...
    ]

    Only last 100 entries are kept (newest first).

    Example:
        >>> log_operation("my_module", json_dir, "save_config", True, "Saved 10 items")
        >>> log_operation("my_module", json_dir, "load_data", False, error="File not found")
    """
    log_file = json_dir / f"{module_name}_log.json"

    try:
        # Ensure directory exists
        json_dir.mkdir(parents=True, exist_ok=True)

        # Load existing log
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                log_entries = json.load(f)
        else:
            log_entries = []

        # Create new entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "success": success,
            "details": details,
            "error": error
        }

        # Add to log (newest first)
        log_entries.insert(0, entry)

        # Keep only last 100 entries
        log_entries = log_entries[:MAX_LOG_ENTRIES]

        # Save log
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entries, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False
