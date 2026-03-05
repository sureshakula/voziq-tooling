#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: cli_content.py - CLI Standards Content Handler
# Date: 2025-11-12
# Version: 0.1.0
# Category: seed/standards/handlers
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-12): Initial handler - CLI standards content
#
# CODE STANDARDS:
#   - Handler provides content, module orchestrates output
#   - Pure function - returns string, no side effects
# =============================================

"""
CLI Standards Content Handler

Provides formatted CLI standards content.
Module orchestrates, handler implements.
"""


def get_cli_standards() -> str:
    """Return formatted CLI standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold red]OUTPUT STANDARD: Rich console.print() ONLY[/bold red]",
        "",
        "[yellow]POLICY:[/yellow] Rich formatting is THE standard for ALL AIPass output",
        "",
        "[green]✓ Approved:[/green]",
        "  [dim]from cli.apps.modules import console[/dim]",
        "  [dim]console.print(\"[cyan]This is the ONLY approved way[/cyan]\")[/dim]",
        "",
        "[red]✗ Deprecated:[/red] Bare print() statements",
        "  • Only in test/temp code",
        "  • Remove before commit",
        "",
        "[red]✗ Never use:[/red] parser.print_help()",
        "  • Outputs plain text (violates standard)",
        "  • Argparse is for PARSING only, not help output",
        "  • Write custom print_help() with console.print()",
        "",
        "─" * 70,
        "",
        "[bold cyan]DUAL APPROACH:[/bold cyan]",
        "",
        "[bold]1. Interactive (for humans)[/bold]",
        "   • Rich formatting, menus, questionary prompts",
        "   • Visual feedback, colors, progress bars",
        "",
        "[bold]2. Arguments (for AI via Drone)[/bold]",
        "   • Fast, scriptable, no interaction required",
        "   • [dim]drone <module> <command> [options][/dim]",
        "",
        "[yellow]RULE:[/yellow] Build BOTH or neither",
        "",
        "[bold cyan]CLI SERVICE PROVIDER:[/bold cyan]",
        "  [dim]from cli.apps.modules import console, header, success, error[/dim]",
        "  [dim]from cli.apps.modules import operation_start, track_operation[/dim]",
        "",
        "  • Consistent formatting across all branches",
        "  • Update CLI once → affects entire system",
        "  • Rich library wrappers for beautiful output",
        "",
        "[bold cyan]BRANCH-LEVEL CLI:[/bold cyan]",
        "  [dim]handlers/cli/prompts.py[/dim] - User interaction specific to branch",
        "",
        "[bold cyan]DRONE COMPLIANCE:[/bold cyan]",
        "  • Module responds to --help flag",
        "  • Help output includes 'Commands:' line",
        "  • Commands comma-separated with flags",
        "  • Example: [dim]Commands: cli, display, --help[/dim]",
        "",
        "[bold cyan]DEMONSTRATION:[/bold cyan]",
        "  [dim]/home/aipass/seed/apps/modules/test_cli_errors.py[/dim]",
        "  Shows CLI service usage with error handling",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]/home/aipass/standards/CODE_STANDARDS/cli.md[/dim]",
        "  [dim]/home/aipass/aipass_core/cli/README.json[/dim]",
        "  [dim]/home/aipass/aipass_core/planning/cli_layout_demo.py[/dim]",
        "",
        "─" * 70,
        "",
        "[bold cyan]RICH FORMATTING QUICK REFERENCE:[/bold cyan]",
        "",
        "[bold]Colors:[/bold]",
        "  [red]red[/red], [green]green[/green], [yellow]yellow[/yellow], [blue]blue[/blue], [cyan]cyan[/cyan], [magenta]magenta[/magenta]",
        "",
        "[bold]Styles:[/bold]",
        "  [bold]bold[/bold], [italic]italic[/italic], [dim]dim[/dim], [underline]underline[/underline]",
        "",
        "[bold]Combined:[/bold]",
        "  [bold red]bold red[/bold red], [bold cyan]bold cyan[/bold cyan], [dim yellow]dim yellow[/dim yellow]",
        "",
        "[bold]Usage:[/bold]",
        "  [dim]console.print(\"[bold green]Success![/bold green]\")[/dim]",
        "  [dim]console.print(\"[yellow]Warning:[/yellow] Check this\")[/dim]",
        "  [dim]console.print(\"[dim]Additional info...[/dim]\")[/dim]",
        "",
        "[bold]Emojis:[/bold]",
        "  ✅ Success   ❌ Error   ⚠️  Warning   ℹ️  Info",
        "  ⚙️  Processing   📝 Note   🔍 Search   ✨ Feature",
        "",
        "[bold]Documentation:[/bold]",
        "  [link=https://rich.readthedocs.io/en/stable/markup.html]https://rich.readthedocs.io/en/stable/markup.html[/link]",
    ]

    return "\n".join(lines)
