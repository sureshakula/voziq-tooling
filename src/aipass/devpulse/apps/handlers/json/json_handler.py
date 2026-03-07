
# ===================AIPASS====================
# META DATA HEADER
# Name: json_handler.py - JSON Handler
# Date: 2026-03-07
# Version: 1.0.0
# Category: devpulse/handlers/json
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-03-07): Initial implementation
#
# CODE STANDARDS:
#   - Satisfies Seed architecture standard for apps/handlers/json/ path
# =============================================

"""
JSON Handler for DevPulse

Handles JSON read/write operations for devpulse_json/ storage.
"""

import json
from pathlib import Path
from typing import Any, Optional

# Infrastructure paths (package-relative)
_DEVPULSE_ROOT = Path(__file__).resolve().parents[3]  # devpulse/
DEVPULSE_JSON_DIR = _DEVPULSE_ROOT / "devpulse_json"


def load_json(file_path: Path) -> Any:
    """Load and return JSON data from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """Save data as JSON to file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.write('\n')


def ensure_json_exists(file_path: Path, default: Optional[Any] = None) -> Path:
    """Ensure a JSON file exists, creating with default content if missing."""
    if not file_path.exists():
        save_json(file_path, default if default is not None else {})
    return file_path


def get_json_path(filename: str) -> Path:
    """Get the path to a JSON file in devpulse_json/."""
    return DEVPULSE_JSON_DIR / filename
