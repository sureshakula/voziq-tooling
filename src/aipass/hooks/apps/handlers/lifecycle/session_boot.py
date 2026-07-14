# =================== AIPass ====================
# Name: session_boot.py
# Version: 2.0.0
# Description: Boot wrapper — attach-first menu for Claude Code sessions
# Branch: hooks
# Layer: apps/handlers/lifecycle
# Created: 2026-06-30
# Modified: 2026-07-13
# =============================================

"""Boot wrapper for Claude Code sessions.

When Patrick runs `claude` in a branch directory, this wrapper presents a menu:

Live session exists:
  devpulse — live chat: PID 773292 · c624cbcd · background · 2h old
    [Enter]  resume this chat
    [n]      start new chat   (closes the one above first)
    [c]      close it and exit

No live session:
  devpulse — no live chat
    [Enter]  continue last chat
    [n]      new chat

Special cases:
  - Already inside tmux → execs claude directly (no nesting).
  - Headless (-p flag) → execs claude directly.

Entry points:
  drone @hooks boot [claude args...]
"""

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

_DEFAULT_ARGS = ["--permission-mode", "bypassPermissions"]


def _resolve_claude_binary() -> str:
    """Resolve the REAL claude binary path from PATH."""
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


def _format_age(session: dict) -> str:
    """Format session age from its start time."""
    started = session.get("startedAt") or session.get("started", "")
    if not started:
        return ""
    try:
        from datetime import datetime, timezone

        if isinstance(started, (int, float)):
            start_dt = datetime.fromtimestamp(started / 1000, tz=timezone.utc)
        else:
            start_dt = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        delta = datetime.now(tz=timezone.utc) - start_dt
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    except Exception:
        return ""


def _session_short_id(session: dict) -> str:
    """Extract first 8 chars of sessionId."""
    return str(session.get("sessionId", ""))[:8]


def _session_label(session: dict, branch: str) -> str:
    """Format a session's one-line label per P6: PID · short-id · kind · age."""
    pid = session.get("pid", "?")
    short_id = _session_short_id(session)
    kind = session.get("kind", "unknown")
    age = _format_age(session)
    age_str = f" · {age} old" if age else ""
    return f"PID {pid} · {short_id} · {kind}{age_str}"


def _read_choice(prompt: str = "> ") -> str:
    """Read a single-line choice from /dev/tty (works even when stdin is piped)."""
    try:
        tty = open("/dev/tty", "r", encoding="utf-8")
        sys.stderr.write(prompt)
        sys.stderr.flush()
        choice = tty.readline().strip().lower()
        tty.close()
        return choice
    except OSError:
        return ""


def _stop_session(session: dict, claude_bin: str) -> None:
    """Properly stop a session — never bare kill for bg jobs."""
    pid = session.get("pid")
    kind = session.get("kind", "unknown")

    if kind == "bg":
        job_id = session.get("jobId", "")
        if job_id:
            try:
                subprocess.run(
                    [claude_bin, "agents", "stop", job_id],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                logger.info("[SESSION_BOOT] Stopped bg job %s (PID %d)", job_id, pid)
                return
            except (OSError, subprocess.TimeoutExpired) as exc:
                logger.warning("[SESSION_BOOT] Failed to stop bg job %s: %s", job_id, exc)

    tmux_session = _find_tmux_session_for_pid(pid) if pid else None
    if tmux_session:
        subprocess.run(["tmux", "kill-session", "-t", tmux_session], check=False)
        logger.info("[SESSION_BOOT] Killed tmux session '%s' (PID %d)", tmux_session, pid)
        return

    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info("[SESSION_BOOT] Sent SIGTERM to PID %d", pid)
        except ProcessLookupError:
            pass


def _resume_session(session: dict, claude_bin: str, defaults: list[str]) -> dict:
    """Resume a session — right mechanism per kind."""
    pid = session.get("pid")
    kind = session.get("kind", "unknown")

    if kind == "bg":
        cwd = session.get("cwd", "")
        args = [claude_bin, "agents", "--cwd", cwd] if cwd else [claude_bin, "agents"]
        logger.info("[SESSION_BOOT] Opening agents view for bg session PID %d", pid)
        os.execvp(claude_bin, args)
        return {"exit_code": 0, "action": "agents_view"}

    tmux_session = _find_tmux_session_for_pid(pid) if pid else None
    if tmux_session:
        logger.info("[SESSION_BOOT] Attaching to tmux session '%s'", tmux_session)
        os.execvp("tmux", ["tmux", "attach-session", "-t", tmux_session])
        return {"exit_code": 0, "action": "attached", "tmux_session": tmux_session}

    logger.info("[SESSION_BOOT] Continuing dead-window session via --continue")
    os.execvp(claude_bin, [claude_bin] + defaults + ["--continue"])
    return {"exit_code": 0, "action": "continued"}


def _make_session_name(branch: str, session_id: str = "") -> str:
    """Generate tmux session name: branch-shortid."""
    short_id = session_id[:8] if session_id else ""
    if short_id:
        return f"{branch}-{short_id}"
    return branch


def boot(cwd: str | None = None, extra_args: list[str] | None = None) -> dict:
    """Boot Claude Code — present menu when sessions exist.

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
        return _menu_live(live, branch, claude_bin, defaults, extra_args)
    return _menu_no_live(branch, claude_bin, defaults, extra_args)


def _menu_live(
    live: list[dict],
    branch: str,
    claude_bin: str,
    defaults: list[str],
    extra_args: list[str] | None,
) -> dict:
    """Display menu when live session(s) exist."""
    if len(live) == 1:
        session = live[0]
        label = _session_label(session, branch)
        sys.stderr.write(f"\n{branch} — live chat: {label}\n")
        sys.stderr.write("  [Enter]  resume this chat\n")
        sys.stderr.write("  [n]      start new chat   (closes the one above first)\n")
        sys.stderr.write("  [c]      close it and exit\n\n")

        choice = _read_choice()

        if choice in ("", "r"):
            return _resume_session(session, claude_bin, defaults)
        elif choice == "n":
            _stop_session(session, claude_bin)
            return _start_fresh(branch, claude_bin, defaults, extra_args)
        elif choice == "c":
            _stop_session(session, claude_bin)
            sys.stderr.write(f"  Closed {branch} session.\n")
            return {"exit_code": 0, "action": "closed"}
        else:
            sys.stderr.write("  Unknown choice. Exiting.\n")
            return {"exit_code": 1, "error": "unknown choice"}

    sys.stderr.write(f"\n{branch} — {len(live)} live sessions:\n")
    for i, session in enumerate(live, 1):
        label = _session_label(session, branch)
        sys.stderr.write(f"  [{i}]  {label}\n")
    sys.stderr.write("  [c]  close all and exit\n\n")

    choice = _read_choice()

    if choice == "c":
        for session in live:
            _stop_session(session, claude_bin)
        sys.stderr.write(f"  Closed all {branch} sessions.\n")
        return {"exit_code": 0, "action": "closed_all"}

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(live):
            return _resume_session(live[idx], claude_bin, defaults)
    except (ValueError, IndexError):
        pass

    if choice == "" and live:
        return _resume_session(live[0], claude_bin, defaults)

    sys.stderr.write("  Unknown choice. Exiting.\n")
    return {"exit_code": 1, "error": "unknown choice"}


def _menu_no_live(
    branch: str,
    claude_bin: str,
    defaults: list[str],
    extra_args: list[str] | None,
) -> dict:
    """Display menu when no live session exists."""
    sys.stderr.write(f"\n{branch} — no live chat\n")
    sys.stderr.write("  [Enter]  continue last chat\n")
    sys.stderr.write("  [n]      new chat\n\n")

    choice = _read_choice()

    if choice in ("", "r"):
        logger.info("[SESSION_BOOT] Continuing last chat via --continue")
        os.execvp(claude_bin, [claude_bin] + defaults + ["--continue"])
        return {"exit_code": 0, "action": "continued"}
    elif choice == "n":
        return _start_fresh(branch, claude_bin, defaults, extra_args)
    else:
        sys.stderr.write("  Unknown choice. Exiting.\n")
        return {"exit_code": 1, "error": "unknown choice"}


def _start_fresh(
    branch: str,
    claude_bin: str,
    defaults: list[str],
    extra_args: list[str] | None,
) -> dict:
    """Start a fresh Claude session in a new tmux session."""
    session_name = _make_session_name(branch)

    if _tmux_session_exists(session_name):
        logger.info("[SESSION_BOOT] Killing stale tmux session '%s'", session_name)
        subprocess.run(["tmux", "kill-session", "-t", session_name], check=False)

    claude_cmd = [claude_bin] + defaults
    if extra_args:
        claude_cmd.extend(extra_args)

    logger.info("[SESSION_BOOT] Starting fresh in tmux session '%s': %s", session_name, " ".join(claude_cmd))
    os.execvp("tmux", ["tmux", "new-session", "-s", session_name, "--"] + claude_cmd)
    return {"exit_code": 0, "action": "started", "tmux_session": session_name}


def main() -> None:
    """CLI entry point for the boot wrapper."""
    result = boot(extra_args=sys.argv[1:] if len(sys.argv) > 1 else None)
    if result.get("exit_code", 0) != 0:
        sys.stderr.write(f"{result.get('error', 'boot failed')}\n")
        sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
