# =================== AIPass ====================
# Name: pr_status_sync.py
# Description: PR event handlers — sync STATUS.md on PR create/merge
# Version: 1.0.0
# Created: 2026-03-30
# Modified: 2026-03-30
# =============================================

"""
PR Status Sync Event Handlers

Handles pr_created and pr_merged events by running
'drone @prax status sync' in a fire-and-forget subprocess.

Events:
    pr_created  — fired when a PR is opened
        data: {branch: str, pr_url: str}
    pr_merged   — fired when a PR is merged
        data: {pr_number: str, title: str}
"""

import subprocess
from typing import Any

from aipass.trigger.apps.config import TRIGGER_ROOT
from aipass.trigger.apps.handlers.json import json_handler

try:
    from aipass.prax import append_jsonl as _append_jsonl
except Exception:
    _append_jsonl = None

_HANDLER_LOG = TRIGGER_ROOT / "logs" / "pr_status_sync_handler.jsonl"


def _log_info(message: str) -> None:
    """Log to file (recursion-safe prax path)."""
    if _append_jsonl is None:
        return
    try:
        _append_jsonl(_HANDLER_LOG, {"level": "INFO", "msg": message})
    except Exception:
        pass  # seedgo:bypass meta-logging


def _run_status_sync(reason: str) -> None:
    """Fire-and-forget: run drone @prax status sync."""
    try:
        subprocess.Popen(
            ["drone", "@prax", "status", "sync"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log_info(f"status sync launched ({reason})")
    except Exception as exc:
        _log_info(f"status sync failed ({reason}): {exc}")


def handle_pr_created(
    branch: str | None = None,
    pr_url: str | None = None,
    **kwargs: Any,
) -> None:
    """Handle pr_created event — trigger STATUS.md sync.

    Args:
        branch: Branch that created the PR
        pr_url: URL of the created PR
        **kwargs: Additional event data (ignored)
    """
    _run_status_sync(f"pr_created by {branch or 'unknown'}")
    json_handler.log_operation(
        "pr_created_event",
        {
            "branch": branch or "unknown",
            "pr_url": pr_url or "",
        },
    )


def handle_pr_merged(
    pr_number: str | None = None,
    title: str | None = None,
    **kwargs: Any,
) -> None:
    """Handle pr_merged event — trigger STATUS.md sync.

    Args:
        pr_number: PR number that was merged
        title: PR title
        **kwargs: Additional event data (ignored)
    """
    _run_status_sync(f"pr_merged #{pr_number or '?'}")
    json_handler.log_operation(
        "pr_merged_event",
        {
            "pr_number": pr_number or "",
            "title": title or "",
        },
    )
