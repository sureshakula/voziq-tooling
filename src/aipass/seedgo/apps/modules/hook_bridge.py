# =================== AIPass ====================
# Name: hook_bridge.py
# Description: Hook bridge installer — adds/removes AIPass hooks in settings
# Version: 1.0.0
# Created: 2026-04-22
# Modified: 2026-04-22
# =============================================

"""Hook bridge installer — adds/removes AIPass hooks in Claude Code settings.

bridge install     Add AIPass hooks to ~/.claude/settings.json (idempotent)
bridge uninstall   Remove only AIPass-added hook entries
bridge reinstall   Remove + re-add (upgrade path)
bridge status      Show current installation state
"""

from pathlib import Path

from aipass.prax import logger
from aipass.cli import console
from aipass.cli.apps.modules import error, warning
from aipass.seedgo.apps.handlers.hooks.bridge_handler import (
    count_aipass_hooks,
    ensure_aipass_env,
    install_hooks,
    read_settings,
    resolve_aipass_home,
    uninstall_hooks,
    write_settings,
)
from aipass.seedgo.apps.handlers.json import json_handler


SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def _run_install() -> None:
    """Install AIPass hooks into global settings."""
    aipass_home = resolve_aipass_home()
    if not aipass_home:
        error("Could not resolve AIPASS_HOME — set env var or install aipass package")
        return

    settings = read_settings(SETTINGS_PATH)
    existing = count_aipass_hooks(settings)
    if existing > 0:
        warning(f"AIPass hooks already installed ({existing} entries). Use 'bridge reinstall' to replace.")
        return

    ensure_aipass_env(settings, str(aipass_home))
    settings, added = install_hooks(settings)

    if added == 0:
        warning("No hooks to add (all events already populated).")
        return

    if not write_settings(SETTINGS_PATH, settings):
        error("Failed to write settings.json")
        return

    console.print(f"[green]Installed {added} AIPass hook entries into {SETTINGS_PATH}[/green]")
    console.print(f"[dim]AIPASS_HOME={aipass_home}[/dim]")
    json_handler.log_operation("bridge_install", {"added": added, "aipass_home": str(aipass_home)})


def _run_uninstall() -> None:
    """Remove AIPass hooks from global settings."""
    settings = read_settings(SETTINGS_PATH)
    existing = count_aipass_hooks(settings)
    if existing == 0:
        warning("No AIPass hooks found in settings.")
        return

    settings, removed = uninstall_hooks(settings)

    if not write_settings(SETTINGS_PATH, settings):
        error("Failed to write settings.json")
        return

    console.print(f"[green]Removed {removed} AIPass hook entries from {SETTINGS_PATH}[/green]")
    json_handler.log_operation("bridge_uninstall", {"removed": removed})


def _run_reinstall() -> None:
    """Uninstall then install AIPass hooks."""
    aipass_home = resolve_aipass_home()
    if not aipass_home:
        error("Could not resolve AIPASS_HOME")
        return

    settings = read_settings(SETTINGS_PATH)
    settings, removed = uninstall_hooks(settings)
    ensure_aipass_env(settings, str(aipass_home))
    settings, added = install_hooks(settings)

    if not write_settings(SETTINGS_PATH, settings):
        error("Failed to write settings.json")
        return

    console.print(f"[green]Reinstalled: removed {removed}, added {added} hook entries[/green]")
    json_handler.log_operation("bridge_reinstall", {"removed": removed, "added": added})


def _run_status() -> None:
    """Show current bridge installation status."""
    settings = read_settings(SETTINGS_PATH)
    count = count_aipass_hooks(settings)
    aipass_home = resolve_aipass_home()

    console.print()
    console.print("[bold cyan]Hook Bridge Status[/bold cyan]")
    console.print(f"  Settings: {SETTINGS_PATH}")
    console.print(f"  AIPASS_HOME: {aipass_home or '[red]not resolved[/red]'}")
    status = "[green](installed)[/green]" if count > 0 else "[dim](not installed)[/dim]"
    console.print(f"  AIPass hooks: {count} entries {status}")
    console.print()


# ---------------------------------------------------------------------------
# Introspection + routing
# ---------------------------------------------------------------------------


def print_help() -> None:
    """CLI --help entry point."""
    print_introspection()


def print_introspection() -> None:
    """Display module info and usage."""
    console.print()
    console.print("[bold cyan]hook_bridge Module[/bold cyan]")
    console.print("Installs/removes AIPass hooks in Claude Code settings.json")
    console.print()
    console.print("[yellow]Subcommands:[/yellow]")
    console.print("  [green]drone @seedgo bridge install[/green]     [dim]# Add AIPass hooks (idempotent)[/dim]")
    console.print("  [green]drone @seedgo bridge uninstall[/green]   [dim]# Remove AIPass hooks only[/dim]")
    console.print("  [green]drone @seedgo bridge reinstall[/green]   [dim]# Remove + re-add (upgrade)[/dim]")
    console.print("  [green]drone @seedgo bridge status[/green]      [dim]# Show installation status[/dim]")
    console.print()
    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print("  [cyan]handlers/hooks/[/cyan]")
    console.print("    [dim]- bridge_handler.py (settings I/O, hook manifest)[/dim]")
    console.print()


def handle_command(command: str, args: list) -> bool:
    """Handle 'bridge' command — hook installation management."""
    if command != "bridge":
        return False

    if not args:
        print_introspection()
        return True
    if args[0] in ("--help", "-h", "help"):
        print_help()
        return True

    subcommand = args[0]

    if subcommand == "install":
        _run_install()
        return True
    if subcommand == "uninstall":
        _run_uninstall()
        return True
    if subcommand == "reinstall":
        _run_reinstall()
        return True
    if subcommand == "status":
        _run_status()
        return True

    logger.info("hook_bridge: unknown subcommand %r", subcommand)
    console.print(f"[dim]Unknown subcommand: {subcommand!r}[/dim]")
    print_introspection()
    return True
