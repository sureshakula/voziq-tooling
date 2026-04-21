# =================== AIPass ====================
# Name: hooks/__init__.py
# Description: Hook test runner — subprocess execution for hooks_ext module
# Version: 1.0.0
# Created: 2026-04-21
# Modified: 2026-04-21
# =============================================

"""Hook test runner handler.

Encapsulates subprocess execution so hooks_ext module stays
at the display/coordination layer.
"""

import re
import subprocess
import sys
import time
from pathlib import Path


def run_pytest_file(test_file: Path, repo_root: Path, timeout: int = 60) -> tuple[int, int, float]:
    """Run pytest on a single test file. Returns (passed, failed, duration_seconds)."""
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "--tb=no", "-q", "--no-header"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(repo_root),
    )
    duration = time.monotonic() - t0
    passed = 0
    failed = 0
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "passed" in line or "failed" in line or "error" in line.lower():
            m_passed = re.search(r"(\d+) passed", line)
            m_failed = re.search(r"(\d+) failed", line)
            m_error = re.search(r"(\d+) error", line)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                failed = int(m_failed.group(1))
            if m_error:
                failed += int(m_error.group(1))
    return passed, failed, duration
