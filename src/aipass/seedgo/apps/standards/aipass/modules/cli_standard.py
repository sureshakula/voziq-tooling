"""
CLI Standards Module

Provides condensed CLI standards for AIPass branches.
Run directly or via: drone @seed cli
"""

# =================== META ====================
# Name: cli_standard.py
# Description: CLI Standards Module
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-03-05
# =============================================


import sys
from pathlib import Path
from typing import List


from aipass.prax import logger
from handlers.json import json_handler
from handlers.standards.cli_content import get_cli_standards

# Import CLI services (Rich console + display functions)
from aipass.cli import console, header


def print_introspection():
    """Display module info and connected handlers"""
    from pathlib import Path

    console.print()
    console.print("[bold cyan]CLI Standards Module[/bold cyan]")
    console.print()

    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    # Auto-discover handler files from handlers/standards/
    handlers_dir = Path(__file__).parent.parent / "handlers" / "standards"

    if handlers_dir.exists():
        # Only show files this module actually uses
        console.print("  [cyan]handlers/standards/[/cyan]")
        console.print("    [dim]- cli_content.py[/dim]")
        console.print()

    console.print("[dim]Run 'python3 cli_standard.py --help' for usage[/dim]")
    console.print()


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]CLI Standards Module[/bold cyan]")
    console.print("Demonstrates AIPass CLI patterns")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: cli, --help")
    console.print()
    console.print("  [cyan]cli[/cyan]       - Display CLI standards")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  drone @seed cli")
    console.print("  python3 cli_standard.py")
    console.print("  python3 cli_standard.py --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed cli")
    console.print()
    console.print("  [dim]# Standalone[/dim]")
    console.print("  python3 cli_standard.py")
    console.print()

    console.print("[yellow]REFERENCE:[/yellow]")
    console.print("  /home/aipass/standards/CODE_STANDARDS/cli.md")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'cli' command"""
    if command != "cli":
        return False

    # Log module usage - triggers JSON auto-creation
    json_handler.log_operation(
        "standard_displayed",
        {"command": command}
    )

    print_standard()
    return True


def print_standard():
    """Print cli standards - orchestrates handler call"""
    console.print()
    header("CLI Standards")
    console.print()
    console.print(get_cli_standards())
    console.print()
    console.print("─" * 70)
    console.print()

    # Offer to run demo (skip if non-interactive)
    try:
        response = input("Press Enter to see CLI demo examples (or 'n' to skip): ").strip().lower()
        if response != 'n':
            run_demo()
    except EOFError:
        # Non-interactive mode - skip demo silently (expected behavior)
        logger.info("[cli_standard] Non-interactive mode detected, skipping demo")


def run_demo():
    """Run the CLI layout demo"""
    import subprocess
    demo_path = str(Path(__file__).resolve().parents[3] / "cli" / "tools" / "cli_layout_demo.py")

    console.print()
    console.print("[bold cyan]Running CLI Demo...[/bold cyan]")
    console.print()

    try:
        subprocess.run(["python3", demo_path], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running demo: {e}")
        console.print(f"[red]Error running demo: {e}[/red]")
    except FileNotFoundError:
        logger.error(f"Demo file not found: {demo_path}")
        console.print(f"[yellow]Demo file not found: {demo_path}[/yellow]")


if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)

    # Handle help flag (drone compliance)
    if sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    # Confirm Prax logger connection
    logger.info("Prax logger connected to cli_standard")

    # Log standalone execution - triggers JSON auto-creation
    json_handler.log_operation(
        "standard_displayed",
        {"command": "standalone"}
    )
    print_standard()             
