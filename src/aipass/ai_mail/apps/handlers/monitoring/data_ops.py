# =================== AIPass ====================
# Name: data_ops.py
# Description: Error Monitor Data Operations Handler
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2025-11-15
# =============================================

"""
Error Monitor Data Operations Handler

Independent handler for error tracking data persistence.
Provides functions for loading and saving error monitor data.

Architecture:
- No cross-domain imports (independent handler)
- Provides: data loading, data saving
- Used by: error_monitor module
"""

# =============================================
# IMPORTS
# =============================================
import json
from pathlib import Path
from typing import Dict


# =============================================
# BUSINESS LOGIC
# =============================================

def load_data(data_file: Path) -> Dict:
    """
    Load error tracking data from file.

    Args:
        data_file: Path to the error tracking data file

    Returns:
        Dictionary containing error tracking data, or empty dict if file doesn't exist
    """
    if not data_file.exists():
        return {}

    try:
        # Direct file read for error tracking data (non-standard structure)
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_data(data: Dict, data_file: Path) -> None:
    """
    Save error tracking data to file.

    Args:
        data: Dictionary containing error tracking data
        data_file: Path to the error tracking data file
    """
    # Direct file write for error tracking data (non-standard structure)
    data_file.parent.mkdir(parents=True, exist_ok=True)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
