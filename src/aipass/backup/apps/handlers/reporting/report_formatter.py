# =================== AIPass ====================
# Name: report_formatter.py
# Description: Backup result reporting
# Version: 1.1.0
# Created: 2025-11-23
# Modified: 2026-03-09
# =============================================

"""
Report Formatter - Backup result formatting and display

Formats and displays backup operation results, statistics, errors, and warnings.
"""

# =============================================
# IMPORTS
# =============================================

import datetime
from pathlib import Path

from aipass.prax import logger
from aipass.backup.apps.handlers.models.backup_models import BackupResult

# logger imported from aipass.prax

def _header(text):
    logger.info(f"{'='*70}")
    logger.info(f"  {text}")
    logger.info(f"{'='*70}")

# =============================================
# REPORT FORMATTING OPERATIONS
# =============================================

def display_backup_results(result: BackupResult, mode_config: dict, backup_path: Path,
                           skipped_items: dict, filter_tracked_items_func, dry_run: bool = False) -> None:
    """Display comprehensive backup results with statistics and errors.

    Args:
        result: BackupResult with operation statistics
        mode_config: Mode configuration dict
        backup_path: Backup destination path
        skipped_items: Dict of skipped directories and files
        filter_tracked_items_func: Function to filter tracked items
        dry_run: If True, show "would be" language in statistics
    """
    duration = datetime.datetime.now() - result.start_time

    # Determine overall result status
    if result.critical_errors:
        status_icon = "!"
        status_text = "FAILED"
    elif result.errors > 0:
        status_icon = "X"
        status_text = "COMPLETED WITH ERRORS"
    elif result.warnings:
        status_icon = "!"
        status_text = "COMPLETED WITH WARNINGS"
    else:
        status_icon = "OK"
        status_text = "COMPLETED SUCCESSFULLY"

    # Use _header for main status
    _header(f"{status_icon} {mode_config['name'].upper()} {status_text}")

    # Statistics Section
    logger.info("STATISTICS:")
    logger.info(f"  Files checked: {result.files_checked}")

    if dry_run:
        # Dry-run mode: show "would be" language
        logger.info(f"  Would copy:    {result.files_copied} files")
        logger.info(f"  Would skip:    {result.files_skipped} files (unchanged)")
        if result.files_deleted > 0:
            logger.warning(f"  Would delete:  {result.files_deleted} files")
    else:
        # Normal mode: show actual actions
        logger.info(f"  Files copied:  {result.files_copied}")
        if result.mode == 'versioned' and result.files_added > 0:
            logger.info(f"  Files added:   {result.files_added} (new)")
        logger.info(f"  Files skipped: {result.files_skipped}")
        if result.mode == 'versioned' and result.files_deleted == 0:
            logger.info(f"  Files deleted: {result.files_deleted} (cleanup disabled - keeps history)")
        else:
            logger.info(f"  Files deleted: {result.files_deleted}")

    logger.info(f"  Errors:        {result.errors}")
    logger.info(f"  Warnings:      {len(result.warnings)}")
    logger.info(f"  Duration:      {duration.total_seconds():.2f}s")
    logger.info(f"  Location:      {backup_path}")

    # Display detailed error information
    if result.critical_errors:
        logger.error(f"CRITICAL ERRORS ({len(result.critical_errors)}):")
        logger.info("-" * 40)
        for i, error in enumerate(result.critical_errors, 1):
            logger.error(f"  {i}. {error}")
        logger.info("RECOVERY SUGGESTIONS:")
        logger.info("  - Check disk space and permissions")
        logger.info("  - Ensure backup destination is accessible")
        logger.info("  - Try running as administrator if permission issues")
        logger.info("  - Check if antivirus is blocking file operations")

    elif result.error_details:
        logger.error(f"ERRORS ({len(result.error_details)}):")
        logger.info("-" * 40)
        for i, error in enumerate(result.error_details[:10], 1):
            logger.error(f"  {i}. {error}")
        if len(result.error_details) > 10:
            logger.info(f"  ... and {len(result.error_details) - 10} more errors")
        logger.info("SUGGESTIONS:")
        logger.info("  - Some files may be in use - try closing applications")
        logger.info("  - Check file permissions on failed files")

    if result.warnings:
        logger.warning(f"WARNINGS ({len(result.warnings)}):")
        logger.info("-" * 40)
        for i, warning in enumerate(result.warnings[:5], 1):
            logger.warning(f"  {i}. {warning}")
        if len(result.warnings) > 5:
            logger.info(f"  ... and {len(result.warnings) - 5} more warnings")

    # Display project-specific skipped items
    tracked_items = filter_tracked_items_func(skipped_items)
    total_tracked = len(tracked_items["directories"]) + len(tracked_items["files"])
    total_all_skipped = len(skipped_items["directories"]) + len(skipped_items["files"])

    if total_tracked > 0:
        logger.info(f"NOTABLE SKIPPED ITEMS ({total_tracked}):")
        logger.info(f"Total ignored: {total_all_skipped}")
        logger.info("-" * 50)

        if tracked_items["directories"]:
            logger.info(f"Directories ({len(tracked_items['directories'])}):")
            for i, dir_path in enumerate(sorted(tracked_items["directories"]), 1):
                logger.info(f"  {i}. {dir_path}/")

        if tracked_items["files"]:
            logger.info(f"Files ({len(tracked_items['files'])}):")
            for i, file_path in enumerate(sorted(tracked_items["files"]), 1):
                logger.info(f"  {i}. {file_path}")
    else:
        if total_all_skipped > 0:
            logger.info(f"No project-specific items skipped ({total_all_skipped} common items filtered)")
        else:
            logger.info("No items were skipped.")


# =============================================
# MODULE INITIALIZATION
# =============================================

# Pure handler - no initialization needed
