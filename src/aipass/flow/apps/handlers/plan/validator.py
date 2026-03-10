# =================== AIPass ====================
# Name: validator.py
# Description: Plan Validation Handler
# Version: 0.3.0
# Created: 2025-11-30
# Modified: 2025-11-30
# =============================================

"""
Plan Validation Handler

Validates and normalizes plan numbers and registry entries.
"""

from typing import Dict, Any, Tuple


def normalize_plan_number(plan_num: str) -> str:
    """
    Normalize plan number to 4-digit format

    Accepts various formats ("1", "42", "0001") and normalizes
    to standard 4-digit format ("0001", "0042", "0001").

    Args:
        plan_num: Plan number in any format

    Returns:
        Normalized 4-digit plan number (e.g., "0001")

    Raises:
        ValueError: If plan_num cannot be converted to integer

    Examples:
        >>> normalize_plan_number("1")
        "0001"
        >>> normalize_plan_number("42")
        "0042"
        >>> normalize_plan_number("0001")
        "0001"
        >>> normalize_plan_number("FPLAN-0042")
        "0042"
        >>> normalize_plan_number("PLAN4444")
        "4444"
    """
    # Normalize prefix variations for robustness
    if isinstance(plan_num, str):
        upper = plan_num.upper()
        # Strip FPLAN- prefix (standard format)
        if upper.startswith("FPLAN-"):
            plan_num = plan_num[6:]
        # Strip PLAN- prefix (alternate format)
        elif upper.startswith("PLAN-"):
            plan_num = plan_num[5:]
        # Strip PLAN prefix without dash (e.g., PLAN4444)
        elif upper.startswith("PLAN"):
            plan_num = plan_num[4:]
    return f"{int(plan_num):04d}"


def validate_plan_exists(plan_key: str, registry: Dict[str, Any]) -> Tuple[bool, str | None]:
    """
    Validate that a plan exists in the registry

    Args:
        plan_key: Normalized plan number (e.g., "0001")
        registry: Registry dictionary with 'plans' section

    Returns:
        Tuple of (exists, error_message)
        - exists: True if plan found in registry
        - error_message: None if exists, error string if not found

    Examples:
        >>> exists, error = validate_plan_exists("0001", registry)
        >>> if not exists:
        ...     print(error)
    """
    if plan_key not in registry.get("plans", {}):
        return False, f"FPLAN-{plan_key} not found in registry"
    return True, None
