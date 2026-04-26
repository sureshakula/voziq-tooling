# =================== AIPass ====================
# Name: handler_import_content.py
# Description: Handler Import Standards Content Handler
# Version: 1.0.0
# Created: 2026-04-26
# Modified: 2026-04-26
# =============================================

"""
Handler Import Standards Content Handler

Provides formatted handler import standards content.
Module orchestrates, handler implements.
"""

from aipass.seedgo.apps.handlers.json import json_handler


def get_handler_import_standards() -> str:
    """Return formatted handler import standards content with Rich markup.

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold red]HANDLER IMPORT STANDARD[/bold red]",
        "",
        "[bold cyan]CORE RULE:[/bold cyan] Every apps/__init__.py must contain 'from . import handlers'",
        "",
        "[yellow]RULE:[/yellow] Python 3.10 mock.patch resolution requires explicit subpackage imports in __init__.py.",
        "  Without 'from . import handlers', mock.patch() targeting handler"
        " submodules fails with AttributeError at test time.",
        "",
        "─" * 70,
        "",
        "[bold cyan]WHY THIS MATTERS:[/bold cyan]",
        "",
        "  [red]✗[/red] mock.patch('aipass.branch.apps.handlers.some_handler') fails silently",
        "  [red]✗[/red] Python 3.10 getattr resolution needs the subpackage pre-imported",
        "  [red]✗[/red] Tests pass on 3.11+ but break on 3.10 without the explicit import",
        "  [red]✗[/red] CI uses 3.10 -- broken patches mean false green tests",
        "",
        "─" * 70,
        "",
        "[bold cyan]WHAT IS CHECKED:[/bold cyan]",
        "",
        "  [yellow]Scope:[/yellow] branch_level -- one check per branch",
        "  [yellow]Check:[/yellow] Does apps/__init__.py contain 'from . import handlers'?",
        "  [yellow]Pass:[/yellow]  Import found → [green]score 100[/green]",
        "  [yellow]Fail:[/yellow]  Import missing → [red]score 0[/red]",
        "",
        "─" * 70,
        "",
        "[bold cyan]EXAMPLES:[/bold cyan]",
        "",
        "[bold]Good (explicit handler import):[/bold]",
        "  [green]✓[/green] [dim]from . import handlers[/dim]",
        "  [green]✓[/green] [dim]from . import modules[/dim]",
        "  [green]✓[/green] [dim]from . import handlers  # noqa[/dim]",
        "",
        "[bold]Bad (missing handler import):[/bold]",
        "  [red]✗[/red] [dim]# empty __init__.py[/dim]",
        "  [red]✗[/red] [dim]from . import modules  # but no handlers[/dim]",
        "",
        "─" * 70,
        "",
        "[bold cyan]HOW TO FIX:[/bold cyan]",
        "",
        "  Add this line to apps/__init__.py:",
        "",
        "  [bold]from . import handlers[/bold]",
        "",
        "  That's it. One line. The import ensures Python registers the",
        "  handlers subpackage on the apps namespace so mock.patch can",
        "  resolve it via getattr chain.",
        "",
        "─" * 70,
        "",
        "[bold cyan]SCORING:[/bold cyan]",
        "  [green]100[/green] - 'from . import handlers' found in apps/__init__.py",
        "  [red]  0[/red] - Import missing from apps/__init__.py",
        "  [red]  0[/red] - apps/__init__.py not found",
        "  [green]100[/green] - Bypassed via .seedgo/bypass.json",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]See: seedgo standards pack (handler_import)[/dim]",
    ]

    json_handler.log_operation("standard_content_queried", {"standard": "handler_import"})
    return "\n".join(lines)
