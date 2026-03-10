# =================== AIPass ====================
# Name: statistics.py
# Description: Registry Statistics Handler
# Version: 1.0.0
# Created: 2025-11-07
# Modified: 2026-03-09
# =============================================

"""
Registry Statistics Handler

Extracts and returns statistics about the Prax module registry.
Returns total module count and other registry metadata.

Features:
- Reads prax_registry.json statistics section
- Returns total_modules count
- Includes registry_exists flag
- Graceful error handling

Usage:
    from aipass.prax.apps.handlers.registry.statistics import get_registry_statistics

    stats = get_registry_statistics()
    print(f"Total modules: {stats['total_modules']}")
"""

import json
from pathlib import Path
from typing import Dict, Any

from aipass.prax.apps.handlers.config.load import PRAX_ROOT

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "statistics"
PRAX_JSON_DIR = PRAX_ROOT / "prax_json"
REGISTRY_FILE = PRAX_JSON_DIR / "prax_registry.json"

# =============================================
# HANDLER FUNCTION
# =============================================

def get_registry_statistics() -> Dict[str, Any]:
    """Get statistics about the module registry

    Returns:
        Dict containing registry statistics:
        {
            "total_modules": 42,
            "registry_exists": True,
            "last_updated": "2025-11-07T...",
            "scan_location": "src/aipass"
        }

        If registry doesn't exist or error occurs:
        {
            "total_modules": 0,
            "registry_exists": False
        }

    Example:
        >>> stats = get_registry_statistics()
        >>> if stats["registry_exists"]:
        >>>     print(f"Registry has {stats['total_modules']} modules")
    """
    if not REGISTRY_FILE.exists():
        return {
            "total_modules": 0,
            "registry_exists": False
        }

    try:
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # Extract statistics section if present
            stats = data.get('statistics', {})

            # Add registry_exists flag
            stats['registry_exists'] = True

            # Ensure total_modules is present (calculate if missing)
            if 'total_modules' not in stats:
                stats['total_modules'] = len(data.get('modules', {}))

            return stats

    except Exception as e:
        # Silently return error info - logging not available at this level
        return {
            "total_modules": 0,
            "registry_exists": False,
            "error": str(e)
        }
