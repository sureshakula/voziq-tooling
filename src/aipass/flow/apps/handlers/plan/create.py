# =================== AIPass ====================
# Name: create.py
# Description: Plan creation handler with registry integration
# Version: 1.1.0
# Created: 2025-11-16
# Modified: 2025-11-16
# =============================================

"""
Plan Creation Handler

Domain-specific handler for PLAN file operations.
Follows handler independence principles - no cross-domain imports.

Handler Responsibilities:
- Write PLAN files to filesystem
- Create registry entry data structures
- Validate paths and filenames
- Handle domain-specific business logic

NOT Handler Responsibilities (module's job):
- Loading/saving registry (cross-domain)
- Template generation (cross-domain)
- Orchestrating workflows

Usage:
    from aipass.flow.apps.handlers.plan.create import write_plan_file, create_registry_entry

    # Write plan file
    success, error = write_plan_file(plan_file_path, content)

    # Create registry entry
    entry = create_registry_entry(plan_number, target_dir, subject, template_type)
"""

# INFRASTRUCTURE IMPORT PATTERN
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from aipass.flow.apps.handlers.json import json_handler
_PKG_ROOT = Path(__file__).resolve().parents[4]
FLOW_ROOT = _PKG_ROOT / "flow"

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "plan_create_handler"
ECOSYSTEM_ROOT = _PKG_ROOT

# =============================================
# HANDLER FUNCTIONS (Domain-specific operations)
# =============================================

def write_plan_file(plan_file: Path, content: str) -> Tuple[bool, str]:
    """
    Write PLAN file to filesystem

    Pure handler function - no cross-domain dependencies.

    Args:
        plan_file: Path to PLAN file
        content: Template content to write

    Returns:
        (success, error_message)
    """
    try:
        # Validate path doesn't already exist
        if plan_file.exists():
            error_msg = f"{plan_file.name} already exists in {plan_file.parent.name}/"
            return False, error_msg

        # Ensure parent directory exists
        if not plan_file.parent.exists():
            error_msg = f"Directory {plan_file.parent} does not exist"
            return False, error_msg

        # Write file
        with open(plan_file, 'w', encoding='utf-8') as f:
            f.write(content)

        json_handler.log_operation("plan_file_written", {"file_path": str(plan_file), "success": True})
        return True, ""

    except Exception as e:
        error_msg = f"Failed to write plan file: {e}"
        return False, error_msg


def create_registry_entry(
    plan_number: int,
    target_dir: Path,
    subject: str,
    template_type: str
) -> Dict[str, Any]:
    """
    Create registry entry data structure for a new plan

    Pure data transformation - no I/O operations.

    Args:
        plan_number: Plan number
        target_dir: Target directory path
        subject: Plan subject
        template_type: Template type used

    Returns:
        Registry entry dict
    """
    # Calculate relative location
    try:
        RELATIVE_LOCATION = str(target_dir.relative_to(ECOSYSTEM_ROOT))
        if RELATIVE_LOCATION == ".":
            RELATIVE_LOCATION = "root"
    except ValueError:
        RELATIVE_LOCATION = str(target_dir)

    # Build plan file path
    PLAN_FILE = target_dir / f"FPLAN-{plan_number:04d}.md"

    # Create entry
    return {
        "location": str(target_dir),
        "relative_path": RELATIVE_LOCATION,
        "created": datetime.now(timezone.utc).isoformat(),
        "subject": subject,
        "status": "open",
        "file_path": str(PLAN_FILE),
        "template_type": template_type
    }


def auto_close_orphaned_plans(registry: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Auto-close plans whose files no longer exist

    Modifies registry dict in-place and returns it with count.

    Args:
        registry: Registry dict to scan

    Returns:
        (modified_registry, auto_closed_count)
    """
    auto_closed_count = 0

    for num, info in registry.get("plans", {}).items():
        if info["status"] == "open":
            plan_file = Path(info.get("file_path", ""))
            if plan_file and not plan_file.exists():
                # Auto-close missing plan
                info["status"] = "closed"
                info["closed"] = datetime.now(timezone.utc).isoformat()
                info["closed_reason"] = "auto_closed_missing_file"
                auto_closed_count += 1

    return registry, auto_closed_count
