# =================== AIPass ====================
# Name: monitor_info.py
# Description: Monitor Introspection & Help Display
# Version: 0.1.0
# Created: 2026-04-11
# Modified: 2026-04-11
# =============================================

"""
Monitor Info - Introspection and Help Display

Extracted from monitor.py to keep the orchestration module under size limits.
Contains pure display functions with no dependency on monitor module state.
"""

from aipass.cli.apps.modules import console
from aipass.prax.apps.handlers.json import json_handler


def print_introspection():
    """Display module introspection - shows connected handlers and architecture"""
    json_handler.log_operation("print_introspection", {"module": "monitor"})
    console.print()
    console.print("[bold cyan]PRAX Monitor Module[/bold cyan]")
    console.print()
    console.print("[yellow]Purpose:[/yellow]")
    console.print("  Mission Control for autonomous branch monitoring")
    console.print("  Unified console for file changes, logs, and module activity")
    console.print()

    console.print("[yellow]Connected Handlers (apps/handlers/monitoring/):[/yellow]")
    console.print()
    console.print("  [cyan]1. unified_stream.py[/cyan]")
    console.print("     [dim]→ print_event() - Terminal output formatting[/dim]")
    console.print()
    console.print("  [cyan]2. branch_detector.py[/cyan]")
    console.print("     [dim]→ detect_branch_from_path() - Path-to-branch mapping[/dim]")
    console.print()
    console.print("  [cyan]3. interactive_filter.py[/cyan]")
    console.print("     [dim]→ FilterState, parse_command() - Runtime filtering[/dim]")
    console.print()
    console.print("  [cyan]4. monitoring_filters.py[/cyan]")
    console.print("     [dim]→ should_monitor(), get_priority() - Event filtering[/dim]")
    console.print()
    console.print("  [cyan]5. event_queue.py[/cyan]")
    console.print("     [dim]→ MonitoringEvent, MonitoringQueue - Event buffering[/dim]")
    console.print()
    console.print("  [cyan]6. module_tracker.py[/cyan]")
    console.print("     [dim]→ ModuleTracker - Module execution tracking[/dim]")
    console.print()
    console.print("  [cyan]7. file watcher (threaded)[/cyan]")
    console.print("     [dim]→ Real-time file change detection using watchdog[/dim]")
    console.print("     [green]STATUS: Active - monitors ECOSYSTEM_ROOT recursively[/green]")
    console.print()
    console.print("  [cyan]8. log monitor (threaded)[/cyan]")
    console.print("     [dim]→ Log stream processing from SYSTEM_LOGS_DIR[/dim]")
    console.print("     [green]STATUS: Active - watches *.log files for new entries[/green]")
    console.print()

    console.print("[dim]Run 'drone @prax monitor --help' for usage[/dim]")
    console.print()


def print_help():
    """Drone-compliant help output - command syntax and examples"""
    console.print()
    console.print("[bold cyan]PRAX Monitor - Unified Branch Monitoring[/bold cyan]")
    console.print()

    console.print("[yellow]Commands:[/yellow]")
    console.print()
    console.print("  [cyan]drone @prax monitor[/cyan]")
    console.print("    Show module introspection")
    console.print()
    console.print("  [cyan]drone @prax monitor run[/cyan]")
    console.print("    Start monitoring all branches")
    console.print()
    console.print("  [cyan]drone @prax monitor run all[/cyan]")
    console.print("    Explicit all-branches monitoring")
    console.print()
    console.print("  [cyan]drone @prax monitor run [branches][/cyan]")
    console.print("    Monitor specific branches (comma-separated)")
    console.print("    Example: drone @prax monitor run seedgo,cli,flow")
    console.print()
    console.print("  [cyan]drone @prax monitor --help[/cyan]")
    console.print("    Show this help")
    console.print()

    console.print("[yellow]Interactive Mode Commands:[/yellow]")
    console.print()
    console.print("  [cyan]help[/cyan]          Show available commands")
    console.print("  [cyan]status[/cyan]        Display current monitoring state")
    console.print("  [cyan]filter [branches][/cyan]  Adjust branch filter")
    console.print("  [cyan]quit/exit[/cyan]     Stop monitoring")
    console.print()

    console.print("[yellow]Examples:[/yellow]")
    console.print()
    console.print("  [dim]# Monitor all branches[/dim]")
    console.print("  $ drone @prax monitor run")
    console.print()
    console.print("  [dim]# Monitor specific branches[/dim]")
    console.print("  $ drone @prax monitor run seedgo,cli,flow")
    console.print()
