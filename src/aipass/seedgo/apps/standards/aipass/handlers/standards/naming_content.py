#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: naming_content.py - Naming Standards Content Handler
# Date: 2025-11-13
# Version: 0.1.0
# Category: seed/standards/handlers
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-13): Initial handler - Naming standards content
#
# CODE STANDARDS:
#   - Handler provides content, module orchestrates output
#   - Pure function - returns string, no side effects
# =============================================

"""
Naming Standards Content Handler

Provides formatted naming standards content.
Module orchestrates, handler implements.
"""


def get_naming_standards() -> str:
    """Return formatted naming standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold cyan]CORE PRINCIPLE:[/bold cyan] Path = Context, Name = Action",
        "",
        "[yellow]RULE:[/yellow] The path provides context, the filename describes the action",
        "  Path already tells you domain → no need to repeat in filename",
        "",
        "─" * 70,
        "",
        "[bold cyan]REAL EXAMPLES (from codebase):[/bold cyan]",
        "",
        "[bold]Good:[/bold]",
        "  [green]✓[/green] [dim]cli/apps/handlers/error/decorators.py[/dim]",
        "  [green]✓[/green] [dim]cli/apps/handlers/error/formatters.py[/dim]",
        "  [green]✓[/green] [dim]prax/apps/handlers/config/load_config.py[/dim]",
        "  [green]✓[/green] [dim]seed/apps/handlers/domain1/ops.py[/dim]",
        "",
        "[bold]Bad (current violations):[/bold]",
        "  [red]✗[/red] [dim]prax/apps/handlers/json/json_ops.py[/dim] - redundant 'json_'",
        "  [red]✗[/red] [dim]prax/apps/handlers/json/json_handler.py[/dim] - redundant 'json_'",
        "",
        "─" * 70,
        "",
        "[bold cyan]STANDARD VERBS:[/bold cyan]",
        "",
        "[bold]Core operations:[/bold]",
        "  create, ops, load, save, initialize",
        "",
        "[bold]Transformation:[/bold]",
        "  formatters, decorators, logger",
        "",
        "[bold]Handlers:[/bold]",
        "  prompts (user interaction), content (data providers)",
        "",
        "─" * 70,
        "",
        "[bold cyan]PATTERN:[/bold cyan] [dim]handlers/<domain>/<action>.py[/dim]",
        "",
        "[yellow]WHY THIS MATTERS:[/yellow]",
        "  • Zero-cost navigation - predictable file locations",
        "  • Easy comparison - same structure across all branches",
        "  • Marketplace ready - handler purpose is immediately clear",
        "  • No lies when refactoring - path defines context, not name",
        "",
        "─" * 70,
        "",
        "[bold cyan]KEY WARNINGS:[/bold cyan]",
        "  [yellow]⚠[/yellow]  This is aspirational - codebase has legacy violations",
        "  [yellow]⚠[/yellow]  New code MUST follow standard - no new violations",
        "  [yellow]⚠[/yellow]  Legacy code being migrated gradually",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]/home/aipass/standards/CODE_STANDARDS/naming.md[/dim]",
    ]

    return "\n".join(lines)
