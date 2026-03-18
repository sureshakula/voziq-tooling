# =================== AIPass ====================
# Name: get_closed_plans.py
# Description: Get Closed Plans Handler
# Version: 1.0.0
# Created: 2025-11-21
# Modified: 2025-11-21
# =============================================

"""
Get Closed Plans Handler

Returns list of closed plans from registry.

Usage:
    from aipass.flow.apps.handlers.plan.get_closed_plans import get_closed_plans
    closed_plans = get_closed_plans()
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[4]

# Internal: Registry handler
from aipass.flow.apps.handlers.registry.load_registry import load_registry
from aipass.flow.apps.handlers.json import json_handler

# =============================================
# HANDLER FUNCTION
# =============================================

def get_closed_plans() -> List[Tuple[str, Dict[str, Any]]]:
    """
    Get all closed plans from registry

    Returns:
        List of tuples: [(plan_num, plan_info), ...]
        Empty list if no closed plans found

    Example:
        >>> plans = get_closed_plans()
        >>> for plan_num, plan_info in plans:
        ...     print(f"PLAN{plan_num}: {plan_info['subject']}")
    """
    # Load registry
    registry = load_registry()

    # Filter for closed plans
    closed_plans = [
        (plan_num, plan_info)
        for plan_num, plan_info in registry.get("plans", {}).items()
        if plan_info.get("status") == "closed"
    ]

    json_handler.log_operation("closed_plans_retrieved", {"count": len(closed_plans)})
    return closed_plans
