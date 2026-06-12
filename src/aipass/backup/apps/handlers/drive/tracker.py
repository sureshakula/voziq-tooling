# =================== AIPass ====================
# Name: tracker.py
# Description: Drive upload tracker — persisted file-id map (stub)
# Version: 0.1.0
# Created: 2026-04-16
# Modified: 2026-04-16
# =============================================

"""Drive upload tracker.

Maintains a persistent mapping of local paths to Drive file IDs so repeat
uploads can update existing resources rather than create duplicates. Full
implementation awaiting Phase 3.
"""

from ..json import json_handler


def load_tracker() -> dict:
    """Load the uploaded-file tracker.

    Returns:
        Mapping of local path to Drive file id. Stub returns an empty
        dict awaiting Phase 3.
    """
    json_handler.log_operation("load_tracker", {"stub": True})
    return {}


def record_upload(tracker: dict, path: str, file_id: str) -> None:
    """Record an upload in the tracker.

    Args:
        tracker: Tracker dict (mutated in place).
        path: Absolute local path that was uploaded.
        file_id: Drive file id assigned to the uploaded resource.
    """
    _ = (tracker, path, file_id)
    json_handler.log_operation(
        "record_upload",
        {"path": path, "file_id": file_id, "stub": True},
    )


def clear_tracker() -> None:
    """Reset the tracker back to an empty state. Stub — awaiting Phase 3."""
    json_handler.log_operation("clear_tracker", {"stub": True})


# =============================================
