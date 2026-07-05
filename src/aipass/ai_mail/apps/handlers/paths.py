# =================== AIPass ====================
# Name: paths.py
# Description: Shared path utilities for ai_mail handlers
# Version: 1.0.0
# Created: 2026-03-29
# Modified: 2026-03-29
# =============================================

"""
Shared path utilities for ai_mail handlers.

Provides repo root discovery used across all handler files.
Consolidated from 8 identical copies per DPLAN-0036 audit.
"""

import os
import sys
from pathlib import Path

from aipass.ai_mail.apps.handlers.json import json_handler

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream in (sys.stdout, sys.stderr):
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is not None:
            _reconfigure(encoding="utf-8", errors="replace")


def find_repo_root() -> Path:
    """Walk up from this file to find AIPASS_REGISTRY.json (repo root)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()


if __name__ == "__main__":
    from aipass.cli.apps.modules import console

    json_handler.log_operation("paths_introspection")
    console.print("\n" + "=" * 70)
    console.print("PATHS UTILITY")
    console.print("=" * 70)
    console.print(f"\nRepo root: {find_repo_root()}")
    console.print("\nFunctions provided:")
    console.print("  - find_repo_root() -> Path")
    console.print()
