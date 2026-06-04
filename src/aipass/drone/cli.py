# =================== AIPass ====================
# Name: cli.py
# Description: Drone CLI entry point — console_scripts wrapper
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-06-04
# =============================================

"""
Drone CLI — command-line interface for aipass.drone.

Entry point: `drone` (wired via pyproject.toml console_scripts).
Thin wrapper that delegates to apps/drone.py main().

Usage:
  drone                          Show available commands
  drone --help                   Show help
  drone --version                Show version
  drone systems                  List registered branches and modules
  drone @branch command [args]   Route command to branch
  drone @module command [args]   Route command to internal module
"""

import os
import sys

# Windows terminals default to cp1252 which can't encode Rich's Unicode
# characters (box-drawing, em dashes, arrows). Force UTF-8 before any
# imports that trigger Rich output.
#
# PYTHONUTF8 only affects *child* interpreters launched afterward — it does
# nothing for this process's already-open stdout/stderr, which were created
# with the cp1252 codec at interpreter startup. Rich writes through those
# live streams, so we must reconfigure them in place (Python 3.7+). Without
# this, `drone @branch` crashes with UnicodeEncodeError ('charmap') when it
# prints a routed branch's captured output on Windows.
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")  # for child subprocesses
    for _stream in (sys.stdout, sys.stderr):
        # getattr guard: streams replaced by a capture layer (e.g. pytest) or
        # not backed by a TextIOWrapper simply lack reconfigure — skip them.
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is not None:
            _reconfigure(encoding="utf-8", errors="replace")

from aipass.drone.apps.drone import main as _drone_main


def main() -> None:
    """Entry point for the `drone` CLI command."""
    sys.exit(_drone_main())


if __name__ == "__main__":
    main()
