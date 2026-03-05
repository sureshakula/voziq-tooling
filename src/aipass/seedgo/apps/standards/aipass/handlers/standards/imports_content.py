#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: imports_content.py - Import Standards Content Handler
# Date: 2025-11-13
# Version: 0.2.0
# Category: seed/standards/handlers
#
# CHANGELOG (Max 5 entries):
#   - v0.2.0 (2025-11-13): Condensed version - truth-checked against codebase
#   - v0.1.0 (2025-11-13): Initial handler - Import standards content
#
# CODE STANDARDS:
#   - Handler provides content, module orchestrates output
#   - Pure function - returns string, no side effects
# =============================================

"""
Import Standards Content Handler

Provides formatted import standards content.
Module orchestrates, handler implements.
"""


def get_imports_standards() -> str:
    """Return formatted import standards content with Rich markup

    Returns:
        str: Formatted standards text with Rich styling
    """
    lines = [
        "[bold cyan]STANDARD IMPORT ORDER:[/bold cyan]",
        "",
        "[bold]1. Infrastructure[/bold]",
        "   • AIPASS_ROOT = Path.home() / 'aipass_core'",
        "   • sys.path.insert(0, str(AIPASS_ROOT))",
        "",
        "[bold]2. Standard library[/bold]",
        "   • Grouped by category, alphabetical",
        "   • json, datetime, typing, pathlib, etc.",
        "",
        "[bold]3. Prax logger (nearly always)[/bold]",
        "   • [dim]from prax.apps.modules.logger import system_logger as logger[/dim]",
        "",
        "[bold]4. Services (CLI, etc.)[/bold]",
        "   • [dim]from cli.apps.modules import console, header, success[/dim]",
        "",
        "[bold]5. Internal handlers[/bold]",
        "   • [dim]from seed.apps.handlers.json import json_handler[/dim]",
        "",
        "[yellow]RULE:[/yellow] Infrastructure → Stdlib → Prax → Services → Internal",
        "",
        "[bold cyan]COMPLETE PATTERN:[/bold cyan]",
        "  [dim]#!/home/aipass/.venv/bin/python3[/dim]",
        "",
        "  [dim]import sys[/dim]",
        "  [dim]from pathlib import Path[/dim]",
        "  [dim]AIPASS_ROOT = Path.home() / 'aipass_core'[/dim]",
        "  [dim]sys.path.insert(0, str(AIPASS_ROOT))[/dim]",
        "",
        "  [dim]import json[/dim]",
        "  [dim]from datetime import datetime[/dim]",
        "  [dim]from typing import Dict, List, Optional[/dim]",
        "",
        "  [dim]from prax.apps.modules.logger import system_logger as logger[/dim]",
        "  [dim]from cli.apps.modules import console, header[/dim]",
        "  [dim]from seed.apps.handlers.json import json_handler[/dim]",
        "",
        "[bold cyan]CRITICAL RULES:[/bold cyan]",
        "  [yellow]✓[/yellow] Path.home() - NEVER hardcode /home/username",
        "  [yellow]✓[/yellow] Absolute imports - NO relative imports (...)",
        "  [yellow]✓[/yellow] Handlers CANNOT import modules (independence)",
        "  [yellow]✓[/yellow] Services before internal (Prax, CLI, then handlers)",
        "",
        "[bold cyan]HANDLER INDEPENDENCE:[/bold cyan]",
        "  Handlers import handlers ✓",
        "  Handlers import services ✓",
        "  Handlers import modules ✗ [dim](BREAKS INDEPENDENCE)[/dim]",
        "",
        "[bold cyan]SERVICE INVOCATION - CONTEXT REQUIREMENTS:[/bold cyan]",
        "",
        "[bold]Context-Independent Services (work anywhere):[/bold]",
        "  • Prax logger - import and use from any location",
        "  • CLI services - import and use from any location",
        "",
        "[bold]Context-Dependent Services (PWD detection):[/bold]",
        "  • [yellow]AI_MAIL[/yellow] - requires calling from branch directory",
        "  • Uses PWD to detect sender identity (@seed, @drone, etc.)",
        "  • Auto-generates config at [branch]/seed_json/user_config.json",
        "",
        "[bold]Best Practice - Use Drone:[/bold]",
        "  [dim]subprocess.run([\"drone\", \"email\", \"send\", \"@recipient\", \"Subject\", \"Message\"])[/dim]",
        "  • Drone handles PWD detection automatically",
        "",
        "[bold]Direct Invocation (Advanced):[/bold]",
        "  [dim]subprocess.run([\"python3\", \"/home/aipass/aipass_core/ai_mail/apps/ai_mail.py\", ...],[/dim]",
        "  [dim]                cwd=str(branch_dir))  # Force correct working directory[/dim]",
        "  • Must use cwd= parameter for PWD detection to work",
        "",
        "[yellow]KEY:[/yellow] AI_MAIL walks up from CWD to find *.id.json for branch identity",
        "",
        "[bold cyan]DEMONSTRATION:[/bold cyan]",
        "  [dim]/home/aipass/seed/apps/modules/create_thing.py[/dim]",
        "  [dim]/home/aipass/seed/apps/modules/test_cli_errors.py[/dim]",
        "  [dim]/home/aipass/aipass_core/cli/apps/modules/display.py[/dim]",
        "",
        "[bold cyan]REFERENCE:[/bold cyan]",
        "  [dim]/home/aipass/standards/CODE_STANDARDS/imports.md[/dim]",
        "",
        "─" * 70,
    ]

    return "\n".join(lines)
