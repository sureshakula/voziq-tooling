# =================== AIPass ====================
# Name: progress.py
# Description: Rich progress and glyph helpers for aipass doctor + init
# Version: 1.1.0
# Created: 2026-04-16
# Modified: 2026-07-05
# =============================================

"""
Rich progress and glyph helpers for aipass doctor.

Provides status glyphs and progress spinners used by doctor checks.
No bare print() — all output via logger or caller's console.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from rich.progress import Progress, SpinnerColumn, TextColumn

from aipass.aipass.apps.handlers.json import json_handler
from aipass.prax import logger

# =============================================================================
# GLYPHS
# =============================================================================

GLYPH_PASS = "[green]✓[/green]"
GLYPH_WARN = "[yellow]![/yellow]"
GLYPH_FAIL = "[red]✗[/red]"


# =============================================================================
# PROGRESS FACTORY
# =============================================================================


def make_doctor_progress() -> Progress:
    """Return a transient spinner progress bar for doctor checks.

    Returns:
        Progress instance with spinner + description columns.
    """
    logger.info("[progress] creating doctor progress bar")
    json_handler.log_operation("make_doctor_progress", {})
    return Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        transient=True,
    )


@contextmanager
def activity_spinner(description: str) -> Iterator[Progress]:
    """Transient spinner for a blocking, non-streaming action.

    Wrap Python work that would otherwise look frozen — scaffold build, ping
    sweep — so the user sees it is alive. Do NOT wrap a subprocess that streams
    its own output to the terminal (installer, spawn): the two renderers fight.
    Yields the Progress so a caller can retitle the task mid-flight if needed.

    Args:
        description: What is happening, e.g. "Building project scaffold…".
    """
    logger.info("[progress] activity spinner: %s", description)
    json_handler.log_operation("activity_spinner", {"description": description})
    prog = Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True)
    with prog:
        prog.add_task(description, total=None)
        yield prog


# =============================================================================
# CHECK FORMATTER
# =============================================================================


def format_check(
    label: str,
    glyph: str,
    detail: str = "",
    remediation: str = "",
) -> str:
    """Format a single doctor check line as Rich markup.

    Args:
        label: Check name (e.g. "python").
        glyph: One of GLYPH_PASS / GLYPH_WARN / GLYPH_FAIL.
        detail: Optional detail appended after the label (e.g. "3.11.5").
        remediation: Optional remediation hint shown indented on next line.

    Returns:
        Rich markup string ready for console.print().
    """
    parts: list[str] = [f"  {glyph} [bold]{label}[/bold]"]
    if detail:
        parts.append(f" [dim]{detail}[/dim]")
    line = "".join(parts)

    if remediation:
        indent = "      "
        line = f"{line}\n{indent}[dim yellow]{remediation}[/dim yellow]"

    return line


def render_step_header(current: int, total: int, label: str, width: int = 18) -> str:
    """Render a one-line stage header with an inline progress bar.

    Example: 'Step 3/10 [██████░░░░░░░░░░░░] — User profile'. Pure formatting —
    a static string, so it composes with the interactive prompts between stages
    (a live Rich bar would have to stop/start around every input()).

    Args:
        current: 1-based index of the stage now starting.
        total: Total number of stages (clamps to >= 1).
        label: Human label for the stage.
        width: Character width of the bar.

    Returns:
        Rich markup string ready for console.print().
    """
    total = max(total, 1)
    current = max(0, min(current, total))
    filled = round(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    return f"[bold cyan]Step {current}/{total}[/bold cyan] [green]{bar}[/green] — [bold]{label}[/bold]"
