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
from typing import Optional

from aipass.prax.apps.modules.logger import system_logger as logger
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


def find_project_root(start: Path) -> Optional[Path]:
    """Walk up from *start* to find the first *_REGISTRY.json (project root).

    Returns the directory containing the registry, or None if not found.
    Stops at filesystem root.
    """
    current = start.resolve()
    for candidate in [current] + list(current.parents):
        try:
            if any(candidate.glob("*_REGISTRY.json")):
                return candidate
        except OSError as exc:
            logger.warning("[paths] find_project_root: glob failed at %s: %s", candidate, exc)
            break
    return None


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
