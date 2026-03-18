# =================== AIPass ====================
# Name: post_close_runner.py
# Description: Background post-close processing
# Version: 1.2.0
# Created: 2026-02-14
# Modified: 2026-02-14
# =============================================

"""
Post-Close Background Runner

Runs memory bank archival as a background process.
Called by close_plan.py via subprocess.Popen so the close command returns fast.

Uses a lock file to prevent concurrent execution - if another instance is
already running, this one exits silently (the running instance will pick up
all unprocessed plans since it scans ALL of them).

This script lives inside the flow branch so handler import guards allow it.
"""

import os
import sys
from pathlib import Path

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[3]  # file.py → modules/ → apps/ → flow/ → aipass/
FLOW_ROOT = _PKG_ROOT / "flow"

# External: CLI console (Rich display) and Prax logger
from aipass.cli.apps.modules import console, error, warning
from aipass.prax.apps.modules.logger import system_logger as logger

# JSON handler for operation tracking
from aipass.flow.apps.handlers.json import json_handler

MODULE_NAME = "post_close_runner"

LOCK_FILE = FLOW_ROOT / ".post_close_runner.lock"

# AI summarization removed — plans vectorized directly from flow/processed_plans/
# from aipass.flow.apps.handlers.summary.generate import generate_summaries
from aipass.flow.apps.handlers.mbank.process import process_closed_plans


def handle_command(command: str, args: list) -> bool:
    """Handle commands routed by the entry point.

    This module is a background utility runner, not a user-facing command.
    It responds to 'post_close' for drone routing compatibility
    and supports --help / -h for introspection.

    Args:
        command: Command name
        args: Command arguments

    Returns:
        True if command was handled, False otherwise
    """
    if command != "post_close":
        return False

    if not args:
        print_introspection()
        return True

    if args and args[0] in ("--help", "-h"):
        print_help()
        return True

    # Log the operation
    json_handler.log_operation(
        "post_close_processed",
        {"command": command, "args": args}
    )

    # Run the post-close processing directly (foreground)
    if not _acquire_lock():
        warning("Another instance is already running")
        return True

    try:
        process_closed_plans()
        console.print("[green]Processing complete[/green]")
    except Exception as e:
        logger.error(f"[{MODULE_NAME}] Background processing failed: {e}")
        error(f"Processing failed: {e}")
    finally:
        _release_lock()

    return True


def _acquire_lock() -> bool:
    """Try to acquire lock file. Returns True if acquired, False if another instance is running."""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)  # Signal 0 = check if process exists
            logger.info(f"[{MODULE_NAME}] Another instance running (PID {pid}), exiting")
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            logger.info(f"[{MODULE_NAME}] Stale lock found, taking over")

    LOCK_FILE.write_text(str(os.getpid()))
    return True


def _release_lock():
    """Release the lock file."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"[{MODULE_NAME}] Failed to release lock file: {e}")


def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("post_close_runner Module")
    console.print("Background post-close processing — runs memory bank archival")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/mbank/")
    console.print("    - process.py (process_closed_plans — scan and archive closed plans)")
    console.print()


def print_help():
    """Display help for this background runner."""
    console.print(f"Usage: python {Path(__file__).name}")
    console.print()
    console.print("Post-Close Background Runner")
    console.print("Runs memory bank archival as a background process.")
    console.print("Called by close_plan.py via subprocess — not intended for direct use.")
    console.print()
    console.print("Options:")
    console.print("  -h, --help    Show this help message")


if __name__ == "__main__":
    if '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0)

    if not _acquire_lock():
        sys.exit(0)

    try:
        # generate_summaries() — removed, AI summarization no longer needed
        process_closed_plans()
    except Exception as e:
        logger.error(f"[{MODULE_NAME}] Background processing failed: {e}")
    finally:
        _release_lock()
