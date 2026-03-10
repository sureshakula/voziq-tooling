# =================== AIPass ====================
# Name: pending_work.py
# Description: Pending Work Handler
# Version: 1.0.0
# Created: 2026-02-17
# Modified: 2026-02-17
# =============================================

"""
Pending Work Handler

Read/write utils for .pending_work.json per branch.
Tracks dispatch workflows, waiting_for states, and next_action queues.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

PENDING_WORK_FILENAME = ".pending_work.json"


def _get_pending_path(branch_path: Path) -> Path:
    """Get the pending work file path for a branch."""
    if branch_path == Path("/"):
        return Path.cwd() / ".ai_mail.local" / PENDING_WORK_FILENAME
    return branch_path / ".ai_mail.local" / PENDING_WORK_FILENAME


def load_pending_work(branch_path: Path) -> Dict[str, Any]:
    """
    Load pending work for a branch.

    Args:
        branch_path: Path to the branch directory

    Returns:
        Pending work dict with 'workflows' array
    """
    pending_path = _get_pending_path(branch_path)

    if not pending_path.exists():
        return {"workflows": []}

    try:
        with open(pending_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "workflows" not in data:
            data["workflows"] = []
        return data
    except (json.JSONDecodeError, OSError):
        return {"workflows": []}


def save_pending_work(branch_path: Path, data: Dict[str, Any]) -> bool:
    """
    Save pending work for a branch.

    Args:
        branch_path: Path to the branch directory
        data: Pending work dict to save

    Returns:
        True if saved successfully
    """
    pending_path = _get_pending_path(branch_path)
    pending_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(pending_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def add_workflow(
    branch_path: Path,
    dispatch_id: str,
    dispatched_to: str,
    subject: str,
    waiting_for: Optional[str] = None,
    next_action: Optional[str] = None
) -> bool:
    """
    Add a workflow entry to a branch's pending work.

    Adds a new dispatch workflow to track pending communications and actions.

    Args:
        branch_path: Path to the branch directory
        dispatch_id: Message ID of the dispatched email
        dispatched_to: Target branch email (e.g., @flow)
        subject: Subject of the dispatched email
        waiting_for: What the branch is waiting for (e.g., reply from @flow)
        next_action: What to do when the response arrives

    Returns:
        True if added successfully
    """
    data = load_pending_work(branch_path)

    entry = {
        "dispatch_id": dispatch_id,
        "dispatched_to": dispatched_to,
        "subject": subject,
        "status": "waiting",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if waiting_for:
        entry["waiting_for"] = waiting_for
    if next_action:
        entry["next_action"] = next_action

    data["workflows"].append(entry)
    return save_pending_work(branch_path, data)


def clear_workflow(branch_path: Path, dispatch_id: str) -> bool:
    """
    Remove a completed workflow entry.

    Args:
        branch_path: Path to the branch directory
        dispatch_id: Message ID to remove

    Returns:
        True if removed successfully
    """
    data = load_pending_work(branch_path)
    data["workflows"] = [
        w for w in data["workflows"]
        if w.get("dispatch_id") != dispatch_id
    ]
    return save_pending_work(branch_path, data)


def has_pending_work(branch_path: Path) -> bool:
    """
    Check if a branch has any pending workflows.

    Args:
        branch_path: Path to the branch directory

    Returns:
        True if there are active workflows
    """
    data = load_pending_work(branch_path)
    return len(data.get("workflows", [])) > 0
