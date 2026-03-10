# =================== AIPass ====================
# Name: append_closed_plan.py
# Description: Closed Plans Local Registry Handler
# Version: 0.1.0
# Created: 2026-03-03
# Modified: 2026-03-03
# =============================================

"""
Closed Plans Append Handler

Appends a closed plan entry to the branch's CLOSED_PLANS.local.json file.
Creates the file if it doesn't exist.
"""

import json
from pathlib import Path

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[4]

# External: Prax logger
from aipass.prax.apps.modules.logger import system_logger as logger

MODULE_NAME = "append_closed_plan"
CLOSED_PLANS_FILE = "CLOSED_PLANS.local.json"


def append_to_closed_plans(plan_key: str, plan_info: dict, plan_location: Path) -> bool:
    """
    Append a closed plan entry to the branch's CLOSED_PLANS.local.json

    Args:
        plan_key: Plan number string (e.g., "0405")
        plan_info: Plan info dict from registry (must contain 'closed', may contain 'subject', 'relative_path')
        plan_location: Path to the directory where the plan resides (branch directory)

    Returns:
        True on success, False on failure
    """
    try:
        plan_id = f"FPLAN-{plan_key}"

        # Extract date (YYYY-MM-DD) from the closed ISO timestamp
        closed_raw = plan_info.get("closed", "")
        date_closed = closed_raw[:10] if closed_raw else ""

        # Build the entry
        entry = {
            "plan_id": plan_id,
            "type": "FPLAN",
            "subject": plan_info.get("subject", ""),
            "date_closed": date_closed,
            "location": plan_info.get("relative_path", "")
        }

        # Read existing file or create new structure
        closed_plans_path = plan_location / CLOSED_PLANS_FILE

        if closed_plans_path.exists():
            with open(closed_plans_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"closed_plans": []}

        # Check for duplicate plan_id before appending
        existing_ids = {p.get("plan_id") for p in data.get("closed_plans", [])}
        if plan_id in existing_ids:
            logger.info(f"[{MODULE_NAME}] {plan_id} already in {CLOSED_PLANS_FILE} at {plan_location}, skipping")
            return True

        # Append and write
        data["closed_plans"].append(entry)

        with open(closed_plans_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')

        logger.info(f"[{MODULE_NAME}] Appended {plan_id} to {closed_plans_path}")
        return True

    except Exception as e:
        logger.warning(f"[{MODULE_NAME}] Failed to append closed plan: {e}")
        return False
