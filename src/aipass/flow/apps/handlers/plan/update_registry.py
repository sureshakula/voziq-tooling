# =================== AIPass ====================
# Name: update_registry.py
# Description: Registry Update Handler
# Version: 0.1.0
# Created: 2025-11-15
# Modified: 2025-11-15
# =============================================

"""
Registry Update Handler

Add and remove plan entries from registry.
"""

from typing import Dict, Any

from aipass.flow.apps.handlers.json import json_handler


def add_plan_to_registry(
    registry: Dict[str, Any],
    plan_num: int,
    entry: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add plan entry to registry and increment counter

    Ensures registry["plans"] exists, adds the entry with
    formatted plan number as key, and increments next_number.

    Args:
        registry: Flow registry dictionary
        plan_num: Plan number (e.g., 1, 42, 101)
        entry: Plan entry dict from build_plan_registry_entry()

    Returns:
        Modified registry with new plan entry

    Side effects:
        - Ensures registry["plans"] exists
        - Adds entry to registry["plans"][formatted_num]
        - Increments registry["next_number"]

    Example:
        >>> registry = {"next_number": 1}
        >>> entry = {"subject": "Test", "status": "open"}
        >>> registry = add_plan_to_registry(registry, 1, entry)
        >>> "0001" in registry["plans"]
        True
        >>> registry["next_number"]
        2
    """
    # Ensure plans dict exists
    if "plans" not in registry:
        registry["plans"] = {}

    # Add entry with formatted number as key
    plan_key = f"{plan_num:04d}"
    registry["plans"][plan_key] = entry

    # Increment counter
    registry["next_number"] = plan_num + 1

    json_handler.log_operation("plan_added_to_registry", {"plan_key": plan_key, "success": True})
    return registry


def remove_plan_from_registry(
    plan_key: str,
    registry: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Remove plan entry from registry

    Args:
        plan_key: Normalized plan number (e.g., "0001")
        registry: Registry dictionary

    Returns:
        Modified registry with plan removed

    Note:
        Modifies registry in place and returns it for chaining.
        Safe to call even if plan_key doesn't exist.

    Example:
        >>> registry = {"plans": {"0001": {}, "0002": {}}}
        >>> registry = remove_plan_from_registry("0001", registry)
        >>> "0001" in registry.get("plans", {})
        False
    """
    if plan_key in registry.get("plans", {}):
        del registry["plans"][plan_key]

    return registry
