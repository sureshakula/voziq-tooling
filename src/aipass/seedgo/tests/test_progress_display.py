#!/usr/bin/env python3
"""
Test script for audit progress display.

Run this through drone to test if Rich Progress renders in Patrick's terminal:
    drone @seedgo test_progress

Or run directly:
    python3 src/aipass/seedgo/tests/test_progress_display.py
"""
import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn

console = Console()

# Fake branch names to simulate audit
branches = [
    "AI_MAIL", "API", "BACKUP", "CLI", "COMMONS",
    "DAEMON", "DRONE", "FLOW", "MEMORY", "PRAX",
    "SEEDGO", "SKILLS", "SPAWN", "TRIGGER"
]


def test_rich_progress():
    """Test 1: Rich Progress bar (same pattern backup uses)"""
    console.print("\n[bold cyan]Test 1: Rich Progress Bar[/bold cyan]")
    console.print("[dim]This is what backup uses — should show a moving bar[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Auditing branches...", total=len(branches))
        for branch in branches:
            progress.update(task, description=f"Auditing {branch}...")
            time.sleep(0.3)  # Simulate work
            progress.advance(task)

    console.print("[green]Done![/green]\n")


def test_rich_progress_with_results():
    """Test 2: Progress bar + print completed lines"""
    console.print("[bold cyan]Test 2: Progress + Per-Branch Results[/bold cyan]")
    console.print("[dim]Shows progress bar while processing, prints results as they complete[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning...", total=len(branches))
        for idx, branch in enumerate(branches, 1):
            progress.update(task, description=f"[cyan]{branch}[/cyan]")
            time.sleep(0.3)  # Simulate work

            # Fake score
            score = 90 + (idx % 5)
            elapsed = 0.3

            # Print result line (persists above progress bar)
            style = "green" if score >= 90 else "yellow"
            progress.console.print(
                f"  [{idx}/{len(branches)}] {branch:<12} [{style}]{score}%[/{style}] ({elapsed:.1f}s)"
            )
            progress.advance(task)

    console.print()
    console.print("[dim]Audit complete[/dim]")
    console.print()


if __name__ == "__main__":
    console.print("\n[bold]Audit Progress Display Tests[/bold]")
    console.print("[dim]Testing which Rich display method works in this terminal[/dim]\n")

    test_rich_progress()
    test_rich_progress_with_results()

    console.print("[bold green]All tests complete[/bold green]\n")
