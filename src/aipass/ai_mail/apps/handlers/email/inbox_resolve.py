# =================== AIPass ====================
# Name: inbox_resolve.py
# Description: Inbox Resolution Handler
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Inbox Resolution Handler

Resolves inbox paths and branch info for inbox viewing.
Independent handler - no module or display dependencies.
"""

from pathlib import Path
from typing import Dict, Optional, Any, Callable, Tuple

from aipass.ai_mail.apps.handlers.json import json_handler


def resolve_inbox_target(
    args_first: Optional[str],
    repo_root: Path,
    get_branch_by_email_fn: Callable,
    get_current_user_fn: Callable,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Resolve which inbox to display based on args.

    Args:
        args_first: First argument (e.g., '@branch') or None
        repo_root: Repository root path
        get_branch_by_email_fn: Callable to look up branch by email
        get_current_user_fn: Callable to detect current user

    Returns:
        Tuple of (success, result_dict).
        result_dict contains:
            inbox_file: Path to inbox.json
            display_name: str for display
            target_branch: str | None (the explicit target, or None for current)
            error: str | None (set when success is False)
    """
    json_handler.log_operation("resolve_inbox_target", {"target": args_first})
    target_branch = None
    if args_first and args_first.startswith("@"):
        target_branch = args_first

    if target_branch:
        branch_info = get_branch_by_email_fn(target_branch)
        if not branch_info:
            return False, {"error": f"Unknown branch: {target_branch}"}

        branch_path = Path(branch_info["path"])
        if not branch_path.is_absolute():
            branch_path = (repo_root / branch_path).resolve()
        mailbox_path = branch_path / ".ai_mail.local"
        display_name = branch_info.get("name", target_branch)
    else:
        user_info = get_current_user_fn()
        mailbox_path = Path(user_info["mailbox_path"])
        display_name = user_info.get("display_name", "")

    inbox_file = mailbox_path / "inbox.json"

    return True, {
        "inbox_file": inbox_file,
        "display_name": display_name,
        "target_branch": target_branch,
        "error": None,
    }
