# =================== AIPass ====================
# Name: settings_window.py
# Description: PyQt5 settings pop-up for a registered backup project (stub)
# Version: 0.1.0
# Created: 2026-04-16
# Modified: 2026-04-16
# =============================================

"""Settings window handler.

Opens a PyQt5 modal that lets the user tune a project's backup settings
(mode, retention, drive-sync target). PyQt5 is intentionally NOT imported
in this stub — awaiting Phase 3.

Reference pattern: ``/home/patrick/Projects/Speakeasy/apps/handlers/
ui_handler.py`` lines 296-453 (the Speakeasy settings dialog).
"""

from ..json import json_handler


def open_settings_window(project_path: str) -> None:
    """Open the settings pop-up for a backup project.

    Args:
        project_path: Absolute filesystem path to the target project.

    Returns:
        None. The dialog is modal and blocks until dismissed.
        Stub — awaiting Phase 3 (PyQt5 wiring).
    """
    _ = project_path
    json_handler.log_operation("settings_window_opened", {"project_path": project_path, "stub": True})
    return None


# =============================================
