# =================== AIPass ====================
# Name: create_ops.py
# Description: Plan Creation Implementation Handler
# Version: 1.1.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Plan Creation Operations Handler

Implements plan creation business logic, extracted from create_plan module.
Handles the full plan creation workflow including registry and dashboard updates.

Returns data - module handles all display.

Usage:
    from aipass.flow.apps.handlers.plan.create_ops import create_plan_impl, slugify_subject
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Any

from aipass.prax import logger
# logger imported from aipass.prax

# =============================================
# INFRASTRUCTURE
# =============================================

_PKG_ROOT = Path(__file__).resolve().parents[4]  # handlers/plan/ -> handlers/ -> apps/ -> flow/ -> aipass/

MODULE_NAME = "create_plan"

# =============================================
# HELPERS
# =============================================

def slugify_subject(subject: str) -> str:
    """Sanitize subject for filename: lowercase, underscores, max 40 chars."""
    slug = re.sub(r'[^\w\s-]', '', subject.lower())
    slug = re.sub(r'[\s-]+', '_', slug)
    return slug.strip('_')[:40]


# =============================================
# CREATE PLAN IMPLEMENTATION
# =============================================

def create_plan_impl(
    location=None,
    subject="",
    template_type="default",
    # Dependencies injected from module
    ecosystem_root=None,
    load_registry=None,
    save_registry=None,
    auto_close_orphaned_plans=None,
    resolve_plan_location=None,
    calculate_relative_location=None,
    get_template=None,
    create_plan_file=None,
    build_plan_registry_entry=None,
    display_plan_created=None,
    update_dashboard_local=None,
    push_to_plans_central=None,
    push_flow_to_branch_dashboard=None,
) -> Tuple[bool, int, str, str, str, List[Dict[str, Any]]]:
    """
    Implement plan creation workflow

    Workflow Steps:
        1. Load registry
        2. Auto-cleanup orphaned plans
        3. Get next plan number
        4. Resolve location (@folder syntax support)
        5. Calculate relative path for display
        6. Build plan file path
        7. Get template content
        8. Create plan file
        9. Build and save registry entry
        10. Update dashboards
        11. Log and display results

    Args:
        location: Target directory for plan (@folder syntax supported)
        subject: Plan subject/title
        template_type: Template to use (default, master, etc.)
        (remaining args): Handler/service dependencies injected by module

    Returns:
        (success, plan_number, location_description, template_type, error_message, messages)
        messages is a list of dicts with type/text for the module to display
    """
    messages: List[Dict[str, Any]] = []

    try:
        # STEP 1: Load registry
        registry = load_registry()

        # STEP 2: Auto-cleanup orphaned plans
        registry, auto_closed_count = auto_close_orphaned_plans(registry)
        if auto_closed_count > 0:
            save_registry(registry)
            messages.append({"type": "dim", "text": f"[AUTO-CLEANUP] Closed {auto_closed_count} orphaned plan(s)"})

        # STEP 3: Get next plan number
        NEXT_NUM = registry["next_number"]

        # STEP 4: Resolve location (@folder syntax support)
        success, target_dir, error_msg = resolve_plan_location(location, ecosystem_root)
        if not success:
            return False, 0, "", "", error_msg, messages

        # STEP 5: Calculate relative path for display
        RELATIVE_LOCATION = calculate_relative_location(target_dir, ecosystem_root)

        # STEP 6: Build plan file path (FPLAN-XXXX_topic_slug_YYYY-MM-DD.md)
        topic_slug = slugify_subject(subject)
        date_str = datetime.now().strftime("%Y-%m-%d")
        if topic_slug:
            PLAN_FILE = target_dir / f"FPLAN-{NEXT_NUM:04d}_{topic_slug}_{date_str}.md"
        else:
            PLAN_FILE = target_dir / f"FPLAN-{NEXT_NUM:04d}_{date_str}.md"

        # STEP 7: Get template content
        try:
            CONTENT = get_template(
                template_type,
                number=NEXT_NUM,
                location=RELATIVE_LOCATION,
                subject=subject
            )
        except Exception as e:
            error_msg = f"Failed to load template '{template_type}': {e}"
            logger.error(f"[{MODULE_NAME}] {error_msg}")
            return False, 0, "", "", error_msg, messages

        # STEP 8: Create plan file
        success, error_msg = create_plan_file(PLAN_FILE, CONTENT)
        if not success:
            return False, 0, "", "", error_msg, messages

        # STEP 9: Build registry entry
        if "plans" not in registry:
            registry["plans"] = {}

        registry["plans"][f"{NEXT_NUM:04d}"] = build_plan_registry_entry(
            NEXT_NUM, target_dir, RELATIVE_LOCATION, subject, PLAN_FILE, template_type
        )
        registry["next_number"] = NEXT_NUM + 1

        # STEP 10: Save updated registry
        if not save_registry(registry):
            error_msg = "Failed to save registry after plan creation"
            logger.error(f"[{MODULE_NAME}] {error_msg}")
            messages.append({"type": "warning", "text": f"[WARNING] {error_msg}"})

        # STEP 11: Update dashboards (3-tier: modules log, handlers don't)
        dashboard_success = update_dashboard_local()
        central_success = push_to_plans_central()

        # Log dashboard update results
        if not dashboard_success:
            logger.warning(f"[{MODULE_NAME}] Failed to update DASHBOARD.local.json")
        if not central_success:
            logger.warning(f"[{MODULE_NAME}] Failed to update PLANS.central.json")

        # STEP 11b: Push flow section to branch's dashboard via write-through
        branch_dashboard_success = push_flow_to_branch_dashboard(target_dir)
        if not branch_dashboard_success:
            messages.append({"type": "dim", "text": f"No branch dashboard at {target_dir} -- no branch is tracking this plan"})

        # STEP 12: Log success
        logger.info(f"[{MODULE_NAME}] Created FPLAN-{NEXT_NUM:04d} in {RELATIVE_LOCATION}")

        # Build display message
        display_msg = display_plan_created(NEXT_NUM, RELATIVE_LOCATION, subject, template_type)
        messages.append({"type": "display", "text": display_msg})

        # Fire trigger event for plan creation
        try:
            from aipass.trigger.apps.modules.core import trigger
            trigger.fire('plan_created', plan_number=NEXT_NUM, location=RELATIVE_LOCATION, subject=subject)
        except ImportError:
            pass  # Trigger not available, silent fallback

        return True, NEXT_NUM, RELATIVE_LOCATION, template_type, "", messages

    except Exception as e:
        error_msg = f"Error creating plan: {e}"
        logger.error(f"[{MODULE_NAME}] {error_msg}")
        return False, 0, "", "", error_msg, messages
