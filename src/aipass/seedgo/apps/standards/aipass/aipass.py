#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: seed.py - Seed Branch Entry Point [SHOWROOM]
# Date: 2025-11-13
# Version: 0.2.0
# Category: seed
#
# CHANGELOG (Max 5 entries):
#   - v0.2.0 (2025-11-13): Drone compliance - argparse help, CLI services, command routing
#   - v0.1.0 (2025-11-12): Showroom structure - demonstrates architecture
#
# CODE STANDARDS:
#   - This is a SHOWROOM/MODEL - demonstrates proper branch structure
#   - Not functional - shows how pieces connect
# =============================================

"""
Seed Branch - Showroom/Model Branch

PURPOSE: Demonstrates proper AIPass branch architecture without functional code.
Like a model home - shows structure, connections, imports, but doesn't actually work.

ARCHITECTURE:
- Entry point auto-discovers modules
- Modules orchestrate workflow by calling handlers
- Handlers implement domain-specific business logic
"""

import os
import sys
from pathlib import Path
from typing import List, Any
import importlib

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

# AIPASS_ROOT pattern - always Path.home(), never hardcode
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))

# Also add /home/aipass so seed package is importable
sys.path.insert(0, str(Path.home()))

# Prax logger import - system-wide logging (oldest module, always reliable)
from prax.apps.modules.logger import system_logger as logger

# CLI services for formatted output
from cli.apps.modules import console, header
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns

# JSON handler for seed tracking
from seed.apps.handlers.json import json_handler

# =============================================================================
# INTROSPECTION DISPLAY
# =============================================================================

def print_introspection():
    """Display discovered modules and handlers"""
    console.print()
    console.print("[bold cyan]Seed - System Education Evolution Development[/bold cyan]")
    console.print()
    console.print("[dim]AIPass Code Standards Showroom[/dim]")
    console.print()

    # Discover modules
    modules = discover_modules()

    console.print(f"[yellow]Discovered Modules:[/yellow] {len(modules)}")
    console.print()

    for module in modules:
        module_name = module.__name__.split('.')[-1]
        console.print(f"  [cyan]•[/cyan] {module_name}")

    console.print()
    console.print("[dim]Run 'python3 seed.py --help' for usage information[/dim]")
    console.print()


# =============================================================================
# DRONE COMPLIANCE - HELP SYSTEM
# =============================================================================

def print_help():
    """Display Rich-formatted help - Seed showpiece!"""

    console.print()

    # =========================================================================
    # RICH FORMATTING TIP: Use header() function for main titles
    # header() creates a bordered box automatically (imported from cli.apps.modules)
    # =========================================================================
    header("Seed - System Education Evolution Development")

    console.print()

    # RICH FORMATTING TIP: [dim] makes text appear dimmed/grayed out
    console.print("[dim]Your guide to AIPass architecture patterns and standards[/dim]")
    console.print()
    console.print("─" * 70)  # Separator line (matches handler style)
    console.print()

    # =========================================================================
    # RICH FORMATTING TIP: Match handler style - simple [bold cyan]LABEL:[/bold cyan] format
    # NO decorative borders (═══), just clean headers like handlers use
    # =========================================================================
    console.print("[bold cyan]WHAT IS SEED?[/bold cyan]")
    console.print()
    console.print("Seed is the [bold]AIPass Code Standards Showroom[/bold] - a reference branch that:")
    # RICH FORMATTING TIP: Use [green]✓[/green] for checkmarks in lists
    console.print("  [green]✓[/green] Demonstrates proper AIPass architecture patterns")
    console.print("  [green]✓[/green] Provides [green]19 queryable code standards[/green] via modules")
    console.print("  [green]✓[/green] Serves as a living example for other branches to follow")
    console.print()

    # =========================================================================
    # RICH FORMATTING TIP: Tables are powerful for structured data
    # Create with Table(), add columns, add rows, then print
    # =========================================================================
    console.print("[bold cyan]AVAILABLE STANDARDS (19):[/bold cyan]")
    console.print()

    # RICH FORMATTING TIP: Table styling - show_header, header_style, border_style
    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Command", style="green")  # Column styling
    table.add_column("Standard", style="white")
    table.add_column("Description", style="dim")

    table.add_row("architecture", "Architecture", "3-layer pattern, handler independence")
    table.add_row("cli", "CLI", "Dual approach (interactive + arguments)")
    table.add_row("imports", "Imports", "Import order, AIPASS_ROOT pattern")
    table.add_row("handlers", "Handlers", "File sizes, domain organization")
    table.add_row("modules", "Modules", "handle_command(), orchestration")
    table.add_row("naming", "Naming", "Path = context, name = action")
    table.add_row("json_structure", "JSON Structure", "Three-JSON pattern")
    table.add_row("error_handling", "Error Handling", "Fail honestly, CLI service")
    table.add_row("documentation", "Documentation", "META headers, docstrings")
    table.add_row("testing", "Testing", "Error handling, edge cases")
    table.add_row("encapsulation", "Encapsulation", "Cross-branch import boundaries")
    table.add_row("trigger", "Trigger", "Event bus patterns, inline ops")
    table.add_row("log_level", "Log Level", "ERROR vs WARNING hygiene")
    table.add_row("cli_flags", "CLI Flags", "Universal --version, --help flags")
    table.add_row("log_handler", "Log Handler", "RotatingFileHandler required, no raw handlers")
    table.add_row("log_visibility", "Log Visibility", "Prax system_logger required, no raw getLogger")
    table.add_row("permission_flags", "Permission Flags", "Only --permission-mode bypassPermissions")

    # RICH FORMATTING TIP: Print the table after adding all rows
    console.print(table)
    console.print()
    console.print("─" * 70)
    console.print()

    # =========================================================================
    # RICH FORMATTING TIP: Columns layout for side-by-side content
    # Columns([item1, item2, item3], equal=True, expand=True)
    # =========================================================================
    console.print("[bold cyan]USAGE:[/bold cyan]")
    console.print()

    usage_examples = [
        "[yellow]Quick Reference:[/yellow]\n  [dim]python3 seed.py architecture[/dim]\n  [dim]python3 seed.py imports[/dim]",
        "[yellow]Via Drone:[/yellow]\n  [dim]drone @seed cli[/dim]\n  [dim]drone @seed error_handling[/dim]",
        "[yellow]With Help Flag:[/yellow]\n  [dim]python3 seed.py naming --help[/dim]\n  [dim]drone @seed handlers --help[/dim]"
    ]

    # RICH FORMATTING TIP: Columns creates side-by-side layout
    console.print(Columns(usage_examples, equal=True, expand=True))
    console.print()
    console.print("─" * 70)
    console.print()

    # =========================================================================
    # =========================================================================
    # RICH FORMATTING TIP: Panels are good for highlighted content blocks
    # Panel(content, border_style="color", padding=(top/bottom, left/right))
    # =========================================================================
    console.print("[bold cyan]AUTOMATED STANDARDS CHECKER (NEW!):[/bold cyan]")
    console.print()

    checker_text = """[bold green]Check your code automatically:[/bold green]

  [yellow]Command:[/yellow]  [dim]python3 seed.py checklist <file.py>[/dim]

  [bold]What it does:[/bold]
  • Checks 19/19 standards automatically (95%+ accuracy - v0.3.0 false positives eliminated)
  • Scores your file 0-100 on each standard
  • Shows specific violations with line numbers
  • Fast - runs in seconds

  [bold]Example:[/bold]
  [dim]python3 seed.py checklist apps/modules/my_module.py[/dim]"""

    console.print(Panel(checker_text, border_style="yellow", padding=(1, 2)))
    console.print()

    # =========================================================================
    # BRANCH AUDIT
    # =========================================================================
    console.print("[bold cyan]BRANCH-WIDE AUDIT (NEW!):[/bold cyan]")
    console.print()

    audit_text = """[bold green]Check all branches at once:[/bold green]

  [yellow]Command:[/yellow]  [dim]python3 seed.py audit[/dim]

  [bold]What it does:[/bold]
  • Scans all 11 branches automatically
  • Shows compliance dashboard for entire system
  • Identifies top improvement areas
  • System-wide health at a glance

  [bold]Examples:[/bold]
  [dim]python3 seed.py audit              # Full audit (all branches, all files)[/dim]
  [dim]python3 seed.py audit drone        # Audit specific branch[/dim]
  [dim]python3 seed.py audit --show-bypasses  # Show all bypassed files[/dim]
  [dim]python3 seed.py audit drone --bypasses # Bypasses for specific branch[/dim]"""

    console.print(Panel(audit_text, border_style="cyan", padding=(1, 2)))
    console.print()

    # =========================================================================
    # SYNC VERIFICATION
    # =========================================================================
    console.print("[bold cyan]SYNC VERIFICATION (NEW!):[/bold cyan]")
    console.print()

    verify_text = """[bold green]Check Seed's internal documentation consistency:[/bold green]

  [yellow]Command:[/yellow]  [dim]python3 seed.py verify[/dim]

  [bold]What it does:[/bold]
  • Scans for stale/deprecated patterns
  • Checks file freshness
  • Verifies help text consistency

  [bold]Example:[/bold]
  [dim]python3 seed.py verify[/dim]"""

    console.print(Panel(verify_text, border_style="magenta", padding=(1, 2)))
    console.print()
    console.print("─" * 70)
    console.print()

    console.print("[bold cyan]FOR BRANCHES USING SEED:[/bold cyan]")
    console.print()

    workflow_text = """[bold]When building features, query Seed for standards:[/bold]

  [green]✓[/green] Starting new module?      → [dim]seed modules[/dim]
  [green]✓[/green] Adding handlers?          → [dim]seed handlers[/dim]
  [green]✓[/green] Naming files/functions?   → [dim]seed naming[/dim]
  [green]✓[/green] Error handling?           → [dim]seed error_handling[/dim]
  [green]✓[/green] Imports pattern?          → [dim]seed imports[/dim]
  [green]✓[/green] JSON structure?           → [dim]seed json_structure[/dim]"""

    # RICH FORMATTING TIP: Panel wraps content in a bordered box
    console.print(Panel(workflow_text, border_style="green", padding=(1, 2)))
    console.print()
    console.print("─" * 70)
    console.print()

    # =========================================================================
    # IMPORTANT NOTE FOR BRANCHES
    # =========================================================================
    console.print("[bold cyan]A NOTE ON STANDARDS CHECKING:[/bold cyan]")
    console.print()

    note_text = """[bold yellow]Seed is actively evolving.[/bold yellow]

  The standards checkers are continuously improving. If you encounter a
  violation that seems like a [bold]false positive[/bold]:

  [green]✓[/green] Trust your judgment - if your code is correct, it's correct
  [green]✓[/green] Report it - your feedback helps improve the checkers
  [green]✓[/green] Don't change correct code to satisfy a flawed check

  [dim]Some edge cases we're still refining:[/dim]
  • Documentation handlers that legitimately need CLI services
  • Branch-specific patterns that differ from the standard model
  • Complex structures that look like business logic but aren't

  [bold]Your feedback drives improvement.[/bold] Questions? Ask via ai_mail."""

    console.print(Panel(note_text, border_style="yellow", padding=(1, 2)))
    console.print()
    console.print("─" * 70)
    console.print()

    # Simple header style (matching handlers)
    console.print("[bold cyan]FULL DOCUMENTATION:[/bold cyan]")
    console.print()
    # RICH FORMATTING TIP: Use [yellow] for labels, [dim] for paths
    console.print("  [yellow]Standards (markdown):[/yellow]  [dim]/home/aipass/standards/CODE_STANDARDS/[/dim]")
    console.print("  [yellow]Handlers (condensed):[/yellow]  [dim]/home/aipass/seed/apps/handlers/standards/[/dim]")
    console.print("  [yellow]Modules (queryable):[/yellow]   [dim]/home/aipass/seed/apps/modules/[/dim]")
    console.print()
    console.print("─" * 70)
    console.print()

    # RICH FORMATTING TIP: Use [bold] for emphasis without color
    console.print("[bold]TIP:[/bold] Each standard has two versions:")
    console.print("  [dim]•[/dim] Handler = quick reference (~100 lines, Rich formatted)")
    console.print("  [dim]•[/dim] Markdown = comprehensive docs (full details)")
    console.print()
    console.print("─" * 70)
    console.print()

    # RICH FORMATTING TIP: Commands line required for drone discovery
    # This is how drone finds available commands - keep [dim] style
    console.print("[dim]Commands: architecture, cli, documentation, encapsulation, error_handling, handlers, imports, json_structure, log_level, log_handler, modules, naming, permission_flags, testing, trigger, checklist, audit, verify, diagnostics, readme, help, --help[/dim]")
    console.print()


# =============================================================================
# MODULE DISCOVERY
# =============================================================================

MODULES_DIR = Path(__file__).parent / "modules"

def discover_modules() -> List[Any]:
    """
    Auto-discover modules in modules/ directory

    Pattern from Cortex: Any .py file in modules/ that implements handle_command()
    gets automatically discovered and registered.

    Returns:
        List of module objects with handle_command() method
    """
    modules = []

    if not MODULES_DIR.exists():
        return modules

    for file_path in MODULES_DIR.glob("*.py"):
        if file_path.name.startswith("_"):  # Skip __init__.py, __pycache__, etc.
            continue

        module_name = f"seed.apps.modules.{file_path.stem}"

        try:
            module = importlib.import_module(module_name)

            # Duck typing: If it has handle_command(), it's a module
            if hasattr(module, 'handle_command'):
                modules.append(module)
                logger.info(f"Discovered module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")

    return modules


def route_command(command: str, args: List[str], modules: List[Any]) -> bool:
    """
    Route command to appropriate module

    Pattern: Each module's handle_command() returns True if it handled the command

    Args:
        command: Command name (e.g., 'create', 'update', 'delete')
        args: Additional arguments
        modules: List of discovered modules

    Returns:
        True if command was handled, False otherwise
    """
    for module in modules:
        try:
            if module.handle_command(command, args):
                return True
        except BrokenPipeError:
            raise
        except Exception as e:
            logger.error(f"Module {module.__name__} error: {e}")

    return False


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point - routes commands or shows help"""

    # Parse arguments
    args = sys.argv[1:]

    # Show introspection when run without arguments
    if len(args) == 0:
        print_introspection()
        json_handler.log_operation("seed_introspection_displayed", {"trigger": "no_args"})
        return

    # Show help only for explicit help flags
    if args[0] in ['--help', '-h', 'help']:
        print_help()
        json_handler.log_operation("seed_help_displayed", {"trigger": args[0]})
        return

    # Show version
    if args[0] in ['--version', '-V']:
        console.print("SEED v0.2.0")
        return

    # Command provided - try to route to modules
    modules = discover_modules()
    command = args[0]
    remaining_args = args[1:] if len(args) > 1 else []

    # Log seed command attempt
    json_handler.log_operation(
        "seed_command_attempted",
        {"command": command, "modules_discovered": len(modules)}
    )

    if route_command(command, remaining_args, modules):
        return  # Module handled it successfully
    else:
        console.print()
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print()
        console.print("Run [dim]python3 seed.py --help[/dim] for available commands")
        console.print()
        return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\nOperation cancelled by user")
        sys.exit(0)
    except BrokenPipeError:
        # Pipe closed by caller (e.g. drone capturing output) - not an error
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(0)
    except Exception as e:
        logger.error(f"Seed entry point error: {e}", exc_info=True)
        console.print(f"\n❌ Error: {e}")
        sys.exit(1)
