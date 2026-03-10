# =================== AIPass ====================
# Name: get_open_plans.py
# Description: Get Open Plans Handler
# Version: 1.0.0
# Created: 2025-11-21
# Modified: 2025-11-21
# =============================================

"""
Get Open Plans Handler

Returns list of open plans from registry.

Usage:
    from aipass.flow.apps.handlers.plan.get_open_plans import get_open_plans
    open_plans = get_open_plans()
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[4]

# Internal: Registry handler
from aipass.flow.apps.handlers.registry.load_registry import load_registry

# =============================================
# HANDLER FUNCTION
# =============================================

def get_open_plans() -> List[Tuple[str, Dict[str, Any]]]:
    """
    Get all open plans from registry

    Returns:
        List of tuples: [(plan_num, plan_info), ...]
        Empty list if no open plans found

    Example:
        >>> plans = get_open_plans()
        >>> for plan_num, plan_info in plans:
        ...     print(f"PLAN{plan_num}: {plan_info['subject']}")
    """
    # Load registry
    registry = load_registry()

    # Filter for open plans
    open_plans = [
        (plan_num, plan_info)
        for plan_num, plan_info in registry.get("plans", {}).items()
        if plan_info.get("status") == "open"
    ]

    return open_plans
