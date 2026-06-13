# =================== AIPass ====================
# Name: entry_limits.py
# Description: Entry limits config reader, validator, and diff helper for memory files
# Version: 1.2.0
# Created: 2026-06-13
# Modified: 2026-06-13
# =============================================

"""
Entry Limits Validator & Diff Helper

Delegates config reading to ``config_loader`` and returns the effective
limits for a given branch, with per_branch overrides deep-merged over
the default entry_types.

Provides ``check_entry()`` — a pure validator that checks whether a
single entry text exceeds its character cap.

Provides ``changed_entries()`` — a pure diff helper that compares
before/after file dicts and returns only NEW or CHANGED entries that
exceed their character cap.  Unchanged legacy over-limit entries pass
untouched (rollover-safe).

Usage:
    from aipass.memory.apps.handlers.json.entry_limits import (
        load_entry_limits, check_entry, changed_entries,
    )

    limits = load_entry_limits("devpulse")
    verdict = check_entry("key_learnings", some_text, limits)
    # => {"ok": True/False, "length": int, "cap": int, "over_by": int, "entry_type": str}

    violations = changed_entries(before_dict, after_dict, limits)
    # => [{"entry_type", "container", "key", "length", "cap", "over_by"}, ...]
"""

import copy
from pathlib import Path
from typing import Any

from aipass.prax import logger
from aipass.memory.apps.handlers.json import json_handler
from aipass.memory.apps.handlers.json import config_loader

# Resolve paths relative to handler location (same pattern as memory_files.py)
_MEMORY_ROOT = Path(__file__).resolve().parents[3]


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

    Delegates config reading to ``config_loader``, pulls the
    ``entry_limits`` section, then deep-merges any
    ``per_branch[branch]`` overrides on top of the default
    ``entry_types``.

    Args:
        branch: Branch name (e.g. "devpulse", "memory").

    Returns:
        Dict with keys: enabled, enforce, entry_types.
    """
    cfg = config_loader.load()
    section = cfg.get("entry_limits")
    if not isinstance(section, dict):
        logger.warning("[entry_limits] No valid 'entry_limits' section in config, returning safe defaults")
        json_handler.log_operation(
            "load_entry_limits",
            {"branch": branch, "fallback": "missing_section"},
            module_name="entry_limits",
        )
        section = config_loader.DEFAULT_CONFIG["entry_limits"]

    enabled = section.get("enabled", True)
    enforce = section.get("enforce", False)
    base_types = section.get("entry_types", {})

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


# ---------------------------------------------------------------------------
# Phase 2: pure entry validator
# ---------------------------------------------------------------------------


def check_entry(entry_type: str, text: str, limits: dict[str, Any]) -> dict[str, Any]:
    """Check whether *text* exceeds the character cap for *entry_type*.

    This is a **pure function** — no I/O, no file reads, no side effects
    (except a debug log when *entry_type* is unknown).

    Args:
        entry_type: Name of the entry type (e.g. ``"key_learnings"``).
        text: The entry text to measure.
        limits: The dict returned by :func:`load_entry_limits`.

    Returns:
        Verdict dict::

            {
                "ok": bool,        # True when within cap (length <= cap)
                "length": int,     # len(text) — characters, not bytes
                "cap": int,        # max_chars for this type (0 if unknown)
                "over_by": int,    # max(0, length - cap)
                "entry_type": str, # echo back the entry_type
            }
    """
    entry_types = limits.get("entry_types", {})
    type_def = entry_types.get(entry_type)

    length = len(text)

    if type_def is None:
        logger.info(f"[entry_limits] Unknown entry_type '{entry_type}' — no cap applied")
        return {
            "ok": True,
            "length": length,
            "cap": 0,
            "over_by": 0,
            "entry_type": entry_type,
        }

    cap = type_def.get("max_chars", 0)
    over_by = max(0, length - cap)

    return {
        "ok": length <= cap,
        "length": length,
        "cap": cap,
        "over_by": over_by,
        "entry_type": entry_type,
    }


# ---------------------------------------------------------------------------
# Phase 3: changed-entries diff helper (rollover-safe)
# ---------------------------------------------------------------------------


def _extract_text(value: Any, field: str) -> str:
    """Extract the text payload from a container entry.

    For dict containers the value may be a plain string or a dict
    with a *field* key (e.g. ``{"value": "some text", ...}``).
    For list containers the entry is always a dict with a *field* key.

    Args:
        value: The entry value (string or dict).
        field: The field name to extract from a dict value.

    Returns:
        The text string, or ``""`` if extraction fails.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get(field, "")
        return text if isinstance(text, str) else ""
    return ""


def _check_dict_container(
    type_name: str,
    container: str,
    field: str,
    before_container: Any,
    after_container: Any,
    limits: dict[str, Any],
) -> list[dict[str, Any]]:
    """Check dict-shaped container for new/changed over-limit entries.

    Args:
        type_name: Entry type name (e.g. ``"key_learnings"``).
        container: Container key in the file dict.
        field: Field to extract text from dict-valued entries.
        before_container: The container value from the on-disk file.
        after_container: The container value from the proposed file.
        limits: The dict returned by :func:`load_entry_limits`.

    Returns:
        List of violation dicts for new/changed entries that exceed cap.
    """
    if not isinstance(after_container, dict):
        return []
    before_dict = before_container if isinstance(before_container, dict) else {}
    hits: list[dict[str, Any]] = []

    for key, after_value in after_container.items():
        after_text = _extract_text(after_value, field)
        if key in before_dict and after_text == _extract_text(before_dict[key], field):
            continue  # Unchanged — skip even if over-limit
        verdict = check_entry(type_name, after_text, limits)
        if not verdict["ok"]:
            hits.append(
                {
                    "entry_type": type_name,
                    "container": container,
                    "key": key,
                    "length": verdict["length"],
                    "cap": verdict["cap"],
                    "over_by": verdict["over_by"],
                }
            )
    return hits


def _check_list_container(
    type_name: str,
    container: str,
    field: str,
    before_container: Any,
    after_container: Any,
    limits: dict[str, Any],
) -> list[dict[str, Any]]:
    """Check list-shaped container for new/changed over-limit entries.

    Args:
        type_name: Entry type name (e.g. ``"sessions"``).
        container: Container key in the file dict.
        field: Field to extract text from list-item dicts.
        before_container: The container value from the on-disk file.
        after_container: The container value from the proposed file.
        limits: The dict returned by :func:`load_entry_limits`.

    Returns:
        List of violation dicts for new/changed entries that exceed cap.
    """
    if not isinstance(after_container, list):
        return []
    before_list = before_container if isinstance(before_container, list) else []
    hits: list[dict[str, Any]] = []

    for idx, after_item in enumerate(after_container):
        after_text = _extract_text(after_item, field)
        if idx < len(before_list) and after_text == _extract_text(before_list[idx], field):
            continue  # Unchanged — skip even if over-limit
        verdict = check_entry(type_name, after_text, limits)
        if not verdict["ok"]:
            hits.append(
                {
                    "entry_type": type_name,
                    "container": container,
                    "key": str(idx),
                    "length": verdict["length"],
                    "cap": verdict["cap"],
                    "over_by": verdict["over_by"],
                }
            )
    return hits


def changed_entries(
    before: dict[str, Any],
    after: dict[str, Any],
    limits: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return over-limit entries that are NEW or CHANGED between *before* and *after*.

    This is a **pure function** — no I/O, no file reads, no side effects.
    Unchanged entries (even if over-limit) are intentionally skipped so
    that rollover and other maintenance writes are never blocked by
    legacy fat entries.

    Args:
        before: Parsed .trinity file dict (current on-disk content).
        after:  Parsed .trinity file dict (proposed new content).
        limits: The dict returned by :func:`load_entry_limits`.

    Returns:
        List of violation dicts, each containing::

            {
                "entry_type": str,   # e.g. "key_learnings"
                "container": str,    # e.g. "key_learnings"
                "key": str,          # dict key or list index (as str)
                "length": int,       # len(text)
                "cap": int,          # max_chars
                "over_by": int,      # length - cap
            }

        Empty list when everything is within limits or unchanged.
    """
    entry_types = limits.get("entry_types", {})
    violations: list[dict[str, Any]] = []

    for type_name, type_def in entry_types.items():
        container = type_def.get("container", "")
        kind = type_def.get("kind", "dict")
        field = type_def.get("field", "value")

        after_container = after.get(container)
        if after_container is None:
            continue

        before_container = before.get(container)

        if kind == "dict":
            violations.extend(
                _check_dict_container(type_name, container, field, before_container, after_container, limits)
            )
        elif kind == "list":
            violations.extend(
                _check_list_container(type_name, container, field, before_container, after_container, limits)
            )

    return violations
