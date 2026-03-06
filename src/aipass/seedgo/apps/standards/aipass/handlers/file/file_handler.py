"""
File Handler

Provides text file reading abstraction for modules.
Keeps direct file operations in handlers, not modules.
"""

import sys
from pathlib import Path
from typing import Optional

def read_file(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    Read text content from a file.

    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)

    Returns:
        File content as string, or None if file not found/error
        (caller module handles logging)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None

        with open(path, 'r', encoding=encoding) as f:
            return f.read()

    except Exception:
        return None


def file_exists(file_path: str) -> bool:
    """
    Check if a file exists.

    Args:
        file_path: Path to check

    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).exists()
