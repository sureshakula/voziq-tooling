# =================== AIPass ====================
# Name: branch_resolve.py
# Description: @ branch reference resolution
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Branch Resolution Handler

Resolves @branch references to filesystem paths via BRANCH_REGISTRY.json.
Extracted from dplan_flow.py to comply with 3-tier architecture.

Usage:
    from aipass.flow.apps.handlers.dplan.branch_resolve import resolve_branch_target
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

BRANCH_REGISTRY_PATH = Path.home() / "BRANCH_REGISTRY.json"


# =============================================================================
# OPERATIONS
# =============================================================================

def resolve_branch_target(branch_ref: str) -> Dict[str, Any]:
    """
    Resolve @branch reference to a filesystem path via BRANCH_REGISTRY.json.

    Args:
        branch_ref: Branch reference like "@vera" or "@team_1"

    Returns:
        Dict with keys:
            success (bool): Whether resolution succeeded
            path (Optional[Path]): Resolved path, or None on failure
            error (str): Error description if failed, empty string on success
    """
    name = branch_ref.lstrip("@").upper()

    if not BRANCH_REGISTRY_PATH.exists():
        return {
            "success": False,
            "path": None,
            "error": f"BRANCH_REGISTRY.json not found at {BRANCH_REGISTRY_PATH}",
        }

    try:
        data = json.loads(BRANCH_REGISTRY_PATH.read_text(encoding="utf-8"))

        for branch in data.get("branches", []):
            if branch.get("name", "").upper() == name:
                branch_path = Path(branch["path"])
                if branch_path.exists():
                    return {
                        "success": True,
                        "path": branch_path,
                        "error": "",
                    }
                else:
                    return {
                        "success": False,
                        "path": None,
                        "error": f"Branch path does not exist: {branch_path}",
                    }

        return {
            "success": False,
            "path": None,
            "error": f"Branch '{name}' not found in registry",
        }

    except Exception as e:
        return {
            "success": False,
            "path": None,
            "error": f"Failed to read branch registry: {e}",
        }
