# =================== AIPass ====================
# Name: snapshot.py
# Description: Snapshot module — full-copy backup of a project
# Version: 2.0.0
# Created: 2026-04-17
# Modified: 2026-06-12
# =============================================

"""Snapshot Module — full mirror backup of a project directory."""

import os
import sys
import time

from aipass.prax import logger
from aipass.cli.apps.modules import console

from aipass.backup.apps.handlers.copy.snapshot import copy_snapshot
from aipass.backup.apps.handlers.ignore.patterns import load_patterns
from aipass.backup.apps.handlers.ignore.whitelist import load_whitelist
from aipass.backup.apps.handlers.json import json_handler
from aipass.backup.apps.handlers.path.builder import build_snapshot_path
from aipass.backup.apps.handlers.project.config import load_project_config
from aipass.backup.apps.handlers.project.setup import create_backup_dir
from aipass.backup.apps.handlers.report.result import BackupResult
from aipass.backup.apps.handlers.scan.filter import filter_paths
from aipass.backup.apps.handlers.scan.walk import walk_project
from aipass.backup.apps.handlers.state.changelog import append_changelog
from aipass.backup.apps.handlers.state.metadata import build_metadata
from aipass.backup.apps.handlers.state.timestamps import save_timestamps
from aipass.backup.apps.modules.display import (
    build_progress_bar,
    show_backups_now,
    show_last_backups,
    show_result_summary,
    show_run_header,
)

MODULE_NAME = "snapshot"
PRIMARY_COMMAND = "snapshot"


def print_introspection():
    """Display module info and connected handlers."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print(f"  Primary command: [yellow]{PRIMARY_COMMAND}[/yellow]")
    console.print("  Status: Phase 3 — implemented")
    console.print("  Handlers: scan, copy/snapshot, state, ignore, path, report")


def print_help():
    """Display help for this module."""
    print_introspection()


def run_snapshot(project_root: str, show_panels: bool = True) -> BackupResult:
    """Run a full snapshot backup for a project."""
    start = time.time()

    if show_panels:
        show_last_backups()

    create_backup_dir(project_root)
    config = load_project_config(project_root)

    patterns = load_patterns(project_root)
    whitelist_entries = load_whitelist(project_root)
    max_size = config.get("max_file_size_mb", 100)

    all_files = list(walk_project(project_root))
    filtered = filter_paths(all_files, patterns, whitelist_entries, max_size)

    dest = str(build_snapshot_path(project_root))

    result = BackupResult(
        mode="snapshot",
        project_root=project_root,
        files_checked=len(filtered),
        backup_path=dest,
    )

    if show_panels:
        show_run_header(result)

    progress = build_progress_bar()
    with progress:
        task = progress.add_task("Processing files...", total=len(filtered))
        copy_result = copy_snapshot(filtered, dest, project_root, on_progress=lambda: progress.advance(task))

    console.print(f"Processing completed: {len(filtered)}/{len(filtered)} files checked")

    duration = time.time() - start

    timestamps = {rel: os.path.getmtime(abs_p) for abs_p, rel in filtered}
    save_timestamps(project_root, timestamps)

    result.files_copied = copy_result.get("files_copied", 0)
    result.files_skipped = result.files_checked - result.files_copied
    result.bytes_copied = copy_result.get("bytes_copied", 0)
    result.duration_seconds = duration
    result.errors = copy_result.get("errors", [])

    metadata = build_metadata(result)
    append_changelog(project_root, metadata)

    json_handler.log_operation(
        "snapshot_complete",
        {"project_root": project_root, "files": result.files_copied},
    )
    logger.info(f"[backup] Snapshot complete: {result.files_copied} files")

    if show_panels:
        show_result_summary(result)
        if not result.errors:
            show_backups_now("snapshot")

    return result


def handle_command(command: str, args: list) -> bool:
    """Handle the snapshot command. Returns True if handled."""
    if command != PRIMARY_COMMAND:
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ("--help", "-h", "help"):
        print_introspection()
        return True

    project_root = args[0]
    run_snapshot(project_root)
    return True


# =============================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_introspection()
        sys.exit(0)
    handle_command(PRIMARY_COMMAND, sys.argv[1:])
