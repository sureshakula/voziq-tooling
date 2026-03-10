# =================== AIPass ====================
# Name: scheduler_ops.py
# Description: Scheduler Cron Operations Module
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Scheduler operations module -- facade for cron entry point.

Provides a clean module-layer interface over handler functions
used by scheduler_cron.py. Entry-level scripts import from
this module instead of reaching into handlers directly.
"""

from aipass.prax import logger

try:
    from aipass.cli.apps.modules.display import console
except ImportError:
    from rich.console import Console
    console = Console()

# =============================================
# TELEGRAM NOTIFICATIONS
# =============================================

try:
    from aipass.daemon.apps.handlers.schedule.telegram_notifier import (
        notify_triggered,
        notify_complete,
        notify_error,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    notify_triggered = None
    notify_complete = None
    notify_error = None

# =============================================
# TASK REGISTRY
# =============================================

try:
    from aipass.daemon.apps.handlers.schedule.task_registry import (
        get_due_tasks,
        mark_dispatching,
        mark_completed,
        mark_pending,
        recover_stale_dispatches,
    )
    TASK_REGISTRY_AVAILABLE = True
except ImportError:
    TASK_REGISTRY_AVAILABLE = False
    get_due_tasks = None
    mark_dispatching = None
    mark_completed = None
    mark_pending = None
    recover_stale_dispatches = None

# =============================================
# ACTION REGISTRY (DPLAN-043)
# =============================================

try:
    from aipass.daemon.apps.handlers.actions.actions_registry import (
        load_registry,
        is_action_due,
        update_last_run,
        mark_reminder_completed,
        migrate_plugins,
        next_due_str,
    )
    ACTION_REGISTRY_AVAILABLE = True
except ImportError:
    ACTION_REGISTRY_AVAILABLE = False
    load_registry = None
    is_action_due = None
    update_last_run = None
    mark_reminder_completed = None
    migrate_plugins = None
    next_due_str = None


# =============================================
# INTROSPECTION
# =============================================

def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("scheduler_ops Module")
    console.print("Facade for scheduler_cron.py — re-exports handler functions for cron entry point")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/schedule/")
    console.print("    - telegram_notifier.py (notify_triggered, notify_complete, notify_error — Telegram notifications)")
    console.print("    - task_registry.py (get_due_tasks, mark_dispatching, mark_completed, mark_pending, recover_stale_dispatches — task lifecycle)")
    console.print()
    console.print("  handlers/actions/")
    console.print("    - actions_registry.py (load_registry, is_action_due, update_last_run, mark_reminder_completed, migrate_plugins, next_due_str — action registry)")
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
    if command == "scheduler-ops":
        from aipass.cli.apps.modules import console

        console.print()
        console.print("[bold cyan]Scheduler Ops[/bold cyan] - Cron operations facade")
        console.print()
        console.print(f"  [dim]Telegram available:[/dim]  {TELEGRAM_AVAILABLE}")
        console.print(f"  [dim]Task registry:[/dim]       {TASK_REGISTRY_AVAILABLE}")
        console.print(f"  [dim]Action registry:[/dim]     {ACTION_REGISTRY_AVAILABLE}")
        console.print()
        console.print("[dim]This module is a facade used by scheduler_cron.py.[/dim]")
        console.print()
        return True
    return False
