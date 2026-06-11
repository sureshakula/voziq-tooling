# =================== AIPass ====================
# Name: path_resolver.py
# Description: Kernel-safe path resolution via openat2 RESOLVE_BENEATH
# Version: 1.0.0
# Created: 2026-06-09
# Modified: 2026-06-09
# =============================================

"""Kernel-safe path resolution via openat2 RESOLVE_BENEATH.

Re-resolves an agent-supplied path string server-side so the broker never
trusts the raw string. Uses Linux openat2(2) with RESOLVE_BENEATH |
RESOLVE_NO_SYMLINKS to guarantee the final target is strictly beneath an
allowed base directory and traverses no symlinks.

Falls back to a pure-Python per-component walk (O_NOFOLLOW openat) when
openat2 is unavailable (non-Linux, older kernels).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import struct
import sys
from pathlib import Path

from aipass.prax import logger
from aipass.drone.apps.handlers.json import json_handler

RESOLVE_BENEATH = 0x08
RESOLVE_NO_SYMLINKS = 0x04
SYS_OPENAT2 = 437
O_PATH = 0o010000000
O_NOFOLLOW = 0o0400000

_OPEN_HOW_SIZE = 24


def _openat2_available() -> bool:
    """Check if the openat2 syscall is usable on this platform."""
    return sys.platform == "linux" and os.uname().machine == "x86_64"


def _openat2(dirfd: int, pathname: bytes, flags: int, resolve: int) -> int:
    """Call openat2(2) via ctypes syscall.

    Returns an fd on success, raises OSError on failure.
    """
    open_how = struct.pack("QQQ", flags, 0, resolve)
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    result = libc.syscall(
        ctypes.c_long(SYS_OPENAT2),
        ctypes.c_int(dirfd),
        ctypes.c_char_p(pathname),
        ctypes.c_char_p(open_how),
        ctypes.c_size_t(_OPEN_HOW_SIZE),
    )
    if result < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno), pathname.decode(errors="replace"))
    return result


def resolve_beneath(base: Path, relpath: str) -> Path:
    """Resolve *relpath* strictly beneath *base*, refusing escapes and symlinks.

    Uses openat2 RESOLVE_BENEATH|RESOLVE_NO_SYMLINKS on Linux x86-64,
    falls back to a per-component O_NOFOLLOW walk otherwise.

    Returns the resolved absolute path on success.
    Raises OSError on traversal failure (escape, symlink, missing component).
    """
    json_handler.log_operation("resolve_beneath", {"base": str(base), "relpath": relpath})

    cleaned = os.path.normpath(relpath)
    if cleaned.startswith("/") or cleaned.startswith(".."):
        raise OSError(1, "Path escapes base via leading / or ..", relpath)

    parts = cleaned.split("/")
    if ".." in parts:
        raise OSError(1, "Path contains .. component", relpath)

    if _openat2_available():
        return _resolve_via_openat2(base, cleaned)
    return _resolve_via_walk(base, parts)


def _resolve_via_openat2(base: Path, cleaned: str) -> Path:
    """Resolve using the openat2 syscall with kernel-enforced containment."""
    dirfd = os.open(str(base), os.O_RDONLY | os.O_DIRECTORY)
    try:
        fd = _openat2(
            dirfd,
            cleaned.encode(),
            O_PATH,
            RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS,
        )
        try:
            resolved = Path(os.readlink(f"/proc/self/fd/{fd}"))
            logger.info("resolve_beneath: openat2 resolved %s -> %s", cleaned, resolved)
            return resolved
        finally:
            os.close(fd)
    finally:
        os.close(dirfd)


def _resolve_via_walk(base: Path, parts: list[str]) -> Path:
    """Fallback: per-component walk using O_NOFOLLOW to block symlinks."""
    current_fd = os.open(str(base), os.O_RDONLY | os.O_DIRECTORY)
    try:
        for i, component in enumerate(parts):
            if component in ("", "."):
                continue

            is_last = i == len(parts) - 1
            flags = O_PATH | O_NOFOLLOW
            if not is_last:
                flags |= os.O_DIRECTORY

            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError as exc:
                raise OSError(
                    exc.errno,
                    f"Component '{component}' failed: {exc.strerror}",
                    "/".join(parts),
                ) from exc

            os.close(current_fd)
            current_fd = next_fd

        resolved = Path(os.readlink(f"/proc/self/fd/{current_fd}"))
        logger.info("resolve_beneath: walk resolved %s -> %s", "/".join(parts), resolved)
        return resolved
    finally:
        os.close(current_fd)
