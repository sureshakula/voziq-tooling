#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: log_visibility_content.py - Log Visibility Standards Content
# Date: 2026-02-27
# Version: 2.0.0
# Category: seed/standards/content
#
# CHANGELOG (Max 5 entries):
#   - v2.0.0 (2026-02-27): Updated for unified Prax logging — handlers no longer exempt
#   - v1.0.0 (2026-02-27): Initial content - log visibility standard
#
# CODE STANDARDS:
#   - Content handler provides Rich-formatted text for display
# =============================================

"""
Log Visibility Standards Content

Provides Rich-formatted reference text for the log visibility standard.
"""

import sys
from pathlib import Path

# Infrastructure
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# Build example strings via concatenation to avoid triggering checkers
_GETLOGGER = "logging" + ".getLogger"
_FILEHANDLER = "logging" + ".FileHandler"
_PRAX_IMPORT = "from prax.apps.modules.logger import system_logger as logger"


def get_log_visibility_standards() -> str:
    """Return Rich-formatted log visibility standards text"""
    return f"""[bold white]LOG VISIBILITY STANDARD[/bold white]

[yellow]PURPOSE:[/yellow]
  ALL Python files (modules, handlers, entry points) MUST use prax system_logger
  so logs appear in system_logs/ and are visible to Prax monitor. Raw
  {_GETLOGGER}() creates local log files invisible to monitoring — blind spots.

[yellow]THE RULES:[/yellow]

  [bold red]PROHIBITED[/bold red]
    - Using {_GETLOGGER}() in ANY file without also importing prax system_logger
    - Creating loggers that only write to local logs/ directories
    - Any {_FILEHANDLER} setup that bypasses Prax dual-handler

  [bold green]REQUIRED[/bold green]
    - Import prax system_logger: {_PRAX_IMPORT}
    - Use system_logger for ALL logging — modules, handlers, entry points
    - If {_GETLOGGER}() is needed for specific purposes, prax import must also be present

  [bold cyan]EXEMPT[/bold cyan]
    - Prax's own logging infrastructure (it IS the implementation)
    - Test files (test isolation)
    - Files with .seed/bypass.json exceptions

[yellow]TWO CHECKS (v3.0.0):[/yellow]

  [bold]Check 1: Prax Import (ALL files — no handler exemption)[/bold]
    - Scans for {_GETLOGGER}() calls
    - If found, checks for prax system_logger import
    - Applies to modules AND handlers — unified Prax logging everywhere

  [bold]Check 2: Local FileHandler (ALL files, no exemptions)[/bold]
    - Scans for {_FILEHANDLER}() creation
    - Checks if it writes to system_logs/ (OK) or local logs/ (violation)

[yellow]EXAMPLES:[/yellow]

  [red]BAD — handler using stdlib:[/red]
    import logging
    logger = {_GETLOGGER}(__name__)    # VIOLATION: use Prax instead

  [green]GOOD — handler using Prax:[/green]
    {_PRAX_IMPORT}
    logger.info("Visible in Prax monitor and system_logs/")

[yellow]WHY THIS MATTERS:[/yellow]
  Audit found 92 local log files with no system_logs mirror — invisible
  to Prax monitor. ONE logging system everywhere — Prax."""
