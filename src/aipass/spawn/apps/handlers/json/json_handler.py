# =================== AIPass ====================
# Name: json_handler.py
# Description: Spawn JSON handler — configured instance of aipass.common
# Version: 3.0.0
# Created: 2026-03-07
# Modified: 2026-06-06
# =============================================

"""Spawn JSON handler — thin shim over aipass.common.json_handler.

Creates a JsonHandler instance configured with spawn's json_dir.
All functions are re-exported for backward-compatible imports.
"""

from pathlib import Path

from aipass.common.json_handler import JsonHandler

_SPAWN_ROOT = Path(__file__).resolve().parents[3]
_JSON_DIR = _SPAWN_ROOT / "spawn_json"

_handler = JsonHandler(json_dir=_JSON_DIR)

MAX_LOG_ENTRIES = JsonHandler.MAX_LOG_ENTRIES

read_json = _handler.read_json
write_json = _handler.write_json
validate_json_structure = _handler.validate_json_structure
get_json_path = _handler.get_json_path
ensure_json_exists = _handler.ensure_json_exists
ensure_module_jsons = _handler.ensure_module_jsons
load_json = _handler.load_json
save_json = _handler.save_json
log_operation = _handler.log_operation
_create_default = _handler._create_default
