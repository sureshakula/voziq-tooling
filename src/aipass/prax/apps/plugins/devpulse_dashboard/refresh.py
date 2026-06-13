# =================== AIPass ====================
# Name: refresh.py
# Description: Orchestrates all devpulse custom dashboard sections
# Version: 1.0.0
# Created: 2026-05-16
# Modified: 2026-05-16
# =============================================

"""Refresh orchestrator for devpulse dashboard plugin.

Calls each section builder in sequence. Each builder gathers its own data
and writes to DASHBOARD.local.json via prax's write_section() API.
Failures in one section don't block others.
"""

from pathlib import Path
from typing import Dict, List, Optional

from aipass.prax.apps.modules.logger import system_logger as logger


# Devpulse branch path — resolved relative to this file's location
_AIPASS_SRC = Path(__file__).resolve().parents[4]  # .../src/aipass/
DEVPULSE_PATH = _AIPASS_SRC / "devpulse"


def refresh(branch_path: Optional[Path] = None) -> Dict:
    """Refresh all devpulse custom dashboard sections.

    Args:
        branch_path: Override path to devpulse branch root.
            Defaults to auto-resolved path.

    Returns:
        Dict with results per section: {section_name: {"success": bool, "error": str|None}}
    """
    target = branch_path or DEVPULSE_PATH
    results: Dict[str, Dict] = {}

    builders: List[tuple] = [
        ("git", _refresh_git),
        ("dispatch", _refresh_dispatch),
    ]

    for name, builder_fn in builders:
        try:
            builder_fn(target)
            results[name] = {"success": True, "error": None}
        except Exception as e:
            logger.error("Failed to refresh section '%s': %s", name, e)
            results[name] = {"success": False, "error": str(e)}

    return results


def _refresh_git(branch_path: Path) -> None:
    from .git_section import build_git_section

    build_git_section(branch_path)


def _refresh_dispatch(branch_path: Path) -> None:
    from .dispatch_section import build_dispatch_section

    build_dispatch_section(branch_path)
