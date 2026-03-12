# =================== AIPass ====================
# Name: wakeup_ops.py
# Description: Wake-Up Cron Operations Module
# Version: 2.0.0
# Created: 2026-03-08
# Modified: 2026-03-10
# =============================================

"""
Wake-up operations module -- facade for cron entry point.

Provides a clean module-layer interface over handler functions
used by daemon_wakeup.py. Telegram stripped — notification stubs
remain for import compatibility.
"""

from aipass.prax import logger

try:
    from aipass.cli.apps.modules.display import console
except ImportError:
    from rich.console import Console
    console = Console()

# =============================================
# NOTIFICATION STUBS (Telegram stripped)
# =============================================

from aipass.daemon.apps.handlers.schedule.assistant_notifier import (
    notify_wakeup,
    notify_report,
    notify_error,
)


# =============================================
# INTROSPECTION
# =============================================

def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("wakeup_ops Module")
    console.print("Facade for daemon_wakeup.py — notification stubs (Telegram stripped)")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/schedule/")
    console.print("    - assistant_notifier.py (notification stubs — Telegram stripped)")
    console.print()


# =============================================
# DRONE ROUTING
# =============================================

def handle_command(command: str, args: list) -> bool:
    """Handle commands routed by the entry point."""
    if command == "wakeup-ops":
        console.print()
        console.print("[bold cyan]Wakeup Ops[/bold cyan] - Cron wake-up facade")
        console.print()
        console.print("  [dim]Notifications:[/dim] stubs (Telegram stripped)")
        console.print()
        console.print("[dim]This module is a facade used by daemon_wakeup.py.[/dim]")
        console.print()
        return True
    return False
