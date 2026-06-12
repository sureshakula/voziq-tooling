# =================== AIPass ====================
# Name: snapshot.py
# Description: Snapshot module — full-copy backup of a project
# Version: 1.0.0
# Created: 2026-04-17
# Modified: 2026-04-23
# =============================================

"""Snapshot Module — full mirror backup of a project directory."""

import os
import sys
import time

from aipass.prax import logger
from aipass.cli.apps.modules import console

from apps.handlers.copy.snapshot import copy_snapshot
from apps.handlers.ignore.patterns import load_patterns
from apps.handlers.ignore.whitelist import load_whitelist
from apps.handlers.json import json_handler
from apps.handlers.path.builder import build_snapshot_path
from apps.handlers.project.config import load_project_config
from apps.handlers.project.setup import create_backup_dir
from apps.handlers.report.formatter import format_result
from apps.handlers.report.result import BackupResult
from apps.handlers.scan.filter import filter_paths
from apps.handlers.scan.walk import walk_project
from apps.handlers.state.changelog import append_changelog
from apps.handlers.state.metadata import build_metadata
from apps.handlers.state.timestamps import save_timestamps

MODULE_NAME = "snapshot"
PRIMARY_COMMAND = "snapshot"


def print_introspection():
    """Display module info and connected handlers."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print(f"  Primary command: [yellow]{PRIMARY_COMMAND}[/yellow]")
    console.print("  Status: Phase 3 — implemented")
    console.print("  Handlers: scan, copy/snapshot, state, ignore, path, report")


def run_snapshot(project_root: str) -> BackupResult:
    """Run a full snapshot backup for a project."""
    start = time.time()

    create_backup_dir(project_root)
    config = load_project_config(project_root)

    patterns = load_patterns(project_root)
    whitelist_entries = load_whitelist(project_root)
    max_size = config.get("max_file_size_mb", 100)

    all_files = list(walk_project(project_root))
    filtered = filter_paths(all_files, patterns, whitelist_entries, max_size)

    dest = str(build_snapshot_path(project_root))
    copy_result = copy_snapshot(filtered, dest, project_root)

    duration = time.time() - start

    timestamps = {rel: os.path.getmtime(abs_p) for abs_p, rel in filtered}
    save_timestamps(project_root, timestamps)

    result = BackupResult(
        mode="snapshot",
        project_root=project_root,
        files_copied=copy_result.get("files_copied", 0),
        bytes_copied=copy_result.get("bytes_copied", 0),
        duration_seconds=duration,
        errors=copy_result.get("errors", []),
    )

    metadata = build_metadata(result)
    append_changelog(project_root, metadata)

    json_handler.log_operation(
        "snapshot_complete",
        {"project_root": project_root, "files": result.files_copied},
    )
    logger.info(f"[backup] Snapshot complete: {result.files_copied} files")
    return result


def handle_command(command: str, args: list) -> bool:
    """Handle the snapshot command. Returns True if handled."""
    if command != PRIMARY_COMMAND:
        return False

    if not args:
        print_introspection()
        return True

    project_root = args[0]
    result = run_snapshot(project_root)
    console.print(format_result(result))
    return True


# =============================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_introspection()
        sys.exit(0)
    handle_command(PRIMARY_COMMAND, sys.argv[1:])
