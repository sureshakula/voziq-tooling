# =================== AIPass ====================
# Name: governance.py
# Description: Surfacing governance module — public API
# Version: 1.0.0
# Created: 2026-07-16
# Modified: 2026-07-16
# =============================================

"""
Surfacing Governance Module — Public API

Pure decision functions for controlling when recalled items (compass
rulings, plans, fragments) should be surfaced to the user. Retrieval-
backend-agnostic: works with any store that produces an item_id and
a relevance_score.

All functions are PURE — state dict in, decision + updated state out.
The caller owns persistence (file, JSONL, in-memory).

Public API:
    should_surface(item_id, relevance_score, state, config)
        -> (bool, reason, updated_state)
    record_message(state) -> updated_state
    new_state() -> state dict
"""

import os
import sys
from typing import Any, Dict, Tuple

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream in (sys.stdout, sys.stderr):
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is not None:
            _reconfigure(encoding="utf-8", errors="replace")

from aipass.memory.apps.handlers.json import json_handler


# =============================================================================
# CONSTANTS — default config values
# =============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "threshold": 0.3,
    "max_surfaces_per_session": 5,
    "min_messages_between": 10,
    "cooldown_seconds": 300,
}


# =============================================================================
# STATE FACTORY
# =============================================================================


def new_state() -> Dict[str, Any]:
    """
    Create a fresh governance state dict.

    Returns:
        State dict with zeroed counters and empty surfaced set.
    """
    return {
        "surfaces_count": 0,
        "messages_since_last": 0,
        "last_surface_time": 0.0,
        "surfaced_ids": [],
    }


# =============================================================================
# CORE GOVERNANCE
# =============================================================================


def should_surface(
    item_id: str,
    relevance_score: float,
    state: Dict[str, Any],
    config: Dict[str, Any] | None = None,
    *,
    current_time: float | None = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Decide whether an item should be surfaced, given current state.

    Pure function — does not mutate the input state dict. Returns an
    updated copy reflecting the decision (surfaced id recorded, counters
    bumped) only when the answer is True; otherwise returns state unchanged.

    Args:
        item_id: Unique identifier of the item to surface.
        relevance_score: Float score from the retrieval backend (0-1).
        state: Current governance state (from new_state() or prior call).
        config: Override config; merged with DEFAULT_CONFIG for missing keys.
        current_time: Epoch seconds for cooldown check. Injected for testability;
            falls back to time.time() in production.

    Returns:
        (should_surface, reason, updated_state)
    """
    import time

    cfg = {**DEFAULT_CONFIG, **(config or {})}
    now = current_time if current_time is not None else time.time()

    if not cfg.get("enabled", True):
        return False, "Surfacing disabled", state

    threshold = cfg.get("threshold", 0.3)
    if relevance_score < threshold:
        return False, f"Below threshold ({relevance_score:.2f} < {threshold})", state

    max_surfaces = cfg.get("max_surfaces_per_session", 5)
    if state.get("surfaces_count", 0) >= max_surfaces:
        return False, f"Session budget exhausted ({max_surfaces}/{max_surfaces})", state

    min_messages = cfg.get("min_messages_between", 10)
    messages_since = state.get("messages_since_last", 0)
    last_time = state.get("last_surface_time", 0.0)
    if last_time > 0 and messages_since < min_messages:
        return False, f"Spacing not met ({messages_since}/{min_messages} messages)", state

    cooldown = cfg.get("cooldown_seconds", 300)
    elapsed = now - last_time
    if last_time > 0 and elapsed < cooldown:
        remaining = int(cooldown - elapsed)
        return False, f"Cooldown active ({remaining}s remaining)", state

    surfaced_ids = state.get("surfaced_ids", [])
    if item_id in surfaced_ids:
        return False, "Already surfaced this session", state

    updated = {
        "surfaces_count": state.get("surfaces_count", 0) + 1,
        "messages_since_last": 0,
        "last_surface_time": now,
        "surfaced_ids": list(surfaced_ids) + [item_id],
    }
    json_handler.log_operation(
        "governance_surface",
        {"item_id": item_id, "relevance_score": relevance_score, "surfaces_count": updated["surfaces_count"]},
    )
    return True, "Ready to surface", updated


# =============================================================================
# MESSAGE TRACKING
# =============================================================================


def record_message(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record that a message was processed. Pure — returns updated state.

    Args:
        state: Current governance state.

    Returns:
        New state dict with messages_since_last incremented.
    """
    return {
        **state,
        "messages_since_last": state.get("messages_since_last", 0) + 1,
    }


# =============================================================================
# MODULE ROUTING (handle_command for drone auto-discovery)
# =============================================================================


def print_introspection() -> None:
    """Display module introspection (seedgo standard)."""
    from aipass.cli.apps.modules import console

    console.print()
    console.print("[bold cyan]governance Module[/bold cyan]")
    console.print("Pure surfacing governance — state-in/state-out decision functions")
    console.print()
    console.print("[yellow]Public API:[/yellow]")
    console.print("  should_surface(item_id, relevance_score, state, config)")
    console.print("  record_message(state)")
    console.print("  new_state()")
    console.print()
    console.print("[dim]Library module — import from: aipass.memory.apps.modules.governance[/dim]")


def handle_command(command: str, args: list) -> bool:
    """Entry point for drone module discovery — governance has no CLI surface."""
    if command != "governance":
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ("--help", "-h", "help"):
        print_introspection()
        return True

    from aipass.cli.apps.modules import warning

    warning(f"governance: unknown subcommand '{args[0]}'")
    print_introspection()
    return True
