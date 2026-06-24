# =================== AIPass ====================
# Name: auto_process.py
# Description: Automated pool + rollover entry point
# Version: 1.0.0
# Created: 2026-06-06
# Modified: 2026-06-06
# =============================================

"""
Auto-process handler — session-start pool + rollover entry point.

Single callable the hook engine fires each session to:
1. Process any files dropped into memory_pool/ (vectorize + archive)
2. Check/run rollover for .trinity/ files exceeding limits

Idempotent: safe to call every session. Fast no-op when nothing to do.
Pool uses upsert with content-hash IDs — re-processing same files is a no-op.

HOOK ENGINE CONTRACT:
  Module: aipass.memory.apps.handlers.intake.auto_process
  Function: auto_process()
  Invocation: importlib.import_module('aipass.memory.apps.handlers.intake.auto_process').auto_process()
  Returns: dict with success, pool, and rollover results
"""

from pathlib import Path
from typing import Any, Dict

from aipass.prax import logger
from aipass.memory.apps.handlers.json import json_handler, config_loader

_MEMORY_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _load_pool_enabled() -> bool:
    return config_loader.section("memory_pool").get("enabled", False)


def run_pool_processing() -> Dict[str, Any]:
    """
    Process memory pool files if enabled.

    Checks config, calls process_memory_pool(), returns summary.
    Fast no-op when pool is empty or disabled.

    Returns:
        dict with success/skipped, files_processed, total_chunks
    """
    if not _load_pool_enabled():
        return {"skipped": True, "reason": "memory_pool disabled in config"}

    try:
        from aipass.memory.apps.handlers.intake.pool_processor import process_memory_pool

        pool_result = process_memory_pool()
        result = {
            "success": pool_result.get("success", False),
            "files_processed": pool_result.get("files_processed", 0),
            "total_chunks": pool_result.get("total_chunks", 0),
        }
        if pool_result.get("files_processed", 0) > 0:
            logger.info(
                f"[auto_process] Pool: {pool_result['files_processed']} files, "
                f"{pool_result.get('total_chunks', 0)} chunks"
            )

        json_handler.log_operation(
            "run_pool_processing",
            {
                "files_processed": result.get("files_processed", 0),
                "success": result.get("success", False),
            },
        )

        return result
    except Exception as e:
        logger.warning(f"[auto_process] Pool processing failed: {e}")
        return {"success": False, "error": str(e)}


def _run_rollover_check() -> Dict[str, Any]:
    """
    Check all branches for rollover triggers and execute if needed.

    Returns:
        dict with success/skipped and rollover details
    """
    try:
        from aipass.memory.apps.handlers.monitor.detector import check_all_branches

        check_result = check_all_branches()
        triggers = check_result.get("triggers", []) if check_result else []

        if not triggers:
            return {"skipped": True, "reason": "no rollover triggers"}

        from aipass.memory.apps.handlers.rollover.orchestrator import execute_rollover

        rollover_result = execute_rollover()
        result = {
            "success": rollover_result.get("success", False),
            "triggers": rollover_result.get("triggers_count", 0),
            "processed": rollover_result.get("success_count", 0),
        }
        logger.info(f"[auto_process] Rollover: {result['processed']}/{result['triggers']} triggers processed")
        return result
    except Exception as e:
        logger.warning(f"[auto_process] Rollover check failed: {e}")
        return {"success": False, "error": str(e)}


def auto_process() -> Dict[str, Any]:
    """
    Single idempotent entry point for session-start auto-processing.

    Processes memory pool files and checks/runs rollover if needed.
    Fast no-op when pool is empty and no rollover triggers.
    Safe to call every session.

    Returns:
        dict with success, pool, and rollover results
    """
    result: Dict[str, Any] = {"success": True, "pool": None, "rollover": None}

    if not _load_pool_enabled():
        result["pool"] = {"skipped": True, "reason": "memory_pool disabled in config"}
        result["rollover"] = {"skipped": True}
        logger.info("[auto_process] Skipped — memory_pool disabled in config")
        return result

    # 1. Process pool files
    pool_result = run_pool_processing()
    result["pool"] = pool_result
    if pool_result.get("success") is False:
        result["success"] = False

    # 2. Check/run rollover
    rollover_result = _run_rollover_check()
    result["rollover"] = rollover_result
    if rollover_result.get("success") is False:
        result["success"] = False

    json_handler.log_operation(
        "auto_process",
        {
            "pool_files": result.get("pool", {}).get("files_processed", 0),
            "rollover_triggered": not result.get("rollover", {}).get("skipped", False),
            "success": result["success"],
        },
    )

    return result
