# =================== AIPass ====================
# Name: sync_test_ops.py
# Description: File operations for Drive sync test
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-09
# =============================================

"""
Sync Test File Operations Handler

Handles file system operations for the Drive sync test workflow:
- Creating test directory and test files
- Cleaning up test directory after test completes
"""

import shutil
from pathlib import Path
from datetime import datetime

from aipass.prax import logger


def create_sync_test_files(backup_root: Path) -> dict:
    """Create test directory and test files for Drive sync verification.

    Args:
        backup_root: Root backup directory (e.g., src/aipass/backup/)

    Returns:
        dict with keys:
            - success (bool): Whether files were created
            - test_dir (Path): Path to test directory
            - file_count (int): Number of test files created
            - error (str|None): Error message if failed
    """
    try:
        test_dir = backup_root / "backups" / "_sync_test"
        test_dir.mkdir(parents=True, exist_ok=True)

        test_files = {
            "test_file_1.txt": "Hello from AIPass backup test",
            "test_file_2.json": '{"test": true, "timestamp": "' + datetime.now().isoformat() + '"}',
            "subdir/nested_file.txt": "Nested directory test",
            "subdir/deep/deeper_file.md": "# Deep nested test\nVerifying folder structure",
        }

        for name, content in test_files.items():
            path = test_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        logger.info(f"[sync_test_ops] Created {len(test_files)} test files in {test_dir}")
        return {
            "success": True,
            "test_dir": test_dir,
            "file_count": len(test_files),
            "error": None,
        }
    except Exception as e:
        logger.error(f"[sync_test_ops] Failed to create test files: {e}")
        return {
            "success": False,
            "test_dir": None,
            "file_count": 0,
            "error": str(e),
        }


def cleanup_sync_test_dir(test_dir: Path) -> dict:
    """Remove the sync test directory and all contents.

    Args:
        test_dir: Path to test directory to remove

    Returns:
        dict with keys:
            - success (bool): Whether cleanup succeeded
            - error (str|None): Error message if failed
    """
    try:
        shutil.rmtree(test_dir, ignore_errors=True)
        logger.info(f"[sync_test_ops] Cleaned up test directory: {test_dir}")
        return {"success": True, "error": None}
    except Exception as e:
        logger.error(f"[sync_test_ops] Failed to cleanup test directory: {e}")
        return {"success": False, "error": str(e)}
