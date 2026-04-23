# =================== AIPass ====================
# Name: discovery.py
# Description: Branch Discovery Handler
# Version: 2.0.0
# Created: 2026-03-05
# Modified: 2026-03-06
# =============================================

"""
Branch Discovery Handler

Discovers all branches from AIPASS_REGISTRY.json for diagnostics scanning.
"""

import json
from pathlib import Path
from typing import Dict, List

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.seedgo.apps.handlers.json import json_handler


def _find_registry() -> Path:
    """Find *_REGISTRY.json — CWD-first for external project support, then __file__ fallback."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        matches = sorted(parent.glob("*_REGISTRY.json"))
        if matches:
            return matches[0]
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        matches = sorted(parent.glob("*_REGISTRY.json"))
        if matches:
            return matches[0]
    return Path.cwd() / "AIPASS_REGISTRY.json"


def discover_branches() -> List[Dict]:
    """
    Discover all branches from AIPASS_REGISTRY.json for diagnostics.

    Returns:
        List of dicts with 'name' and 'path' keys
    """
    branches = []
    registry_path = _find_registry()

    if not registry_path.exists():
        return branches

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry_data = json.load(f)

        registry_dir = registry_path.parent

        for branch in registry_data.get("branches", []):
            branch_name = branch.get("name", "")
            raw_path = branch.get("path", "")
            branch_path = Path(raw_path)

            if not branch_path.is_absolute():
                branch_path = (registry_dir / branch_path).resolve()

            if branch_path.exists():
                branches.append({"name": branch_name, "path": str(branch_path)})

        json_handler.log_operation("diagnostics_discovered", {"count": len(branches)})
        return sorted(branches, key=lambda x: x["name"])

    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error discovering branches: {e}")
        return branches
