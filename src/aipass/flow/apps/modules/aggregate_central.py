# =================== AIPass ====================
# Name: aggregate_central.py
# Description: Aggregate Central Plans Module
# Version: 1.3.0
# Created: 2025-11-30
# Modified: 2025-11-30
# =============================================

"""
Aggregate Central Plans Module

Thin orchestrator for central plans aggregation.
All business logic delegated to handlers/plan/aggregate_ops.py.

Features:
- Validates all plans in branches.* sections have files on disk
- Auto-closes plans with missing files in their branch registries
- Aggregates active plans from all branches into top-level active_plans array
- Builds recently_closed array from all branches
- Updates statistics across all branches
- Preserves unknown branch sections

Usage:
    from aipass.flow.apps.modules.aggregate_central import aggregate_central
    success = aggregate_central()

Standalone:
    python3 apps/modules/aggregate_central.py aggregate
    python3 apps/modules/aggregate_central.py aggregate --heal
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[3]  # file.py -> modules/ -> apps/ -> flow/ -> aipass/
FLOW_ROOT = _PKG_ROOT / "flow"

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.cli.apps.modules import console

# Implementation handler
from aipass.flow.apps.handlers.plan.aggregate_ops import aggregate_central_impl

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "aggregate_central"


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains AIPASS_REGISTRY.json)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()


_REPO_ROOT = _find_repo_root()
AI_CENTRAL_DIR = _REPO_ROOT / ".ai_central"
CENTRAL_FILE = AI_CENTRAL_DIR / "PLANS.central.json"


# =============================================
# MAIN AGGREGATION FUNCTION (thin orchestrator)
# =============================================

def aggregate_central(heal: bool = True) -> bool:
    """Aggregate and validate central plans (thin orchestrator)

    Delegates all business logic to aggregate_ops handler.

    Args:
        heal: If True, auto-close plans with missing files in their registries

    Returns:
        True on success, False on failure
    """
    return aggregate_central_impl(
        heal=heal,
        central_file=CENTRAL_FILE,
        central_dir=AI_CENTRAL_DIR,
    )


# =============================================
# DISPLAY FUNCTIONS
# =============================================

def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("aggregate_central Module")
    console.print("Thin orchestrator for central plans aggregation and self-healing validation")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/plan/")
    console.print("    - aggregate_ops.py (aggregate_central_impl — aggregation and healing logic)")
    console.print()


def print_help():
    """Print help information for aggregate_central module"""
    console.print()
    console.print("[bold cyan]aggregate_central - Central Plans Aggregator[/bold cyan]")
    console.print()
    console.print("[yellow]DESCRIPTION:[/yellow]")
    console.print("  Self-healing central aggregator for PLANS.central.json that validates")
    console.print("  file existence and rebuilds the active_plans list.")
    console.print()
    console.print("[yellow]FEATURES:[/yellow]")
    console.print("  • Validates all plans in branches have files on disk")
    console.print("  • Auto-closes plans with missing files in their branch registries")
    console.print("  • Aggregates active plans from all branches into central list")
    console.print("  • Builds recently_closed array from all branches")
    console.print("  • Updates statistics across all branches")
    console.print()
    console.print("[yellow]USAGE:[/yellow]")
    console.print("  python3 aggregate_central.py aggregate [options]")
    console.print("  python3 aggregate_central.py --help")
    console.print()
    console.print("[yellow]OPTIONS:[/yellow]")
    console.print("  --heal      Enable auto-closing of missing plans (default)")
    console.print("  --no-heal   Disable auto-closing (validation only)")
    console.print()
    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  # Aggregate with healing (default)")
    console.print("  python3 aggregate_central.py aggregate")
    console.print()
    console.print("  # Aggregate with explicit healing")
    console.print("  python3 aggregate_central.py aggregate --heal")
    console.print()
    console.print("  # Aggregate without healing (validation only)")
    console.print("  python3 aggregate_central.py aggregate --no-heal")
    console.print()


# =============================================
# COMMAND INTERFACE
# =============================================

def handle_command(command: str, args: List[str]) -> bool:
    """Handle module commands

    Args:
        command: Command name ('aggregate' or 'aggregate_central')
        args: Additional arguments (e.g., ['--heal'])

    Returns:
        True if command handled successfully
    """
    if command == "aggregate":
        # Check for --heal flag (default is True)
        heal = True
        if "--no-heal" in args:
            heal = False

        return aggregate_central(heal=heal)

    return False


# =============================================
# MAIN ENTRY POINT
# =============================================

def main():
    """Main entry point for standalone execution"""
    # Handle help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    if len(sys.argv) < 2:
        console.print(f"Usage: python3 {sys.argv[0]} <command> [options]")
        console.print("Commands:")
        console.print("  aggregate         - Aggregate central plans (with healing)")
        console.print("  aggregate --heal  - Aggregate with explicit healing")
        console.print("  aggregate --no-heal - Aggregate without healing")
        console.print()
        console.print("Run with --help for detailed information")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    success = handle_command(command, args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
