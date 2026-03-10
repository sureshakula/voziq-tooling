# =================== AIPass ====================
# Name: list_ops.py
# Description: Plan Listing Implementation Handler
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Plan Listing Operations Handler

Implements plan listing business logic, extracted from list_plans module.
Loads registry, filters plans, gets statistics, and returns data for display.

Usage:
    from aipass.flow.apps.handlers.plan.list_ops import list_plans_impl
"""

from typing import Dict, Any

from aipass.prax import logger
# logger imported from aipass.prax

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "list_plans"


# =============================================
# LIST PLANS IMPLEMENTATION
# =============================================

def list_plans_impl(
    filter_type: str = "open",
    # Dependencies injected from module
    load_registry=None,
    get_registry_statistics=None,
    format_plans_list=None,
    format_statistics_summary=None,
) -> Dict[str, Any]:
    """
    Implement plan listing workflow

    Args:
        filter_type: Filter plans by status ("open", "closed", "all")
        load_registry: Registry loader function (injected from module)
        get_registry_statistics: Statistics function (injected from module)
        format_plans_list: Plan list formatter (injected from module)
        format_statistics_summary: Stats formatter (injected from module)

    Returns:
        Dict with keys: success (bool), formatted_list (str), formatted_stats (str),
        empty (bool), filter_type (str)
    """
    try:
        # STEP 1: Load registry (handler)
        registry = load_registry()

        # STEP 2: Get plans
        plans = registry.get("plans", {})

        if not plans:
            logger.info(f"[{MODULE_NAME}] No plans in registry")
            return {
                "success": True,
                "formatted_list": "",
                "formatted_stats": "",
                "empty": True,
                "filter_type": filter_type,
            }

        # STEP 3: Determine filter
        if filter_type == "all":
            filter_status = None
        else:
            filter_status = filter_type  # "open" or "closed"

        # STEP 4: Format plans list
        formatted_list = format_plans_list(plans, filter_status)

        # STEP 5: Get and format statistics
        stats = get_registry_statistics(registry)
        formatted_stats = format_statistics_summary(stats)

        # STEP 6: Log success
        logger.info(f"[{MODULE_NAME}] Listed plans (filter: {filter_type})")

        return {
            "success": True,
            "formatted_list": formatted_list,
            "formatted_stats": formatted_stats,
            "empty": False,
            "filter_type": filter_type,
        }

    except BrokenPipeError:
        # Pipe closed by reader (e.g. automated subprocesses, head)
        logger.info(f"[{MODULE_NAME}] Broken pipe (stdout closed early)")
        return {
            "success": True,
            "formatted_list": "",
            "formatted_stats": "",
            "empty": True,
            "filter_type": filter_type,
        }

    except Exception as e:
        error_msg = f"Error listing plans: {e}"
        logger.error(f"[{MODULE_NAME}] {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "formatted_list": "",
            "formatted_stats": "",
            "empty": True,
            "filter_type": filter_type,
        }
