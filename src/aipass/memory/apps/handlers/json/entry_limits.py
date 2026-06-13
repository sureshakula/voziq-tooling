# =================== AIPass ====================
# Name: entry_limits.py
# Description: Entry limits config reader for memory files
# Version: 1.0.0
# Created: 2026-06-13
# Modified: 2026-06-13
# =============================================

"""
Entry Limits Config Reader

Reads the entry_limits section from memory.config.json and returns
the effective limits for a given branch, with per_branch overrides
deep-merged over the default entry_types.

Phase 1 only: reader + safe defaults. No enforcement, no validation,
no write-path integration.

Usage:
    from aipass.memory.apps.handlers.json.entry_limits import load_entry_limits

    limits = load_entry_limits("devpulse")
    # => {"enabled": True, "enforce": False, "entry_types": {...}}
"""

import copy
import json
from pathlib import Path
from typing import Any

from aipass.prax import logger
from aipass.memory.apps.handlers.json import json_handler

# Resolve paths relative to handler location (same pattern as memory_files.py)
_MEMORY_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _MEMORY_ROOT / "config" / "memory.config.json"

# Safe defaults — returned when config is missing or malformed.
# These match the canonical values in memory.config.json.
_SAFE_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "enforce": False,
    "entry_types": {
        "key_learnings": {
            "file": "local.json",
            "container": "key_learnings",
            "kind": "dict",
            "field": "value",
            "max_chars": 200,
        },
        "sessions": {
            "file": "local.json",
            "container": "sessions",
            "kind": "list",
            "field": "summary",
            "max_chars": 300,
        },
        "todos": {
            "file": "local.json",
            "container": "todos",
            "kind": "list",
            "field": "task",
            "max_chars": 200,
        },
        "observations": {
            "file": "observations.json",
            "container": "observations",
            "kind": "list",
            "field": "note",
            "max_chars": 600,
        },
    },
}


def _deep_merge_entry_types(
    base: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Deep-merge per_branch overrides into entry_types.

    For each key in *overrides*:
      - If the key exists in *base*, shallow-merge the override dict
        into a copy of the base dict (override wins per field).
      - If the key is new, add it verbatim (new entry type for branch).

    Args:
        base: Default entry_types dict.
        overrides: per_branch[branch] dict (same shape as entry_types).

    Returns:
        Merged entry_types dict. The originals are not mutated.
    """
    merged = copy.deepcopy(base)
    for type_name, type_overrides in overrides.items():
        if type_name in merged:
            merged[type_name].update(type_overrides)
        else:
            merged[type_name] = copy.deepcopy(type_overrides)
    return merged


def load_entry_limits(branch: str) -> dict[str, Any]:
    """Load effective entry limits for *branch*.

    Reads memory.config.json, pulls the ``entry_limits`` section, then
    deep-merges any ``per_branch[branch]`` overrides on top of the
    default ``entry_types``.

    Graceful degradation:
      - Missing config file -> safe defaults + warning log.
      - Malformed JSON       -> safe defaults + loud warning log.
      - Missing entry_limits section -> safe defaults + warning log.

    Args:
        branch: Branch name (e.g. "devpulse", "memory").

    Returns:
        Dict with keys: enabled, enforce, entry_types.
    """
    # --- Attempt to read config ------------------------------------------------
    try:
        raw_text = _CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(f"[entry_limits] Config file not found at {_CONFIG_PATH}, returning safe defaults")
        json_handler.log_operation(
            "load_entry_limits",
            {"branch": branch, "fallback": "missing_config"},
            module_name="entry_limits",
        )
        return copy.deepcopy(_SAFE_DEFAULTS)
    except OSError as exc:
        logger.warning(f"[entry_limits] Could not read config at {_CONFIG_PATH}: {exc}, returning safe defaults")
        json_handler.log_operation(
            "load_entry_limits",
            {"branch": branch, "fallback": "read_error"},
            module_name="entry_limits",
        )
        return copy.deepcopy(_SAFE_DEFAULTS)

    # --- Parse JSON ------------------------------------------------------------
    try:
        config = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning(f"[entry_limits] Malformed JSON in {_CONFIG_PATH}: {exc}, returning safe defaults")
        json_handler.log_operation(
            "load_entry_limits",
            {"branch": branch, "fallback": "malformed_json", "error": str(exc)},
            module_name="entry_limits",
        )
        return copy.deepcopy(_SAFE_DEFAULTS)

    # --- Extract entry_limits section ------------------------------------------
    section = config.get("entry_limits")
    if not isinstance(section, dict):
        logger.warning("[entry_limits] No valid 'entry_limits' section in config, returning safe defaults")
        json_handler.log_operation(
            "load_entry_limits",
            {"branch": branch, "fallback": "missing_section"},
            module_name="entry_limits",
        )
        return copy.deepcopy(_SAFE_DEFAULTS)

    # --- Build effective result ------------------------------------------------
    enabled = section.get("enabled", True)
    enforce = section.get("enforce", False)
    base_types = section.get("entry_types", {})

    # Apply per_branch overrides if present
    per_branch = section.get("per_branch", {})
    branch_overrides = per_branch.get(branch, {})

    if branch_overrides:
        effective_types = _deep_merge_entry_types(base_types, branch_overrides)
    else:
        effective_types = copy.deepcopy(base_types)

    result: dict[str, Any] = {
        "enabled": enabled,
        "enforce": enforce,
        "entry_types": effective_types,
    }

    json_handler.log_operation(
        "load_entry_limits",
        {"branch": branch, "types_count": len(effective_types)},
        module_name="entry_limits",
    )

    return result
