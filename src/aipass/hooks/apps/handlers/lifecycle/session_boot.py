# =================== AIPass ====================
# Name: session_boot.py
# Version: 1.1.0
# Description: Boot wrapper — attach-if-live or start-in-tmux for Claude Code
# Branch: hooks
# Layer: apps/handlers/lifecycle
# Created: 2026-06-30
# Modified: 2026-06-30
# =============================================

"""Boot wrapper for Claude Code sessions.

When Patrick boots Claude in a branch directory, this wrapper:
  1. If already inside tmux ($TMUX set) → execs claude directly (no nesting).
  2. Checks CC-native ~/.claude/sessions/ for a live session at this cwd.
  3. If live AND hosted in a tmux session → attaches to that tmux session.
  4. If live but NOT in tmux → warns (can't inject into a plain terminal).
  5. If no live session → starts fresh inside a new tmux session.

Tmux sessions are named after the branch directory (e.g., "hooks", "devpulse").
All sessions use --permission-mode bypassPermissions (TG user can't answer prompts).
Remote visibility is preserved (tmux composes with remoteControlAtStartup).

Entry points:
  drone @hooks boot [claude args...]
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

_DEFAULT_ARGS = ["--permission-mode", "bypassPermissions"]


def _resolve_claude_binary() -> str:
    """Resolve the REAL claude binary path from PATH.

    Uses shutil.which, which searches the filesystem PATH — it does NOT see
    shell functions. So even when a claude() shell function shadows the binary,
    this finds the real one.
    """
    path = shutil.which("claude")
    if path:
        return path
    logger.error("[SESSION_BOOT] claude binary not found on PATH")
    return "claude"


def _find_live_sessions(cwd: str) -> list[dict]:
    """Find live CC sessions for the given cwd via cc_sessions module."""
    import importlib

    cc_sessions = importlib.import_module("aipass.hooks.apps.modules.cc_sessions")
    return cc_sessions.find_live_for_cwd(cwd)


def _find_tmux() -> str | None:
    """Find tmux binary on PATH."""
    return shutil.which("tmux")


def _tmux_session_exists(name: str) -> bool:
    """Check if a tmux session with the given name exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", name],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _find_tmux_session_for_pid(pid: int) -> str | None:
    """Find which tmux session hosts the given PID (as a descendant of a pane)."""
    result = subprocess.run(
        ["tmux", "list-panes", "-a", "-F", "#{pane_pid} #{session_name}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.strip().splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        pane_pid_str, session_name = parts
        try:
            pane_pid = int(pane_pid_str)
        except ValueError:
            logger.info("[SESSION_BOOT] Non-integer pane PID: %s", pane_pid_str)
            continue
        if _is_descendant(pid, pane_pid):
            return session_name
    return None


def _get_ppid(pid: int) -> int | None:
    """Get parent PID portably (Linux + macOS). Returns None on failure."""
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        logger.info("[SESSION_BOOT] ppid lookup failed for PID %d: %s", pid, exc)
    return None


def _is_descendant(target_pid: int, ancestor_pid: int) -> bool:
    """Check if target_pid is a descendant of ancestor_pid via process tree walk."""
    pid = target_pid
    for _ in range(20):
        if pid == ancestor_pid:
            return True
        if pid <= 1:
            return False
        ppid = _get_ppid(pid)
        if ppid is None:
            return False
        pid = ppid
    return False


def boot(cwd: str | None = None, extra_args: list[str] | None = None) -> dict:
    """Boot Claude Code — attach if live, else start in tmux.

    Args:
        cwd: Branch directory (defaults to current working directory).
        extra_args: Additional arguments to pass to claude (after default args).

    Returns:
        Result dict with action taken and details.
    """
    cwd = cwd or str(Path.cwd().resolve())
    branch = Path(cwd).name
    claude_bin = _resolve_claude_binary()

    defaults = _DEFAULT_ARGS if not (extra_args and "--permission-mode" in extra_args) else []

    if extra_args and "-p" in extra_args:
        logger.info("[SESSION_BOOT] Headless mode (-p) — running claude directly, no tmux")
        claude_cmd = [claude_bin] + defaults
        claude_cmd.extend(extra_args)
        os.execvp(claude_bin, claude_cmd)
        return {"exit_code": 0, "action": "direct", "reason": "headless -p mode"}

    if os.environ.get("TMUX"):
        logger.info("[SESSION_BOOT] Already inside tmux — running claude directly")
        claude_cmd = [claude_bin] + defaults
        if extra_args:
            claude_cmd.extend(extra_args)
        os.execvp(claude_bin, claude_cmd)
        return {"exit_code": 0, "action": "direct", "reason": "already in tmux"}

    tmux = _find_tmux()
    if not tmux:
        logger.error("[SESSION_BOOT] tmux not found on PATH")
        return {"exit_code": 1, "error": "tmux not found — required for session hosting"}

    live = _find_live_sessions(cwd)

    if live:
        session = live[0]
        pid = session["pid"]
        name = session.get("name", "")
        logger.info("[SESSION_BOOT] Live session found: PID %d%s", pid, f" ({name})" if name else "")

        tmux_session = _find_tmux_session_for_pid(pid)
        if tmux_session:
            logger.info("[SESSION_BOOT] Attaching to tmux session '%s'", tmux_session)
            os.execvp("tmux", ["tmux", "attach-session", "-t", tmux_session])
            return {"exit_code": 0, "action": "attached", "tmux_session": tmux_session}

        return {
            "exit_code": 1,
            "action": "warn",
            "error": (
                f"{branch} already has a live Claude session (PID {pid}) running outside tmux"
                f" — Claude allows one session per branch.\n"
                f"  • Reattach in its own terminal, OR\n"
                f"  • Reclaim it here:   kill {pid} && claude\n"
                f"  • Or bypass this wrapper:   command claude --resume"
            ),
        }

    if _tmux_session_exists(branch):
        logger.info("[SESSION_BOOT] Killing stale tmux session '%s'", branch)
        subprocess.run(["tmux", "kill-session", "-t", branch], check=False)

    claude_cmd = [claude_bin] + defaults
    if extra_args:
        claude_cmd.extend(extra_args)

    logger.info("[SESSION_BOOT] Starting fresh in tmux session '%s': %s", branch, " ".join(claude_cmd))
    os.execvp("tmux", ["tmux", "new-session", "-s", branch, "--"] + claude_cmd)
    return {"exit_code": 0, "action": "started", "tmux_session": branch}


def main() -> None:
    """CLI entry point for the boot wrapper."""
    result = boot(extra_args=sys.argv[1:] if len(sys.argv) > 1 else None)
    if result.get("exit_code", 0) != 0:
        sys.stderr.write(f"{result.get('error', 'boot failed')}\n")
        sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
