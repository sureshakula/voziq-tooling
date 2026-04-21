# =================== AIPass ====================
# Name: hooks_ext.py
# Description: Hook Test and List Subcommands (split from hooks.py)
# Version: 1.0.0
# Created: 2026-04-21
# Modified: 2026-04-21
# =============================================

"""
Hook Test and List Subcommands

Extended subcommands for hooks.py — split out to keep hooks.py under 700 lines.

  hooks test   Run hook test suite, display per-file pass/fail table
  hooks list   Show every wired hook from project and global settings
"""

import glob as _glob
import json
from pathlib import Path

from aipass.prax import logger
from aipass.cli import console
from aipass.cli.apps.modules import warning
from aipass.seedgo.apps.handlers.file import read_lines_safe, read_text_safe
from aipass.seedgo.apps.handlers.hooks import run_pytest_file
from aipass.seedgo.apps.handlers.json import json_handler
from rich.table import Table


# =============================================================================
# SUBCOMMAND: hooks test
# =============================================================================


def cmd_hooks_test(repo_root: Path) -> None:
    """Run hook test suite, display per-file pass/fail table."""
    pattern = str(repo_root / "src" / "aipass" / "seedgo" / "tests" / "test_hooks*.py")
    test_files = sorted(_glob.glob(pattern))

    if not test_files:
        warning("No test_hooks*.py files found")
        return

    table = Table(
        title="[bold cyan][HOOKS TEST][/bold cyan] Hook Test Suite",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Test File", style="cyan", no_wrap=True)
    table.add_column("Tests", justify="right", style="yellow")
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Duration", justify="right", style="dim")
    table.add_column("Status", justify="center")

    total_passed = 0
    total_failed = 0

    for tf in test_files:
        stem = Path(tf).stem
        passed, failed, duration = run_pytest_file(Path(tf), repo_root)
        total_passed += passed
        total_failed += failed
        status = (
            "[green]PASS[/green]"
            if failed == 0 and passed > 0
            else ("[red]FAIL[/red]" if failed > 0 else "[yellow]NONE[/yellow]")
        )
        table.add_row(
            stem,
            str(passed + failed),
            str(passed),
            str(failed),
            f"{duration:.1f}s",
            status,
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold]Total:[/bold] [green]{total_passed} passed[/green]  [red]{total_failed} failed[/red]\n")
    json_handler.log_operation(
        "hooks_test_run",
        {"files": len(test_files), "total_passed": total_passed, "total_failed": total_failed},
    )


# =============================================================================
# SUBCOMMAND: hooks list — helpers
# =============================================================================


def read_settings_file(path: Path) -> dict:
    """Read and parse a settings.json file. Returns {} on failure."""
    if not path.exists():
        return {}
    text = read_text_safe(path)
    if text is None:
        logger.info("hooks_ext.py: could not read %s", path)
        return {}
    try:
        return json.loads(text)
    except Exception as exc:
        logger.info("hooks_ext.py: could not parse %s: %s", path, exc)
        return {}


def extract_hook_script(command: str) -> str:
    """Extract the Python script filename from a hook command string."""
    parts = command.split()
    for part in reversed(parts):
        if part.endswith(".py"):
            return Path(part).name
    return command[:40] if command else "(unknown)"


def _parse_version_from_lines(lines: list) -> str | None:
    """Scan lines for a Version: comment. Returns version string or None."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# Version:") or stripped.startswith("Version:"):
            return stripped.split(":", 1)[1].strip()
    return None


def read_hook_version(command: str) -> str:
    """Extract version string from a hook file's first 20 lines."""
    parts = command.split()
    for part in reversed(parts):
        if part.endswith(".py"):
            raw_lines = read_lines_safe(Path(part), n=20)
            version = _parse_version_from_lines(raw_lines)
            if version is not None:
                return version
    return "?"


def _add_hook_defs_to_table(
    table: Table,
    hook_defs: list,
    event_name: str,
    matcher: str,
    location: str,
    seen: set,
) -> int:
    """Add hook definitions to table, skipping duplicates. Returns count added."""
    count = 0
    for hook_def in hook_defs:
        if not isinstance(hook_def, dict):
            continue
        command = hook_def.get("command", "")
        if not command:
            continue
        script_name = extract_hook_script(command)
        dedup_key = (script_name, event_name, location)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        version = read_hook_version(command)
        script_path_parts = [p for p in command.split() if p.endswith(".py")]
        exists = Path(script_path_parts[0]).exists() if script_path_parts else False
        table.add_row(
            script_name,
            event_name,
            matcher[:35] if len(matcher) > 35 else matcher,
            version,
            location,
            "[green]✓[/green]" if exists else "[red]✗[/red]",
        )
        count += 1
    return count


def _populate_hooks_table(table: Table, sources: list, seen: set) -> int:
    """Populate hooks list table from settings sources. Returns row count."""
    total = 0
    for _label, path, location in sources:
        settings = read_settings_file(path)
        for event_name, entries in settings.get("hooks", {}).items():
            hook_entries = entries if isinstance(entries, list) else []
            for entry in hook_entries:
                matcher = entry.get("matcher", "*") if isinstance(entry, dict) else "*"
                hook_defs = entry.get("hooks", []) if isinstance(entry, dict) else []
                total += _add_hook_defs_to_table(table, hook_defs, event_name, matcher, location, seen)
    return total


# =============================================================================
# SUBCOMMAND: hooks list
# =============================================================================


def cmd_hooks_list(repo_root: Path) -> None:
    """Show every wired hook from both project and user-global settings."""
    global_settings_path = Path.home() / ".claude" / "settings.json"
    project_settings_path = repo_root / ".claude" / "settings.json"

    sources = [
        ("~/.claude/settings.json", global_settings_path, "global"),
        (".claude/settings.json", project_settings_path, "project"),
    ]

    table = Table(
        title="[bold cyan][HOOKS LIST][/bold cyan] Wired Hooks",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=True,
    )
    table.add_column("Hook Script", style="cyan", no_wrap=True)
    table.add_column("Event", style="yellow")
    table.add_column("Matcher", style="dim")
    table.add_column("Version", justify="center", style="green")
    table.add_column("Source", style="dim")
    table.add_column("Exists", justify="center")

    seen: set = set()
    total = _populate_hooks_table(table, sources, seen)

    console.print()
    console.print(table)
    console.print(f"\n[dim]{total} hook entries across both settings files[/dim]\n")

    json_handler.log_operation("hooks_list", {"total": total})


# =============================================================================
# DRONE ROUTING (helper module — delegates to hooks.py)
# =============================================================================


def print_introspection() -> None:
    """Print subcommand info for this helper module."""
    console.print("[bold cyan]hooks_ext[/bold cyan] — hook test and list helper")
    console.print("  [dim]Use via hooks.py: drone @seedgo hooks test | hooks list[/dim]")


def handle_command(command: str, args: list) -> bool:
    """Not a primary drone module — delegates to hooks.py for routing."""
    if not args:
        print_introspection()
        return True
    return False
