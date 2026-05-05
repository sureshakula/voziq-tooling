# =================== AIPass ====================
# Name: progress.py
# Description: Rich progress and glyph helpers for aipass doctor
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-16
# =============================================

"""
Rich progress and glyph helpers for aipass doctor.

Provides status glyphs and progress spinners used by doctor checks.
No bare print() — all output via logger or caller's console.
"""

from __future__ import annotations

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
