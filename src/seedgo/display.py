"""Rich-based display utilities for seedgo CLI output.

Provides consistent, styled terminal output using the Rich library.
All seedgo CLI commands use these functions for human-facing output.

Functions:
    console          — Shared Rich Console instance.
    print_header     — Branded section header with optional subtitle.
    print_plugin     — Plugin check result line (name + verdict + score).
    print_check_item — Individual check item with severity marker.
    print_summary    — Overall score and verdict.
    print_counts     — Check count summary (passed/failed/warnings).
    print_plugin_table — Table of discovered plugins (for `seedgo list`).
    print_init       — Init success message.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from .models import Severity

console = Console()


def print_header(title: str, subtitle: str | None = None) -> None:
    """Print a branded seedgo header panel."""
    content = f"[bold cyan]{title}[/bold cyan]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(content, border_style="cyan", box=box.ROUNDED, expand=False, padding=(0, 2)))
    console.print()


def print_plugin(name: str, file_path: str, passed: bool, score: int) -> None:
    """Print a plugin result header line."""
    if passed:
        verdict = "[green]PASS[/green]"
        icon = "[green]✓[/green]"
    else:
        verdict = "[red]FAIL[/red]"
        icon = "[red]✗[/red]"

    # Truncate long paths for readability
    path_display = file_path
    if len(path_display) > 40:
        path_display = "..." + path_display[-37:]

    dots = "[dim]" + "·" * max(1, 48 - len(name) - len(path_display)) + "[/dim]"
    console.print(f"  {icon} [bold]{name}[/bold]  [dim]{path_display}[/dim] {dots} {verdict} [dim]({score}/100)[/dim]")


def print_check_item(name: str, passed: bool, message: str, severity: Severity,
                     line: int | None = None, fix_hint: str | None = None) -> None:
    """Print a single check item with appropriate severity marker."""
    if passed:
        marker = "[green]✓[/green]"
        name_style = "dim"
    elif severity == Severity.ERROR:
        marker = "[red]✗[/red]"
        name_style = "red"
    elif severity == Severity.WARNING:
        marker = "[yellow]⚠[/yellow]"
        name_style = "yellow"
    else:
        marker = "[cyan]ℹ[/cyan]"
        name_style = "cyan"

    line_ref = f" [dim]\\[line {line}][/dim]" if line is not None else ""
    console.print(f"      {marker} [{name_style}]{name}[/{name_style}]: {message}{line_ref}")

    if fix_hint and not passed:
        console.print(f"        [dim]hint: {fix_hint}[/dim]")


def print_summary(score: int, passed: bool, threshold: int) -> None:
    """Print the overall score and verdict."""
    if passed:
        verdict = "[bold green]PASS[/bold green]"
    else:
        verdict = "[bold red]FAIL[/bold red]"

    console.print(f"  [bold]Overall:[/bold] {score}/100 — {verdict} [dim](threshold: {threshold})[/dim]")


def print_counts(plugins_passed: int, plugins_failed: int,
                 error_count: int = 0, warning_count: int = 0) -> None:
    """Print the check count summary line."""
    total = plugins_passed + plugins_failed
    parts = [f"{total} check(s) ran", f"{plugins_passed} passed", f"{plugins_failed} failed"]
    if error_count:
        parts.append(f"[red]{error_count} error(s)[/red]")
    if warning_count:
        parts.append(f"[yellow]{warning_count} warning(s)[/yellow]")

    console.print("  " + ", ".join(parts))


def print_separator() -> None:
    """Print a horizontal separator."""
    console.print()
    console.print("[dim]" + "─" * 56 + "[/dim]")
    console.print()


def print_plugin_table(plugins: list[dict]) -> None:
    """Print a Rich table of discovered plugins."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        box=box.ROUNDED,
        expand=False,
    )
    table.add_column("Plugin", style="bold")
    table.add_column("Source", style="dim")
    table.add_column("File Types")
    table.add_column("Description", style="dim")

    for plugin in plugins:
        module = plugin["module"]
        name = plugin["name"]
        source = plugin["source"]
        description = getattr(module, "PLUGIN_DESCRIPTION", "")
        file_types = getattr(module, "FILE_TYPES", ["*"])
        types_str = ", ".join(file_types)
        table.add_row(name, source, types_str, description)

    console.print(table)


def print_init_success(config_path: str, plugins_path: str, profile: str | None = None) -> None:
    """Print init success message."""
    console.print()
    console.print("[green]✓[/green] [bold]Seed Go initialized[/bold]")
    console.print()
    console.print(f"  Config:   [dim]{config_path}[/dim]")
    console.print(f"  Plugins:  [dim]{plugins_path}[/dim]")
    if profile:
        console.print(f"  Profile:  [cyan]{profile}[/cyan]")
    console.print()
    console.print("  [bold]Next steps:[/bold]")
    console.print("  1. Add plugins to .seedgo/plugins/")
    console.print("  2. Run: [cyan]seedgo check[/cyan]")
    console.print()


def print_no_results() -> None:
    """Print message when no checks ran."""
    console.print("[dim]No checks ran.[/dim]")


def print_error(message: str, suggestion: str | None = None) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] [red bold]{message}[/red bold]")
    if suggestion:
        console.print(f"  [yellow]→ {suggestion}[/yellow]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow]  [yellow]{message}[/yellow]")
