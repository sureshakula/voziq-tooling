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
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

from aipass.drone.apps.drone import main as _drone_main


def main() -> None:
    """Entry point for the `drone` CLI command."""
    sys.exit(_drone_main())


if __name__ == "__main__":
    main()
