# =================== AIPass ====================
# Name: alert_dismiss.py
# Version: 1.0.1
# Description: Dismiss alerts from .aipass/alerts.json via drone @hooks dismiss
# Branch: hooks
# Layer: apps/modules
# Created: 2026-07-14
# Modified: 2026-07-14
# =============================================

"""Dismiss alerts from .aipass/alerts.json by ID."""

import json
from pathlib import Path

from aipass.cli.apps.modules import err_console
from aipass.prax.apps.modules.logger import system_logger as logger

CONSOLE = err_console

HELP_COMMANDS = [
    ("dismiss <alert-id>", "Remove an alert from .aipass/alerts.json"),
]


def _find_aipass_dir() -> Path | None:
    """Walk up from CWD; return the nearest .aipass/ that contains alerts.json.

    Every branch has its own .aipass/ (branch prompt), so stopping at the first
    .aipass directory would never reach the project root where alerts.json lives.
    """
    search = Path.cwd()
    home = Path.home()
    while search != home and search.parent != search:
        aipass_dir = search / ".aipass"
        if (aipass_dir / "alerts.json").exists():
            return aipass_dir
        search = search.parent
    return None


def _dismiss_alert(alert_id: str) -> bool:
    """Remove an alert by ID from alerts.json. Returns True if found and removed."""
    aipass_dir = _find_aipass_dir()
    if not aipass_dir:
        CONSOLE.print("[red]No .aipass/ directory found in this directory tree.[/red]")
        return False

    alerts_path = aipass_dir / "alerts.json"
    if not alerts_path.exists():
        CONSOLE.print("[yellow]No alerts.json found — nothing to dismiss.[/yellow]")
        return False

    try:
        data = json.loads(alerts_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("[HOOKS] dismiss: read error: %s", exc)
        CONSOLE.print(f"[red]Failed to read alerts.json: {exc}[/red]")
        return False

    alerts = data.get("alerts", []) if isinstance(data, dict) else []
    original_count = len(alerts)
    remaining = [a for a in alerts if a.get("id") != alert_id]

    if len(remaining) == original_count:
        CONSOLE.print(f"[yellow]Alert {alert_id} not found.[/yellow]")
        return False

    try:
        alerts_path.write_text(
            json.dumps({"alerts": remaining}, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("[HOOKS] dismiss: write error: %s", exc)
        CONSOLE.print(f"[red]Failed to write alerts.json: {exc}[/red]")
        return False

    logger.info("[HOOKS] dismiss: removed alert %s", alert_id)
    CONSOLE.print(f"[green]Dismissed alert {alert_id}[/green]")
    return True


def print_introspection():
    """Print module structure for drone routing."""
    CONSOLE.print("[bold cyan]alert_dismiss[/bold cyan] — Remove alerts from .aipass/alerts.json")


def handle_command(command: str, args: list) -> bool:
    """Route dismiss commands from drone @hooks."""
    if command != "dismiss":
        return False

    if not args:
        print_introspection()
        CONSOLE.print()
        CONSOLE.print("  drone @hooks dismiss <alert-id>")
        CONSOLE.print()
        CONSOLE.print("Removes the alert with the given ID from .aipass/alerts.json.")
        return True

    if args[0] in ("--help", "-h", "help"):
        CONSOLE.print("[bold cyan]dismiss[/bold cyan] — Remove an alert")
        CONSOLE.print()
        CONSOLE.print("  drone @hooks dismiss <alert-id>")
        CONSOLE.print()
        CONSOLE.print("Removes the alert with the given ID from .aipass/alerts.json.")
        return True

    _dismiss_alert(args[0])
    return True
