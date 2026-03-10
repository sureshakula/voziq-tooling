# =================== AIPass ====================
# Name: wakeup_ops.py
# Description: Wake-Up Cron Operations Module
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Wake-up operations module -- facade for cron entry point.

Provides a clean module-layer interface over handler functions
used by daemon_wakeup.py. Entry-level scripts import from
this module instead of reaching into handlers directly.
"""

from aipass.prax import logger

try:
    from aipass.cli.apps.modules.display import console
except ImportError:
    from rich.console import Console
    console = Console()

# =============================================
# DAEMON BOT TELEGRAM NOTIFICATIONS
# =============================================

try:
    from aipass.daemon.apps.handlers.schedule.assistant_notifier import (
        notify_wakeup,
        notify_report,
        notify_error,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    notify_wakeup = None
    notify_report = None
    notify_error = None


# =============================================
# INTROSPECTION
# =============================================

def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("wakeup_ops Module")
    console.print("Facade for daemon_wakeup.py — re-exports daemon bot Telegram notifications")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/schedule/")
    console.print("    - assistant_notifier.py (notify_wakeup, notify_report, notify_error — daemon bot Telegram notifications)")
    console.print()


# =============================================
# DRONE ROUTING
# =============================================

def handle_command(command: str, args: list) -> bool:
    """Handle commands routed by the entry point.

    Args:
        command: Command name
        args: Additional arguments

    Returns:
        True if command was handled, False otherwise
    """
    if command == "wakeup-ops":
        from aipass.cli.apps.modules import console

        console.print()
        console.print("[bold cyan]Wakeup Ops[/bold cyan] - Cron wake-up facade")
        console.print()
        console.print(f"  [dim]Telegram available:[/dim] {TELEGRAM_AVAILABLE}")
        console.print()
        console.print("[dim]This module is a facade used by daemon_wakeup.py.[/dim]")
        console.print()
        return True
    return False
