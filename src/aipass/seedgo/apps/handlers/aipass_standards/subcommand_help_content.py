# =================== AIPass ====================
# Name: subcommand_help_content.py
# Description: Subcommand Help Standards Content
# Version: 1.0.0
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""Subcommand Help Standards Content.

Provides Rich-formatted reference text for the subcommand help standard.
"""

from aipass.seedgo.apps.handlers.json import json_handler


def get_subcommand_help_standards() -> str:
    """Return Rich-formatted subcommand help standards text."""
    json_handler.log_operation("standard_content_queried", {"standard": "subcommand_help"})
    return """[bold white]SUBCOMMAND HELP STANDARD[/bold white]

[yellow]PURPOSE:[/yellow]
  Every branch entry point must handle [bold]<cmd> --help[/bold] by showing
  that subcommand's help — never execute the command, never silently
  fall back to top-level help.

[yellow]THE CONTRACT:[/yellow]

  [dim]drone @branch cmd --help[/dim]   →  shows cmd-specific help
  [dim]drone @branch cmd --help[/dim]   ✗  executes cmd (side-effect risk)
  [dim]drone @branch cmd --help[/dim]   ✗  shows top-level help (unhelpful)

[yellow]CANONICAL PATTERN (module-discovery branches):[/yellow]

  [dim]command = args[0][/dim]
  [dim]remaining = args[1:][/dim]

  [bold cyan]# Subcommand --help guard (REQUIRED)[/bold cyan]
  [dim]if remaining and remaining[0] in ["--help", "-h"]:[/dim]
  [dim]    for module in modules:[/dim]
  [dim]        if module.handle_command(command, ["--help"]):[/dim]
  [dim]            return 0[/dim]
  [dim]    print_help()  # fallback to top-level[/dim]
  [dim]    return 0[/dim]

  [dim]# Normal dispatch (only reached if NOT --help)[/dim]
  [dim]if route_command(command, remaining, modules):[/dim]
  [dim]    return 0[/dim]

[yellow]ALTERNATIVE PATTERNS (also accepted):[/yellow]

  [bold cyan]argparse with parse_known_args:[/bold cyan]
  [dim]parser.add_argument("--help", action="store_true", dest="show_help")[/dim]
  [dim]parsed, remaining = parser.parse_known_args()[/dim]
  [dim]if parsed.show_help:[/dim]
  [dim]    all_args = ["--help"] + all_args  # pass to handler[/dim]

  [bold cyan]Post-dispatch fallback:[/bold cyan]
  [dim]if not route_command(command, remaining, modules):[/dim]
  [dim]    if remaining and remaining[0] in ["--help", "-h"]:[/dim]
  [dim]        print_module_help(command, modules)[/dim]

[yellow]WHAT THE CHECKER DETECTS:[/yellow]

  [green]✓[/green] A [bold]--help[/bold] comparison on remaining/subcommand args (not args[0])
  [green]✓[/green] argparse [bold]parse_known_args()[/bold] call (absorbs --help)
  [red]✗[/red] Only top-level --help check (args[0] in ["--help", ...])
  [red]✗[/red] No --help handling at all

[yellow]KEY RULES:[/yellow]

  [bold white]Intercept before dispatch[/bold white] — don't let --help reach the handler
  [bold white]Show subcommand help[/bold white] — not top-level help
  [bold white]Never execute[/bold white] — --help must never trigger side effects
  [bold white]Scope: entry points only[/bold white] — apps/{branch}.py files"""
