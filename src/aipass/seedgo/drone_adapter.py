"""
Seedgo drone adapter — bridges drone routing to seedgo commands.

Drone discovers this module via aipass.drone.modules._MODULE_REGISTRY
and routes `drone @seedgo <command> [args]` here.
"""

import sys
from io import StringIO

DRONE_MODULE = {
    "name": "seedgo",
    "version": "2.0.0",
    "description": "Standards compliance through pluggable checker packs",
}


def handle_command(command: str, args: list[str] | None = None) -> dict:
    """Route a drone command to seedgo's entry point.

    Captures stdout/stderr and returns as dict for drone CLI to print.
    """
    if args is None:
        args = []

    # Build argv as if `seedgo <command> [args]` was called
    original_argv = sys.argv
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_out = StringIO()
    captured_err = StringIO()

    try:
        sys.argv = ["seedgo", command] + args
        sys.stdout = captured_out
        sys.stderr = captured_err

        # Import here to avoid circular imports at module level
        from aipass.seedgo.apps.seedgo import main
        exit_code = main()
    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
    except Exception as e:
        captured_err.write(str(e))
        exit_code = 1
    finally:
        sys.argv = original_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return {
        "stdout": captured_out.getvalue(),
        "stderr": captured_err.getvalue(),
        "exit_code": exit_code if isinstance(exit_code, int) else 1,
    }


def get_help(command: str | None = None) -> str:
    """Return help text for seedgo as Rich markup strings.

    Returns Rich markup (not captured ANSI) so drone's console.print()
    renders it cleanly — same pattern as get_introspective().
    """
    if command:
        result = handle_command(command, ["--help"])
        return result.get("stdout", "") or result.get("stderr", "")

    # Build help as Rich markup strings (drone renders these)
    try:
        from aipass.seedgo.apps.seedgo import discover_handler_packs, VERSION
        packs = discover_handler_packs()
    except Exception:
        return "seedgo — Standards compliance platform\nRun 'drone @seedgo --help' for usage\n"

    lines = []
    lines.append("")
    lines.append("[bold cyan]SEEDGO - Standards Platform for AIPass[/bold cyan]")
    lines.append(f"  Version: {VERSION}")
    lines.append("")
    lines.append("[dim]Code standards reference and automated compliance for all AIPass branches[/dim]")
    lines.append("")
    lines.append("─" * 70)
    lines.append("")

    # What is seedgo
    lines.append("[bold cyan]WHAT IS SEEDGO?[/bold cyan]")
    lines.append("")
    lines.append("Seedgo is the [bold]AIPass Standards Platform[/bold] — it:")
    lines.append("  [green]✓[/green] Provides [green]queryable code standards[/green] via content modules")
    lines.append("  [green]✓[/green] Runs automated checkers that score files 0-100 per standard")
    lines.append("  [green]✓[/green] Audits all branches with a single command")
    lines.append("  [green]✓[/green] Supports bypass rules for deliberate exceptions")
    lines.append("")

    # Checker packs
    if packs:
        lines.append("[bold cyan]CHECKER PACKS:[/bold cyan]")
        lines.append("")
        for pack in packs:
            lines.append(
                f"  [cyan]•[/cyan] {pack['name']}  "
                f"({pack['check_count']} checkers, {pack['content_count']} content modules)"
            )
        lines.append("")

    lines.append("─" * 70)
    lines.append("")

    # Usage
    lines.append("[bold cyan]USAGE:[/bold cyan]")
    lines.append("")
    lines.append("[yellow]Audit:[/yellow]")
    lines.append("  [dim]drone @seedgo audit                              # Show available packs[/dim]")
    lines.append("  [dim]drone @seedgo audit aipass                       # Audit all branches[/dim]")
    lines.append("  [dim]drone @seedgo audit aipass @spawn                # Audit specific branch[/dim]")
    lines.append("")
    lines.append("[yellow]Query Standards:[/yellow]")
    lines.append("  [dim]drone @seedgo standards_query                        # List packs[/dim]")
    lines.append("  [dim]drone @seedgo standards_query aipass_standards        # List standards[/dim]")
    lines.append("  [dim]drone @seedgo standards_query aipass_standards cli    # Show content[/dim]")
    lines.append("")

    lines.append("─" * 70)
    lines.append("")

    # Commands line for drone discovery
    lines.append("[dim]Commands: audit, standards_audit, standards_query, diagnostics, diagnostics_audit, readme, readme_update, --help[/dim]")
    lines.append("")

    return "\n".join(lines)


def get_introspective() -> str:
    """Discovery mode: show what seedgo has connected."""
    try:
        from aipass.seedgo.apps.seedgo import (
            discover_handler_packs, discover_modules, VERSION,
        )
        packs = discover_handler_packs()
        modules = discover_modules()

        lines = []
        lines.append(f"[bold cyan]SEEDGO - Standards Platform for AIPass[/bold cyan]")
        lines.append(f"  Version: {VERSION}")
        lines.append("")

        # Modules
        lines.append(f"[yellow]Discovered Modules:[/yellow] {len(modules)}")
        for module in modules:
            mod_name = getattr(module, "__name__", "unknown").split(".")[-1]
            desc = (module.__doc__ or "").strip().split("\n")[0] if module.__doc__ else "No description"
            lines.append(f"  [cyan]•[/cyan] {mod_name} — {desc}")
        if not modules:
            lines.append("  [dim]No modules discovered[/dim]")
        lines.append("")

        # Handler packs
        if packs:
            lines.append(f"[yellow]Checker Packs:[/yellow] {len(packs)}")
            for pack in packs:
                lines.append(
                    f"  [cyan]•[/cyan] {pack['name']}  "
                    f"({pack['check_count']} checkers, {pack['content_count']} content modules)"
                )
            lines.append("")

        lines.append("[dim]Run 'drone @seedgo --help' for usage[/dim]")
        lines.append("")

        return "\n".join(lines)
    except Exception:
        return "@seedgo — Standards compliance platform (run 'drone @seedgo --help' for usage)\n"
