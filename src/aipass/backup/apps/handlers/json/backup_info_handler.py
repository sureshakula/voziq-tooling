# =================== AIPass ====================
# Name: backup_info_handler.py
# Description: Backup state and statistics
# Version: 1.0.0
# Created: 2025-11-16
# Modified: 2026-03-09
# =============================================

"""
Backup Info Handler

Manages backup state and statistics persistence.
Handles mode-specific formats (dynamic vs versioned).

Functions:
    load_backup_info: Load mode-specific backup state
    save_backup_info: Persist backup state to JSON
"""

# =============================================
# IMPORTS
# =============================================

import json
import datetime
from pathlib import Path
from typing import Dict

# =============================================
# BACKUP INFO OPERATIONS
# =============================================

def load_backup_info(backup_info_file: Path, mode_behavior: str) -> Dict:
    """Load backup information from JSON file.

    Args:
        backup_info_file: Path to backup_info JSON file
        mode_behavior: 'dynamic' or 'versioned'

    Returns:
        Dictionary with backup information (mode-specific format)
    """
    if backup_info_file.exists():
        try:
            with open(backup_info_file, 'r', encoding='utf-8', errors='replace') as f:
                return json.load(f)
        except Exception:
            pass

    # Return mode-specific default structure
    if mode_behavior == 'versioned':
        return {"backups": []}
    else:  # dynamic
        return {"last_backup": None, "file_timestamps": {}}


def save_backup_info(backup_info_file: Path, backup_info: Dict) -> bool:
    """Save backup information to JSON file.

    Args:
        backup_info_file: Path to backup_info JSON file
        backup_info: Dictionary containing backup information

    Returns:
        True if save succeeded, False otherwise
    """
    try:
        with open(backup_info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


# =============================================
# MODULE INITIALIZATION
# =============================================

# No initialization needed - pure utility functions
