# =================== AIPass ====================
# Name: hooksound.py
# Version: 1.0.0
# Description: Hook sound control — mute/unmute all hook audio
# Branch: hooks
# Layer: apps/modules
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Hook sound control — mute and unmute all hook audio via drone @hooks hooksound."""

from aipass.cli.apps.modules import err_console
from aipass.hooks.apps.sound import MUTE_FLAG, is_muted

CONSOLE = err_console


def print_introspection():
    """Print module structure for drone routing."""
    status = "MUTED" if is_muted() else "ACTIVE"
    CONSOLE.print(f"[bold cyan]hooksound[/bold cyan] — Hook sound control ({status})")


def handle_command(command: str, args: list) -> bool:
    """Route hooksound commands from drone @hooks."""
    if command == "hooksound":
        sub = args[0] if args else None

        if sub in ("--help", "-h", "help"):
            CONSOLE.print("[bold cyan]hooksound[/bold cyan] — Mute/unmute all hook audio")
            CONSOLE.print()
            CONSOLE.print("  drone @hooks hooksound        Show current status")
            CONSOLE.print("  drone @hooks hooksound on     Unmute all hook sounds")
            CONSOLE.print("  drone @hooks hooksound off    Mute all hook sounds")
            return True

        if sub == "off":
            MUTE_FLAG.touch()
            CONSOLE.print("[yellow]Hook sounds MUTED[/yellow]")
            return True

        if sub == "on":
            if MUTE_FLAG.exists():
                MUTE_FLAG.unlink()
            CONSOLE.print("[green]Hook sounds ACTIVE[/green]")
            return True

        if sub is None:
            if is_muted():
                CONSOLE.print("[yellow]Hook sounds: MUTED[/yellow]")
                CONSOLE.print(f"  Flag: {MUTE_FLAG}")
                CONSOLE.print("  Run: drone @hooks hooksound on")
            else:
                CONSOLE.print("[green]Hook sounds: ACTIVE[/green]")
                CONSOLE.print("  Run: drone @hooks hooksound off")
            return True

    return False
