"""
Skill Handler Standards Content Handler

Provides formatted handler contract standards content.
Module orchestrates, handler implements.
"""

# =================== META ====================
# Name: skill_handler_content.py
# Description: Skill Handler Standards Content Handler
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


def get_skill_handler_standards() -> str:
    """Return formatted skill handler standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold cyan]CORE PRINCIPLE:[/bold cyan]",
        "  Skill handlers implement a standard contract for predictable execution",
        "  Handlers never print, always return structured dicts",
        "",
        "[bold cyan]REQUIRED CONTRACT:[/bold cyan]",
        "",
        "  [yellow]run(action, args, config) -> dict[/yellow]",
        "",
        "  Parameters:",
        "    [dim]action[/dim]  - str: The action to perform",
        "    [dim]args[/dim]    - dict: Arguments for the action",
        "    [dim]config[/dim]  - dict: Configuration/context",
        "",
        "  Return keys:",
        "    [dim]success[/dim] - bool: Whether the action succeeded",
        "    [dim]output[/dim]  - any: Result data",
        "    [dim]error[/dim]   - str or None: Error message if failed",
        "",
        "[bold cyan]RECOMMENDED:[/bold cyan]",
        "",
        "  [yellow]get_actions() -> list[/yellow]",
        "",
        "  Returns list of supported action names",
        "  Enables introspection and auto-discovery",
        "",
        "[bold cyan]EXAMPLE HANDLER:[/bold cyan]",
        "",
        '  [dim]def run(action, args, config):[/dim]',
        '  [dim]    if action == "greet":[/dim]',
        '  [dim]        name = args.get("name", "world")[/dim]',
        '  [dim]        return {"success": True, "output": f"Hello {name}", "error": None}[/dim]',
        '  [dim]    return {"success": False, "output": None, "error": f"Unknown action: {action}"}[/dim]',
        "",
        '  [dim]def get_actions():[/dim]',
        '  [dim]    return ["greet"][/dim]',
        "",
        "[yellow]CHECKS PERFORMED:[/yellow]",
        "",
        "  1. [bold]handler.py has run() function[/bold]",
        "  2. [bold]run() accepts action, args, config[/bold] parameters",
        "  3. [bold]run() return annotation[/bold] is dict (if present)",
        "  4. [bold]No print() calls[/bold] in handler code",
        "  5. [bold]get_actions() exists[/bold] (WARNING level, not ERROR)",
        "",
        "[yellow]WARNINGS:[/yellow]",
        "  - print() in handlers = [red]breaks structured output[/red]",
        "  - Missing run() = [red]handler cannot be invoked[/red]",
        "  - Wrong parameters = [red]caller will crash[/red]",
        "  - Missing get_actions() = [yellow]reduced discoverability[/yellow]",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]See: seedgo standards pack (skills)[/dim]",
    ]

    return "\n".join(lines)
