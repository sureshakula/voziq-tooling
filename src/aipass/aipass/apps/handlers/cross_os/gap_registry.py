# =================== AIPass ====================
# Name: gap_registry.py
# Description: Live-parse the cross-OS gap registry and filter by platform
# Version: 1.0.0
# Created: 2026-07-02
# Modified: 2026-07-02
# =============================================

"""Cross-OS gap registry parser — Layer-3-lite pre-flight source.

Live-reads ``tests/CROSS_OS_TESTING.md`` (read-only to @aipass), parses the
"Known cross-OS gap registry" markdown table, and filters rows to the running
platform. This is a *machine pre-flight* — it surfaces tracked OS-specific gaps
for the box the user is on. It NEVER claims the checklist's human acceptance
green ("you watched it work on that OS").

Fail-to-error contract: if the doc is missing, the section is absent, or no data
rows can be parsed, functions raise ``CrossOsGapError`` — they never silently
return "no gaps". Callers must surface the error as a WARN/FAIL, not swallow it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, NamedTuple

from aipass.prax import logger
from aipass.aipass.apps.handlers.json import json_handler

# Path of the source-of-truth doc, relative to the repo root.
DOC_RELATIVE = Path("tests") / "CROSS_OS_TESTING.md"

# Case-insensitive marker identifying the registry section header line.
_SECTION_MARKER = "known cross-os gap registry"

# Expected column count in the registry table: # | Gap | OS | Symptom | Owner | Status
_EXPECTED_COLUMNS = 6


class CrossOsGapError(RuntimeError):
    """Raised when the cross-OS gap registry cannot be located or parsed."""


class CrossOsGap(NamedTuple):
    """One row of the Known cross-OS gap registry table."""

    number: str
    gap: str
    os: str
    symptom: str
    owner: str
    status: str


def find_gap_doc(start: Path | None = None) -> Path:
    """Search upward from ``start`` (or this file) for ``tests/CROSS_OS_TESTING.md``.

    Portable — derives the repo root by walking ancestors rather than hardcoding
    an absolute path.

    Raises:
        CrossOsGapError: if the doc is not found in any ancestor directory.
    """
    base = (start or Path(__file__)).resolve()
    for parent in [base, *base.parents]:
        candidate = parent / DOC_RELATIVE
        if candidate.is_file():
            return candidate
    raise CrossOsGapError(f"cross-OS testing doc not found (searched upward from {base} for {DOC_RELATIVE})")


def parse_gap_registry(text: str) -> List[CrossOsGap]:
    """Parse the 'Known cross-OS gap registry' table out of the doc text.

    Only rows whose first cell begins with a digit are treated as data rows,
    which naturally skips the header and the ``|---|`` separator.

    Raises:
        CrossOsGapError: if the section is missing or no data rows parse.
    """
    lines = text.splitlines()

    section_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#") and _SECTION_MARKER in line.lower():
            section_idx = i
            break
    if section_idx is None:
        raise CrossOsGapError("'Known cross-OS gap registry' section not found in doc")

    gaps: List[CrossOsGap] = []
    for line in lines[section_idx + 1 :]:
        stripped = line.strip()
        # Stop at the next top-level section.
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < _EXPECTED_COLUMNS:
            continue
        number = cells[0]
        # Skip header ("#") and separator ("---") rows — data rows start with a digit.
        if not number or not number[0].isdigit():
            continue
        gaps.append(
            CrossOsGap(
                number=number,
                gap=cells[1],
                os=cells[2],
                symptom=cells[3],
                owner=cells[4],
                status=cells[5],
            )
        )

    if not gaps:
        raise CrossOsGapError("gap registry table found but no data rows could be parsed")
    return gaps


def load_gaps(start: Path | None = None) -> List[CrossOsGap]:
    """Locate, read, and parse the full gap registry.

    Raises:
        CrossOsGapError: on missing/unreadable doc or unparseable table.
    """
    doc = find_gap_doc(start)
    try:
        raw = doc.read_text(encoding="utf-8")
    except OSError as exc:
        raise CrossOsGapError(f"cross-OS testing doc unreadable at {doc}: {exc}") from exc
    logger.info("[cross_os] parsing gap registry from %s", doc)
    return parse_gap_registry(raw)


def os_matches(os_cell: str, platform_name: str) -> bool:
    """Return True if an OS cell applies to ``platform_name`` (a ``sys.platform`` value).

    Mapping (case-insensitive): 'all' matches every platform; 'win' matches
    win32; 'mac' matches darwin. So 'Win/mac' matches both win32 and darwin.
    """
    cell = os_cell.lower()
    if "all" in cell:
        return True
    if platform_name == "win32":
        return "win" in cell
    if platform_name == "darwin":
        return "mac" in cell
    return False


def gaps_for_platform(platform_name: str | None = None, start: Path | None = None) -> List[CrossOsGap]:
    """Return only the gap rows relevant to ``platform_name`` (defaults to ``sys.platform``).

    Raises:
        CrossOsGapError: on any load/parse failure (never silently empty).
    """
    plat = platform_name or sys.platform
    gaps = load_gaps(start)
    relevant = [g for g in gaps if os_matches(g.os, plat)]
    json_handler.log_operation(
        "cross_os_gap_lookup",
        {"platform": plat, "total": len(gaps), "relevant": len(relevant)},
    )
    return relevant
