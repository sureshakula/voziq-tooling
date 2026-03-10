# =================== AIPass ====================
# Name: log_structure_content.py
# Description: Log Structure Standards Content Handler
# Version: 1.1.0
# Created: 2026-03-06
# Modified: 2026-03-08
# =============================================

"""
Log Structure Standards Content Handler

Provides formatted display of log structure standards for terminal output.
Describes the hierarchical log placement model where every directory
containing .py code has a sibling logs/ directory.
"""

def get_log_structure_standards() -> str:
    """Return formatted log structure standards for display."""
    lines = [
        "[bold red]HIERARCHICAL LOG STRUCTURE[/bold red]",
        "",
        "[yellow]CORE PRINCIPLE:[/yellow] Logs live where the code lives — every directory",
        "  containing .py files should have a sibling [bold]logs/[/bold] directory",
        "",
        "[bold cyan]DUAL LOGGING MODEL:[/bold cyan]",
        "  [green]1.[/green] [bold]system_logs/[/bold] at repo root — central aggregation ({branch}_{module}.log)",
        "  [green]2.[/green] [bold]logs/[/bold] at every code level — hierarchical local placement",
        "",
        "[bold cyan]REQUIREMENTS:[/bold cyan]",
        "  [green]1.[/green] Every directory with .py files has a sibling [bold]logs/[/bold] directory",
        "  [green]2.[/green] No hardcoded absolute paths to .log files",
        "  [green]3.[/green] No /home/ references in logging configuration",
        "",
        "[bold cyan]HIERARCHICAL DIRECTORY PATTERN:[/bold cyan]",
        "  [dim]src/aipass/{branch}/[/dim]",
        "  [dim]  logs/                          <-- branch root logs[/dim]",
        "  [dim]  apps/[/dim]",
        "  [dim]    logs/                        <-- entry point level[/dim]",
        "  [dim]    modules/[/dim]",
        "  [dim]      logs/                      <-- module level[/dim]",
        "  [dim]    handlers/[/dim]",
        "  [dim]      logs/                      <-- handler root[/dim]",
        "  [dim]      dispatch/[/dim]",
        "  [dim]        logs/                    <-- sub-handler level[/dim]",
        "  [dim]      email/[/dim]",
        "  [dim]        logs/                    <-- sub-handler level[/dim]",
        "",
        "[bold cyan]LOG PATH PATTERN:[/bold cyan]",
        "  [green]CORRECT:[/green]  Use prax's system_logger (auto-routes to correct location)",
        "  [dim]  from aipass.prax.apps.modules.logger import system_logger[/dim]",
        "  [dim]  system_logger.info('message')  # prax handles hierarchical placement[/dim]",
        "",
        "  [green]ALSO OK:[/green]  Manual relative path to sibling logs/",
        "  [dim]  LOG_DIR = Path(__file__).resolve().parent / 'logs'[/dim]",
        "  [dim]  log_path = LOG_DIR / 'my_handler.log'[/dim]",
        "",
        "  [red]WRONG:[/red]  All logs dumped at branch root only",
        "  [dim]  LOG_DIR = Path(__file__).resolve().parents[3] / 'logs'[/dim]",
        "  [dim]  # All handlers write to branch/logs/ — no hierarchy[/dim]",
        "",
        "  [red]WRONG:[/red]  Hardcoded absolute paths",
        "  [dim]  path = '/absolute/path/to/system_logs/module.log'[/dim]",
        "  [dim]  path = Path.home() / 'logs' / 'module.log'[/dim]",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]Prax logger: src/aipass/prax/apps/modules/logger.py[/dim]",
        "  [dim]Hierarchical resolver: src/aipass/prax/apps/handlers/config/load.py[/dim]",
    ]
    return "\n".join(lines)
