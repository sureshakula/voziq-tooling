# =================== AIPass ====================
# Name: reporter.py
# Description: File Change Reporter Handler
# Version: 0.2.0
# Created: 2025-11-15
# Modified: 2026-03-09
# =============================================

"""
File Change Reporter Handler

Formats and displays file change events in real-time using CLI service provider.
Shows branch name, action type, and file path with Rich formatting.
"""

from pathlib import Path
from datetime import datetime

from aipass.cli.apps.modules import console, header

# =============================================================================
# FORMATTING
# =============================================================================

# Action symbols and colors (Rich markup)
ACTION_FORMAT = {
    'CREATED': {'symbol': '+', 'color': 'green'},
    'MODIFIED': {'symbol': '~', 'color': 'yellow'},
    'DELETED': {'symbol': '-', 'color': 'red'},
    'MOVED': {'symbol': '→', 'color': 'blue'}
}

# =============================================================================
# REPORTER FUNCTIONS
# =============================================================================

def format_change(branch_name: str, action: str, file_path: str) -> str:
    """
    Format a file change event for display with Rich markup

    Args:
        branch_name: Name of the branch
        action: Type of action (CREATED, MODIFIED, DELETED, MOVED)
        file_path: Path to the file

    Returns:
        Formatted string with Rich markup
    """
    timestamp = datetime.now().strftime('%H:%M:%S')
    fmt = ACTION_FORMAT.get(action, {'symbol': '?', 'color': 'white'})
    symbol = fmt['symbol']
    color = fmt['color']

    # Make path relative to branch for cleaner output
    try:
        path_obj = Path(file_path)
        relative_path = file_path
        for part in path_obj.parts:
            if part == 'aipass':
                idx = path_obj.parts.index(part)
                if idx + 1 < len(path_obj.parts):
                    relative_path = str(Path(*path_obj.parts[idx+1:]))
                break
    except Exception:
        relative_path = file_path

    # Rich markup format
    return f"[dim]\\[{timestamp}][/dim] [{color}]\\[{branch_name.upper():12}][/{color}] [{color}]{symbol}[/{color}] {relative_path}"


def report_change(branch_name: str, action: str, file_path: str) -> None:
    """
    Report a file change to terminal and log using CLI service

    Args:
        branch_name: Name of the branch
        action: Type of action (CREATED, MODIFIED, DELETED, MOVED)
        file_path: Path to the file
    """
    formatted = format_change(branch_name, action, file_path)
    console.print(formatted)


def print_header() -> None:
    """Print monitoring header using CLI service"""
    console.print()
    console.print("─" * 80)
    console.print("[bold cyan]🔍 BRANCH WATCHER[/bold cyan] [dim]- Real-time File Monitoring[/dim]")
    console.print("─" * 80)
    console.print()
    console.print("[cyan]Legend:[/cyan]")
    console.print("  [green]+[/green] CREATED   New file")
    console.print("  [yellow]~[/yellow] MODIFIED  File changed")
    console.print("  [red]-[/red] DELETED   File removed")
    console.print("  [blue]→[/blue] MOVED     File renamed/moved")
    console.print()
    console.print("[dim]Press Ctrl+C to stop monitoring[/dim]")
    console.print()
    console.print("─" * 80)
    console.print()


def print_footer(total_changes: int) -> None:
    """
    Print monitoring summary using CLI service

    Args:
        total_changes: Total number of changes detected
    """
    console.print()
    console.print("─" * 80)
    console.print(f"[cyan]Monitoring stopped.[/cyan] Total changes: [bold]{total_changes}[/bold]")
    console.print("─" * 80)
    console.print()
