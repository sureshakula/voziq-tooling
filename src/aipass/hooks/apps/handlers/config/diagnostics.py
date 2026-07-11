# =================== AIPass ====================
# Name: diagnostics.py
# Version: 1.0.0
# Description: JSONL diagnostic logging for hook engine
# Branch: hooks
# Layer: apps/handlers/config
# Created: 2026-05-19
# Modified: 2026-05-19
# =============================================

"""JSONL diagnostic logging — appends structured entries for hook activity."""

from pathlib import Path

from aipass.prax import append_jsonl
from aipass.prax.apps.modules.logger import system_logger as logger

BRANCH_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LOG_FILE = BRANCH_ROOT / "logs" / "engine.jsonl"


def log_entry(entry: dict) -> None:
    """Append a JSONL log entry for detailed diagnostics."""
    try:
        append_jsonl(LOG_FILE, entry)
    except OSError as exc:
        logger.error("[HOOKS] log write failed: %s", exc)


def tail_log(count: int = 20) -> list[str]:
    """Return the last N lines from the engine log."""
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text().strip().split("\n")
    return lines[-count:]
