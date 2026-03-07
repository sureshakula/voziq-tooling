"""
Skill Structure Standards Content Handler

Provides formatted directory structure standards content.
Module orchestrates, handler implements.
"""

# =================== META ====================
# Name: skill_structure_content.py
# Description: Skill Structure Standards Content Handler
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


def get_skill_structure_standards() -> str:
    """Return formatted skill structure standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold cyan]CORE PRINCIPLE:[/bold cyan]",
        "  Skills follow a tiered structure based on complexity",
        "  Simple skills need only a SKILL.md; complex skills use the 3-layer pattern",
        "",
        "[bold cyan]TIER 1 - MINIMAL (documentation only):[/bold cyan]",
        "",
        "  [dim]skill_name/[/dim]",
        "  [dim]  SKILL.md[/dim]",
        "",
        "  Use when: skill is a prompt, reference, or static content",
        "",
        "[bold cyan]TIER 2 - EXECUTABLE (single handler):[/bold cyan]",
        "",
        "  [dim]skill_name/[/dim]",
        "  [dim]  SKILL.md[/dim]",
        "  [dim]  handler.py[/dim]",
        "",
        "  Use when: skill has executable logic but is self-contained",
        "",
        "[bold cyan]TIER 3 - FULL (3-layer architecture):[/bold cyan]",
        "",
        "  [dim]skill_name/[/dim]",
        "  [dim]  SKILL.md[/dim]",
        "  [dim]  apps/[/dim]",
        "  [dim]    modules/[/dim]",
        "  [dim]    handlers/[/dim]",
        "",
        "  Use when: skill has complex logic requiring orchestration",
        "",
        "[yellow]CHECKS PERFORMED:[/yellow]",
        "",
        "  1. [bold]Skill directory exists[/bold] and is a directory",
        "  2. [bold]SKILL.md exists[/bold] (required for all tiers)",
        "  3. [bold]handler.py has run()[/bold] if handler.py exists",
        "  4. [bold]apps/ has modules/ and handlers/[/bold] if apps/ exists",
        "  5. [bold]No stray files[/bold] outside the valid structure",
        "",
        "[yellow]VALID FILES IN SKILL ROOT:[/yellow]",
        "  SKILL.md, handler.py, __init__.py, apps/, tests/, docs/,",
        "  requirements.txt, .gitignore",
        "",
        "[yellow]WARNINGS:[/yellow]",
        "  - Tier 3 without modules/ or handlers/ = [red]incomplete 3-layer[/red]",
        "  - handler.py without run() = [red]broken contract[/red]",
        "  - Stray files = [yellow]possible misplaced code[/yellow]",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]See: seedgo standards pack (skills)[/dim]",
    ]

    return "\n".join(lines)
