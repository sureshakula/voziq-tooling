# =================== AIPass ====================
# Name: load_registry.py
# Description: Load Registry Handler
# Version: 1.1.0
# Created: 2025-11-07
# Modified: 2025-11-07
# =============================================

"""
Load Registry Handler

Loads the Flow PLAN registry from JSON file with error handling.

Features:
- Loads flow_registry.json
- Returns default structure if file missing
- Graceful error handling
- Reusable across Flow modules

Usage:
    from aipass.flow.apps.handlers.registry.load_registry import load_registry
    registry = load_registry()
"""

import json
from pathlib import Path
from typing import Dict, Any

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[4]
FLOW_ROOT = _PKG_ROOT / "flow"

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "load_registry"
FLOW_JSON_DIR = FLOW_ROOT / "flow_json"
REGISTRY_FILE = FLOW_JSON_DIR / "flow_registry.json"

# =============================================
# HANDLER FUNCTION
# =============================================

def load_registry() -> Dict[str, Any]:
    """Load PLAN registry

    Returns:
        Dict containing:
        - plans: Dict of plan_number -> plan_info
        - next_number: Next available plan number

    Returns default structure if file doesn't exist or on error.
    """
    if not REGISTRY_FILE.exists():
        return {"plans": {}, "next_number": 1}

    try:
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"plans": {}, "next_number": 1}
