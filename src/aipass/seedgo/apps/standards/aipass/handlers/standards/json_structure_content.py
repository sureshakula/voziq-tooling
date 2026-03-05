#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: json_structure_content.py - JSON Structure Standards Content Handler
# Date: 2025-11-13
# Version: 0.3.0
# Category: seed/standards/handlers
#
# CHANGELOG (Max 5 entries):
#   - v0.3.0 (2025-11-21): Added mandatory json_handler.py setup section with path configuration warnings
#   - v0.2.0 (2025-11-13): Condensed content - truth-checked against codebase
#   - v0.1.0 (2025-11-13): Initial handler - JSON structure standards content
#
# CODE STANDARDS:
#   - Handler provides content, module orchestrates output
#   - Pure function - returns string, no side effects
# =============================================

"""
JSON Structure Standards Content Handler

Provides formatted JSON structure standards content.
Module orchestrates, handler implements.
"""


def get_json_structure_standards() -> str:
    """Return formatted JSON structure standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold cyan]THREE-JSON PATTERN:[/bold cyan]",
        "",
        "[bold]Every module gets 3 auto-created files:[/bold]",
        "  • [yellow]module_config.json[/yellow] - Settings, limits (small, stable)",
        "  • [yellow]module_data.json[/yellow]   - Metrics, state (medium, periodic)",
        "  • [yellow]module_log.json[/yellow]    - Operations history (auto-rotating)",
        "",
        "[yellow]RULE:[/yellow] Auto-created on first use - NEVER create manually",
        "",
        "[bold cyan]USAGE (AUTO-DETECTION):[/bold cyan]",
        "  [dim]from seed.apps.handlers.json import json_handler[/dim]",
        "",
        "  [dim]# Handler auto-detects calling module name:[/dim]",
        "  [dim]json_handler.log_operation(\"operation_name\", {\"key\": \"value\"})[/dim]",
        "",
        "  [dim]# Creates module_config.json, module_data.json, module_log.json[/dim]",
        "  [dim]# Based on templates in apps/json_templates/default/[/dim]",
        "",
        "[bold cyan]LOG ROTATION (CRITICAL):[/bold cyan]",
        "  Set in config.json:",
        "  [dim]{[/dim]",
        "    [dim]\"config\": { \"max_log_entries\": 100 }[/dim]",
        "  [dim]}[/dim]",
        "",
        "  • Handler auto-rotates when limit reached",
        "  • Keeps most recent N entries (FIFO)",
        "  • [yellow]⚠️  Prevents log explosion (drone logs hit 171KB/7001 entries)[/yellow]",
        "",
        "[bold cyan]LOG STRUCTURE:[/bold cyan]",
        "  Array of entries (NOT object with \"entries\" key):",
        "  [dim][[/dim]",
        "    [dim]{ \"timestamp\": \"...\", \"operation\": \"...\", \"data\": {...} }[/dim]",
        "  [dim]][/dim]",
        "",
        "[bold cyan]LOCATIONS:[/bold cyan]",
        "  • Seed: [dim]/home/aipass/seed/seed_json/[/dim]",
        "  • Branches: [dim]/home/aipass/aipass_core/{branch}/{branch}_json/[/dim]",
        "",
        "[bold red]SETUP json_handler.py (MANDATORY):[/bold red]",
        "  [red]✗ DO NOT copy SEED's handler without changing paths![/red]",
        "",
        "  [green]✓ Update BRANCH_ROOT:[/green]",
        "    [dim]{BRANCH}_ROOT = Path.home() / \"aipass_core\" / \"{branch}\"[/dim]",
        "",
        "  [green]✓ Update JSON_DIR:[/green]",
        "    [dim]{BRANCH}_JSON_DIR = {BRANCH}_ROOT / \"{branch}_json\"[/dim]",
        "",
        "  [green]✓ Update TEMPLATES_DIR:[/green]",
        "    [dim]JSON_TEMPLATES_DIR = {BRANCH}_ROOT / \"apps\" / \"json_templates\"[/dim]",
        "",
        "  [yellow]Validate:[/yellow] Run standards checker on json_handler.py",
        "  [dim]Expected: 100/100 on JSON STRUCTURE standard[/dim]",
        "",
        "[bold cyan]SPECIAL JSONS:[/bold cyan]",
        "  • [bold]Registries:[/bold] Collections (BRANCH_REGISTRY.json)",
        "  • [bold]Custom:[/bold] Module-specific needs (no limit)",
        "  • [dim]Not part of three-JSON pattern[/dim]",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]/home/aipass/standards/CODE_STANDARDS/json_structure.md[/dim]",
        "  [dim]/home/aipass/seed/apps/handlers/json/json_handler.py[/dim]",
    ]

    return "\n".join(lines)
