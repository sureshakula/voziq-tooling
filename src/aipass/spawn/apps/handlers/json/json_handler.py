# =================== AIPass ====================
# Name: json_handler.py
# Description: JSON file read/write operations for spawn
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================

"""JSON handler for spawn module."""

import json
from pathlib import Path
from typing import Any, Optional


def read_json(file_path: Path) -> Optional[dict]:
    """Read and parse a JSON file."""
    try:
        return json.loads(file_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def write_json(file_path: Path, data: Any, indent: int = 2) -> bool:
    """Write data to a JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=indent) + "\n")
        return True
    except OSError:
        return False
