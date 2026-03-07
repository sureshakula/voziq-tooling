"""
Skill Format Standards Content Handler

Provides formatted SKILL.md format standards content.
Module orchestrates, handler implements.
"""

# =================== META ====================
# Name: skill_format_content.py
# Description: Skill Format Standards Content Handler
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


def get_skill_format_standards() -> str:
    """Return formatted skill format standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold cyan]CORE PRINCIPLE:[/bold cyan]",
        "  Every skill MUST have a SKILL.md with valid YAML frontmatter",
        "  The frontmatter is the skill's identity - without it, the skill is invisible",
        "",
        "[bold cyan]REQUIRED FIELDS:[/bold cyan]",
        "",
        "  [yellow]name:[/yellow]         Skill name (non-empty string)",
        "  [yellow]description:[/yellow]  What the skill does (non-empty string)",
        "",
        "[bold cyan]OPTIONAL FIELDS:[/bold cyan]",
        "",
        "  [dim]version:[/dim]      Semver format (e.g., 1.0.0, 0.2.1)",
        "  [dim]has_handler:[/dim]  Boolean - if true, handler.py must exist",
        "  [dim]author:[/dim]       Who created the skill",
        "  [dim]tags:[/dim]         List of categorization tags",
        "",
        "[bold cyan]VALID SKILL.md FORMAT:[/bold cyan]",
        "",
        "  [dim]---[/dim]",
        "  [dim]name: my_skill[/dim]",
        "  [dim]description: Does something useful[/dim]",
        "  [dim]version: 1.0.0[/dim]",
        "  [dim]has_handler: true[/dim]",
        "  [dim]---[/dim]",
        "",
        "  [dim]# My Skill[/dim]",
        "  [dim]Detailed documentation below the frontmatter...[/dim]",
        "",
        "[yellow]CHECKS PERFORMED:[/yellow]",
        "",
        "  1. [bold]SKILL.md exists[/bold] in skill directory",
        "  2. [bold]YAML frontmatter parseable[/bold] (valid --- delimited block)",
        "  3. [bold]name field[/bold] present and non-empty",
        "  4. [bold]description field[/bold] present and non-empty",
        "  5. [bold]has_handler consistency[/bold] - if true, handler.py must exist",
        "  6. [bold]version format[/bold] - semver if present",
        "",
        "[yellow]WARNINGS:[/yellow]",
        "  - Missing SKILL.md = [red]skill is invisible to the system[/red]",
        "  - Invalid YAML = [red]skill metadata cannot be loaded[/red]",
        "  - has_handler: true without handler.py = [red]broken skill[/red]",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]See: seedgo standards pack (skills)[/dim]",
    ]

    return "\n".join(lines)
