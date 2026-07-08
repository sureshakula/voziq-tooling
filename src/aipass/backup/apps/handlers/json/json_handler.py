# =================== AIPass ====================
# Name: json_handler.py
# Description: Generic JSON ops — read/write, self-healing, atomic writes
# Version: 1.0.0
# Created: 2026-04-17
# Modified: 2026-04-23
# =============================================

"""JSON handler — generic persistence utilities shared across backup modules."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from aipass.prax import logger


def log_operation(operation: str, data: dict) -> None:
    """Record an operation entry to the backup system log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        **data,
    }
    log_dir = Path(__file__).resolve().parents[3] / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "operations.jsonl"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError as e:
        logger.warning(f"Failed to write operation log: {e}")


def load_json(path: str) -> dict:
    """Load JSON from path with self-healing on corruption."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Corrupt JSON at {p}, renaming to .corrupt: {e}")
        corrupt = p.with_suffix(p.suffix + ".corrupt")
        p.rename(corrupt)
        return {}


def save_json(path: str, data: dict) -> None:
    """Atomic write JSON to path (write temp -> rename)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
            f.write("\n")
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError as e:
            logger.warning(f"Failed to clean up temp file {tmp}: {e}")
        raise


# =============================================
