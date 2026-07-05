# =================== AIPass ====================
# Name: log_watcher_service.py
# Description: Persistent log watcher process for Medic error detection
# Version: 1.0.0
# Created: 2026-03-29
# Modified: 2026-03-29
# =============================================

"""
Log Watcher Service — Persistent process for Medic

Starts both branch log watcher and system log watcher,
then blocks until SIGTERM/SIGINT. Designed to run as a
systemd user service (trigger-log-watcher.service).

Usage:
    python -m aipass.trigger.apps.log_watcher_service
    # Or via systemd: systemctl --user start trigger-log-watcher.service
"""

import os
import signal
import sys
import threading

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.trigger.apps.modules.branch_log_events import (
    start as start_branch_watcher,
    stop as stop_branch_watcher,
)
from aipass.trigger.apps.modules.log_events import (
    start as start_system_watcher,
    stop as stop_system_watcher,
)

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream in (sys.stdout, sys.stderr):
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is not None:
            _reconfigure(encoding="utf-8", errors="replace")


def print_introspection():
    """Display module introspection info."""
    try:
        from aipass.cli.apps.modules.display import console
    except ImportError:
        logger.info("CLI console not available, using rich fallback")
        from rich.console import Console

        console = Console()

    console.print()
    console.print("[bold cyan]log_watcher_service Module[/bold cyan]")
    console.print("[dim]Persistent log watcher process — starts branch and system watchers as systemd service[/dim]")
    console.print()


def main() -> None:
    """Start watchers and block until signaled."""
    stop_event = threading.Event()

    def shutdown(signum: int, _frame: object) -> None:
        """Handle SIGTERM/SIGINT gracefully."""
        print(f"[trigger-log-watcher] Received signal {signum}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Start both watchers
    branch_ok = start_branch_watcher()
    system_ok = start_system_watcher()

    if not branch_ok and not system_ok:
        print("[trigger-log-watcher] Both watchers failed to start", file=sys.stderr)
        sys.exit(1)

    started = []
    if branch_ok:
        started.append("branch")
    if system_ok:
        started.append("system")
    print(f"[trigger-log-watcher] Running ({', '.join(started)} watchers active)")

    # Block until shutdown signal
    stop_event.wait()

    # Graceful shutdown
    stop_branch_watcher()
    stop_system_watcher()
    print("[trigger-log-watcher] Stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print("log_watcher_service 1.0.0")
        sys.exit(0)
    main()
