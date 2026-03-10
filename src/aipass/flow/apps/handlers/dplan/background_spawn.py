# =================== AIPass ====================
# Name: background_spawn.py
# Description: Background process spawning handler
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Background Spawn Handler

Spawns a background process (e.g., post-close runner) in a new session.
Extracted from dplan_flow.py to comply with 3-tier architecture
(modules must not make direct subprocess calls).

Usage:
    from aipass.flow.apps.handlers.dplan.background_spawn import spawn_post_close
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import io


# =============================================================================
# CONFIGURATION
# =============================================================================

# Default runner script lives alongside the module that invokes it
DEFAULT_RUNNER = Path(__file__).parents[2] / "modules" / "post_close_runner.py"


# =============================================================================
# OPERATIONS
# =============================================================================

def spawn_post_close(
    runner_path: Optional[Path] = None,
    log_file_handle: Optional[io.TextIOWrapper] = None,
) -> Dict[str, Any]:
    """
    Spawn the post-close background runner in a detached session.

    Args:
        runner_path: Path to the runner script. Defaults to
                     apps/modules/post_close_runner.py.
        log_file_handle: Open file handle for stdout/stderr.
                         If None, output is discarded (DEVNULL).

    Returns:
        Dict with keys:
            success (bool): Whether the process was spawned
            pid (Optional[int]): PID of the spawned process, or None on failure
            runner (str): Path to the runner script that was invoked
            error (str): Error description if failed, empty string on success
    """
    script = runner_path or DEFAULT_RUNNER

    stdout_target = log_file_handle if log_file_handle else subprocess.DEVNULL
    stderr_target = log_file_handle if log_file_handle else subprocess.DEVNULL

    try:
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=stdout_target,
            stderr=stderr_target,
            start_new_session=True,
        )
        return {
            "success": True,
            "pid": proc.pid,
            "runner": str(script),
            "error": "",
        }
    except Exception as e:
        return {
            "success": False,
            "pid": None,
            "runner": str(script),
            "error": f"Failed to spawn background process: {e}",
        }
