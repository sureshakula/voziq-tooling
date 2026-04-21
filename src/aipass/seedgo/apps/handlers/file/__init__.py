# File handlers package
# =================== AIPass ====================
# Name: file/__init__.py
# Description: File I/O handler — centralises open() calls for modules
# Version: 1.0.0
# Created: 2026-04-21
# Modified: 2026-04-21
# =============================================

"""File I/O handler.

Modules must not call open() directly. Use these helpers instead.
"""

from pathlib import Path


def read_text_safe(path: Path, encoding: str = "utf-8") -> str | None:
    """Read a text file. Returns None on any OSError."""
    try:
        with open(path, encoding=encoding) as fh:
            return fh.read()
    except OSError:
        return None


def read_lines_safe(path: Path, n: int = 0, encoding: str = "utf-8") -> list[str]:
    """Read up to n lines from a file (0 = all). Returns [] on any OSError."""
    try:
        with open(path, encoding=encoding) as fh:
            if n > 0:
                return [fh.readline() for _ in range(n)]
            return fh.readlines()
    except OSError:
        return []


def write_text_safe(path: Path, text: str, encoding: str = "utf-8") -> bool:
    """Write text to a file. Returns True on success, False on OSError."""
    try:
        path.write_text(text, encoding=encoding)
        return True
    except OSError:
        return False
