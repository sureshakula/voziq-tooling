# =================== AIPass ====================
# Name: memory_pool.py
# Description: Memory pool auto-process event handler — observability for pool processing
# Version: 1.0.0
# Created: 2026-06-06
# Modified: 2026-06-06
# =============================================

"""
Memory Pool Auto-Processed Event Handler

Handles memory_pool_auto_processed events fired by the hook engine after
calling @memory's auto_process() entry point. Makes pool processing visible
in AIPass's event/error tracking (not just buried in engine.jsonl).

On success: logs the result for monitoring.
On failure: fires error_detected so the error enters the Medic dispatch pipeline.

Event data expected:
    - success: bool — overall result from auto_process()
    - branch: str — branch that triggered the processing (or "__global__")
    - pool: dict — {status, files_processed, total_chunks}
    - rollover: dict — {status, triggers, processed}
    - error: str | None — error message if success=False
"""

from datetime import datetime, timezone
from typing import Any

from aipass.trigger.apps.config import TRIGGER_ROOT
from aipass.trigger.apps.handlers.json import json_handler

_HANDLER_LOG = TRIGGER_ROOT / "logs" / "memory_pool_handler.log"


def _log_warning(message: str) -> None:
    """Log warning to file (event handlers cannot import prax logger — causes recursion)."""
    try:
        _HANDLER_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(_HANDLER_LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts} | WARNING | {message}\n")
    except Exception:
        pass  # Meta-logging: cannot log a failure to log


def handle_memory_pool_auto_processed(
    success: bool | None = None,
    branch: str | None = None,
    pool: dict | None = None,
    rollover: dict | None = None,
    error: str | None = None,
    **kwargs: Any,
) -> None:
    """Handle memory_pool_auto_processed event.

    On success: logs pool/rollover stats for monitoring.
    On failure: fires error_detected to enter the Medic dispatch pipeline.

    Args:
        success: Overall result from auto_process()
        branch: Branch that triggered processing
        pool: Pool processing result dict
        rollover: Rollover result dict
        error: Error message if success=False
        **kwargs: Additional event data (may include fire_event callback)
    """
    pool = pool or {}
    rollover = rollover or {}
    files_processed = pool.get("files_processed", 0)
    total_chunks = pool.get("total_chunks", 0)

    if success:
        json_handler.log_operation(
            "memory_pool_auto_processed",
            {
                "success": True,
                "files_processed": files_processed,
                "total_chunks": total_chunks,
                "pool_status": pool.get("status", "unknown"),
                "rollover_status": rollover.get("status", "unknown"),
            },
        )
        return

    error_msg = error or "memory pool auto-process failed (no detail)"
    _log_warning(f"auto-process failure: {error_msg}")

    json_handler.log_operation(
        "memory_pool_auto_processed",
        {
            "success": False,
            "error": error_msg,
        },
    )

    fire_event = kwargs.get("fire_event")
    if fire_event is not None:
        fire_event(
            "error_detected",
            branch=branch or "memory",
            error_type="MemoryPoolAutoProcessError",
            message=error_msg,
            source_file="auto_process.py",
        )
