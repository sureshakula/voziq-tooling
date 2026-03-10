# =================== AIPass ====================
# Name: integration_ops.py
# Description: Backup Integration Operations Handler
# Version: 1.0.0
# Created: 2026-02-20
# Modified: 2026-03-09
# =============================================

"""
Backup Integration Operations Handler

Implementation logic for external integrations:
- Google Drive sync operations
- Backup directory read-only protection

Called by the integrations module orchestrator.
"""

import os
import stat
from pathlib import Path
from typing import Any, Optional


def sync_to_drive(
    backup_path: Path,
    source_dir: Path,
    mode: str,
    backup_note: str,
    drive_sync_module: Any,
    drive_sync_available: bool,
) -> bool:
    """Sync versioned backups to Google Drive.

    Args:
        backup_path: Path to backup directory to sync
        source_dir: Source directory being backed up (for project name)
        mode: Backup mode ('snapshot' or 'versioned')
        backup_note: Optional note describing the backup
        drive_sync_module: The GoogleDriveSync class (injected)
        drive_sync_available: Whether google_drive_sync is importable

    Returns:
        bool: True if sync succeeded, False otherwise
    """
    if not drive_sync_available or drive_sync_module is None:
        return False

    if mode != 'versioned':
        return False

    try:
        project_name = "AIPass"
        drive_sync = drive_sync_module()

        if not drive_sync.authenticate():
            return False

        result = drive_sync.sync_backup_files(
            backup_dir=backup_path,
            project_name=project_name,
            note=backup_note
        )
        return result["success"] if isinstance(result, dict) else result

    except Exception:
        return False


def set_backup_readonly(backup_path: Path) -> tuple[bool, str]:
    """Set backup directory to read-only for protection.

    Applies read-only permissions recursively to all directories and files.

    Args:
        backup_path: Path to backup directory to protect

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not backup_path.exists():
        return False, f"Backup path does not exist: {backup_path}"

    try:
        protected_dirs = 0
        protected_files = 0

        for root, dirs, files in os.walk(str(backup_path)):
            try:
                os.chmod(root, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH |
                              stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                protected_dirs += 1
            except Exception:
                pass

            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.chmod(file_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                    protected_files += 1
                except Exception:
                    pass

        return True, f"Protected {protected_dirs} dirs, {protected_files} files"

    except Exception as e:
        return False, f"Could not set read-only protection: {e}"
