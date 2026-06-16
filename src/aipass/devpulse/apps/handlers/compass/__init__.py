# =================== AIPass ====================
# Name: __init__.py
# Description: Compass handler package — devpulse-owned rated decision store
# Version: 1.0.0
# Created: 2026-06-16
# Modified: 2026-06-16
# =============================================

"""Compass — devpulse-owned, SQLite/FTS5-backed rated decision store.

P1 ships the storage core only (``store.py``). The drone command, slash
command, and maintenance wiring arrive in later phases (see DPLAN-0212).

The package is the public entry point: the storage API is re-exported here so
callers (later-phase commands, tests) depend on ``compass`` rather than
reaching into the ``store`` submodule directly.
"""

from aipass.devpulse.apps.handlers.compass.store import (
    DEFAULT_DB_PATH,
    VALID_RATINGS,
    VALID_SOURCES,
    VALID_STATUSES,
    add_decision,
    archive,
    query_decisions,
    rate,
    review,
    stats,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "VALID_RATINGS",
    "VALID_SOURCES",
    "VALID_STATUSES",
    "add_decision",
    "archive",
    "query_decisions",
    "rate",
    "review",
    "stats",
]
