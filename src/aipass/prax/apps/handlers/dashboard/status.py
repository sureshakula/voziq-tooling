# =================== AIPass ====================
# Name: status.py
# Description: Dashboard Status Calculation Handler
# Version: 0.2.0
# Created: 2026-02-25
# Modified: 2026-03-09
# =============================================

"""
Dashboard Status Handler

Handles status calculations and branch path resolution.
All business logic for dashboard status operations.
"""

import json
from pathlib import Path
from typing import Dict, List

from aipass.prax.apps.modules.logger import get_direct_logger
from aipass.prax.apps.handlers.json import json_handler

logger = get_direct_logger()


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains AIPASS_REGISTRY.json)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()


AIPASS_REGISTRY = _find_repo_root() / "AIPASS_REGISTRY.json"


def _read_todo_count(branch_path: Path) -> int:
    """Read todos[] length from .trinity/local.json."""
    local_path = branch_path / ".trinity" / "local.json"
    if not local_path.exists():
        return 0
    try:
        data = json.loads(local_path.read_text())
        return len(data.get("todos", []))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read todos from %s: %s", local_path, exc)
        return 0


def _read_mail_counts(branch_path: Path) -> tuple:
    """Read new/opened mail counts from .ai_mail.local/inbox.json."""
    inbox_path = branch_path / ".ai_mail.local" / "inbox.json"
    if not inbox_path.exists():
        return (0, 0)
    try:
        data = json.loads(inbox_path.read_text())
        new_mail = 0
        opened_mail = 0
        for msg in data.get("messages", []):
            status = msg.get("status", "")
            if status == "new" or (not status and not msg.get("read", False)):
                new_mail += 1
            elif status == "opened":
                opened_mail += 1
        return (new_mail, opened_mail)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read inbox from %s: %s", inbox_path, exc)
        return (0, 0)


def calculate_quick_status(sections: Dict, branch_path: "Path | None" = None) -> Dict:
    """
    Calculate quick status from branch data sources.

    Sources counts directly from local files (inbox.json, local.json).

    Args:
        sections: All dashboard sections
        branch_path: Optional path to branch root (for sourcing counts)

    Returns:
        Quick status dict with summary data
    """
    flow = sections.get("flow", {})

    if branch_path:
        new_mail, opened_mail = _read_mail_counts(branch_path)
        todo_count = _read_todo_count(branch_path)
    else:
        new_mail, opened_mail, todo_count = 0, 0, 0
    active_plans = flow.get("active_plans", 0)

    action_required = new_mail > 0 or active_plans > 0

    summary_parts = []
    if new_mail:
        summary_parts.append(f"{new_mail} new emails")
    if opened_mail:
        summary_parts.append(f"{opened_mail} opened")
    if active_plans:
        summary_parts.append(f"{active_plans} active plans")
    if todo_count:
        summary_parts.append(f"{todo_count} todos")

    result = {
        "new_mail": new_mail,
        "opened_mail": opened_mail,
        "active_plans": active_plans,
        "todo_count": todo_count,
        "action_required": action_required,
        "summary": ", ".join(summary_parts) if summary_parts else "All clear",
    }

    json_handler.log_operation(
        "status_calculated",
        {
            "action_required": action_required,
            "new_mail": new_mail,
            "active_plans": active_plans,
            "todo_count": todo_count,
        },
    )

    return result


def get_branch_paths() -> List[Path]:
    """
    Get all branch paths from registry

    Returns:
        List of branch paths

    Raises:
        FileNotFoundError: If AIPASS_REGISTRY.json doesn't exist
        json.JSONDecodeError: If registry is corrupted
    """
    if not AIPASS_REGISTRY.exists():
        raise FileNotFoundError(f"AIPASS_REGISTRY.json not found: {AIPASS_REGISTRY}")

    repo_root = _find_repo_root()
    data = json.loads(AIPASS_REGISTRY.read_text())
    paths = []
    for b in data.get("branches", []):
        raw = Path(b.get("path", ""))
        paths.append(raw if raw.is_absolute() else repo_root / raw)
    return paths


def resolve_branch_path(branch_ref: str) -> Path:
    """
    Resolve @branch reference to filesystem path via AIPASS_REGISTRY.json.

    Handler-layer function: performs file I/O to read registry and
    resolve branch name to its directory path.

    Args:
        branch_ref: Branch reference like "@flow" or "@vera"

    Returns:
        Path to the branch directory

    Raises:
        FileNotFoundError: If registry missing or branch not found
    """
    name = branch_ref.lstrip("@").upper()

    if not AIPASS_REGISTRY.exists():
        raise FileNotFoundError("AIPASS_REGISTRY.json not found")

    repo_root = _find_repo_root()
    data = json.loads(AIPASS_REGISTRY.read_text())
    for branch in data.get("branches", []):
        if branch.get("name", "").upper() == name:
            raw = Path(branch["path"])
            path = raw if raw.is_absolute() else repo_root / raw
            if path.exists():
                return path
            raise FileNotFoundError(f"Branch path does not exist: {path}")

    raise FileNotFoundError(f"Branch '{name}' not found in registry")
