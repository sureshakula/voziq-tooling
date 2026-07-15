# =================== AIPass ====================
# Name: session_boot.py
# Version: 4.0.0
# Description: Boot wrapper — attach-first menu for Claude Code sessions
# Branch: hooks
# Layer: apps/handlers/lifecycle
# Created: 2026-06-30
# Modified: 2026-07-14
# =============================================

"""Boot wrapper for Claude Code sessions.

When Patrick runs `claude` in a branch directory, this wrapper presents a menu:

Live session (interactive):
  hooks — live chat: PID 1234 · abc12345 · interactive · 2h old
    [Enter]  resume this chat
    [n]      start new chat   (closes the one above first)
    [c]      close it and exit

Live session (background):
  devpulse — live chat: PID 773292 · c624cbcd · background "chroma review" · 2h old
    [Enter]  resume this chat   (stops bg, reopens as normal chat)
    [n]      start new chat   (stops bg first)
    [c]      close it and exit   (stops bg)

No live session:
  devpulse — no live chat
    [Enter]  continue last chat
    [n]      new chat

All interactive launches are tmux-wrapped (closed terminal = recoverable).

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
    except Exception as exc:
        logger.info("[SESSION_BOOT] age format error: %s", exc)
        return ""


def _session_short_id(session: dict) -> str:
    """Extract first 8 chars of sessionId."""
    return str(session.get("sessionId", ""))[:8]


def _session_label(session: dict, branch: str) -> str:
    """Format a session's one-line label: PID · short-id · kind [auto-name] · age."""
    pid = session.get("pid", "?")
    short_id = _session_short_id(session)
    kind = session.get("kind", "unknown")
    auto_name = session.get("name", "")
    name_str = f' "{auto_name}"' if auto_name else ""
    age = _format_age(session)
    age_str = f" · {age} old" if age else ""
    return f"PID {pid} · {short_id} · {kind}{name_str}{age_str}"


def _read_choice(prompt: str = "> ") -> str:
    """Read a single-line choice from /dev/tty (works even when stdin is piped)."""
    try:
        tty = open("/dev/tty", "r", encoding="utf-8")
        sys.stderr.write(prompt)
        sys.stderr.flush()
        choice = tty.readline().strip().lower()
        tty.close()
        return choice
    except OSError as exc:
        logger.info("[SESSION_BOOT] /dev/tty not available: %s", exc)
        return ""


def _stop_session(session: dict, claude_bin: str) -> str:
    """Stop a session. Returns description of action taken.

    bg sessions: no per-job stop exists in the CLI. Returns an honest
    message — never SIGTERMs bg (daemon respawns it).
    """
    pid = session.get("pid")
    kind = session.get("kind", "unknown")

    if kind in ("bg", "background"):
        logger.info("[SESSION_BOOT] Cannot stop bg PID %s — no per-job stop in CLI", pid)
        return f"PID {pid}: bg session — no per-job stop available"

    tmux_session = _find_tmux_session_for_pid(pid) if pid else None
    if tmux_session:
        subprocess.run(["tmux", "kill-session", "-t", tmux_session], check=False)
        logger.info("[SESSION_BOOT] Killed tmux session '%s' (PID %d)", tmux_session, pid)
        return f"PID {pid}: killed tmux session '{tmux_session}'"

    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info("[SESSION_BOOT] Sent SIGTERM to PID %d", pid)
            return f"PID {pid}: sent SIGTERM"
        except ProcessLookupError:
            logger.info("[SESSION_BOOT] PID %d already dead", pid)
            return f"PID {pid}: already dead"
        except OSError as exc:
            logger.warning("[SESSION_BOOT] SIGTERM PID %d failed: %s", pid, exc)
            return f"PID {pid}: SIGTERM failed ({exc})"
    return f"PID {pid}: no action"


def _resume_session(
    session: dict, branch: str, claude_bin: str, defaults: list[str], extra_args: list[str] | None = None
) -> dict:
    """Resume a session — right mechanism per kind.

    bg: takeover (daemon stop + --resume in tmux). Never opens agents view.
    tmux: attach to existing tmux session.
    dead-window: --continue in a new tmux session.
    """
    pid = session.get("pid")
    kind = session.get("kind", "unknown")
    ea = list(extra_args or [])

    if kind in ("bg", "background"):
        return _takeover_bg(session, branch, claude_bin, defaults, extra_args)

    tmux_session = _find_tmux_session_for_pid(pid) if pid else None
    if tmux_session:
        logger.info("[SESSION_BOOT] Attaching to tmux session '%s'", tmux_session)
        os.execvp("tmux", ["tmux", "attach-session", "-t", tmux_session])
        return {"exit_code": 0, "action": "attached", "tmux_session": tmux_session}

    logger.info("[SESSION_BOOT] Continuing dead-window session via --continue")
    sid = session.get("sessionId", "")
    nf = _name_flag(branch, sid, extra_args)
    return _exec_in_tmux(branch, "", claude_bin, [claude_bin] + defaults + ["--continue"] + ea + nf)


def _make_session_name(branch: str, session_id: str = "") -> str:
    """Generate tmux session name: branch-shortid."""
    short_id = session_id[:8] if session_id else ""
    if short_id:
        return f"{branch}-{short_id}"
    return branch


def _name_flag(branch: str, session_id: str = "", extra_args: list[str] | None = None) -> list[str]:
    """Build --name args for session stamping, unless user already provided one."""
    if extra_args and ("-n" in extra_args or "--name" in extra_args):
        return []
    return ["--name", _make_session_name(branch, session_id)]


def _exec_in_tmux(branch: str, session_id: str, claude_bin: str, claude_cmd: list[str]) -> dict:
    """Exec a claude command inside a new tmux session."""
    session_name = _make_session_name(branch, session_id)
    if _tmux_session_exists(session_name):
        subprocess.run(["tmux", "kill-session", "-t", session_name], check=False)
    logger.info("[SESSION_BOOT] Launching in tmux '%s': %s", session_name, " ".join(claude_cmd))
    os.execvp("tmux", ["tmux", "new-session", "-s", session_name, "--"] + claude_cmd)
    return {"exit_code": 0, "action": "started", "tmux_session": session_name}


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
        claude_cmd = [claude_bin] + defaults + _name_flag(branch, extra_args=extra_args)
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


def _has_bg(sessions: list[dict]) -> bool:
    """Check if any session is a background session."""
    return any(s.get("kind") in ("bg", "background") for s in sessions)


def _get_collateral_bg(branch: str) -> list[dict]:
    """Find live bg sessions outside the given branch (blast-radius check)."""
    import importlib

    cc_sessions = importlib.import_module("aipass.hooks.apps.modules.cc_sessions")
    collateral = []
    for s in cc_sessions.read_all_sessions():
        if s.get("kind") not in ("bg", "background"):
            continue
        s_branch = Path(s.get("cwd", "")).name
        if s_branch != branch and s.get("pid") and cc_sessions._is_pid_alive(s["pid"]):
            collateral.append(s)
    return collateral


def _daemon_stop(claude_bin: str, branch: str, pid: int | None) -> dict:
    """Run daemon stop --any with blast-radius confirmation.

    Returns {"ok": True} on success, {"ok": False, "error": "..."} on failure.
    """
    collateral = _get_collateral_bg(branch)
    if collateral:
        sys.stderr.write("  Other branches have live bg sessions that will also stop:\n")
        for s in collateral:
            coll_branch = Path(s.get("cwd", "")).name
            sys.stderr.write(f"    PID {s.get('pid')} · {coll_branch} · {_session_short_id(s)}\n")
        sys.stderr.write("  Continue? [y/N] ")
        confirm = _read_choice("")
        if confirm != "y":
            return {"ok": False, "error": "cancelled by user"}

    sys.stderr.write("  Stopping background sessions (daemon stop --any)...\n")
    try:
        result = subprocess.run(
            [claude_bin, "daemon", "stop", "--any"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            stderr_msg = result.stderr.strip()
            logger.warning("[SESSION_BOOT] daemon stop exit %d: %s", result.returncode, stderr_msg)
            sys.stderr.write(f"  daemon stop failed (exit {result.returncode}): {stderr_msg}\n")
            return {"ok": False, "error": f"daemon stop exit {result.returncode}: {stderr_msg}"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("[SESSION_BOOT] daemon stop failed: %s", exc)
        sys.stderr.write(f"  daemon stop failed: {exc}\n")
        return {"ok": False, "error": f"daemon stop failed: {exc}"}

    import time

    for _ in range(10):
        time.sleep(1)
        if not _is_session_file_present(pid):
            break
    else:
        logger.warning("[SESSION_BOOT] Session file for PID %s did not clear after daemon stop", pid)

    return {"ok": True}


def _takeover_bg(
    session: dict, branch: str, claude_bin: str, defaults: list[str], extra_args: list[str] | None = None
) -> dict:
    """Take over a bg session: daemon stop --any, poll, then --resume in tmux.

    Checks blast radius first (other branches' bg sessions). On daemon stop
    failure, aborts honestly. Resumes inside a tmux session so a closed
    terminal is always recoverable.
    """
    session_id = session.get("sessionId", "")
    pid = session.get("pid")
    ea = list(extra_args or [])
    nf = _name_flag(branch, session_id, extra_args)

    stop_result = _daemon_stop(claude_bin, branch, pid)
    if not stop_result["ok"]:
        return {"exit_code": 1, "error": stop_result["error"]}

    if session_id:
        logger.info("[SESSION_BOOT] Resuming session %s after takeover", session_id[:8])
        return _exec_in_tmux(
            branch, session_id, claude_bin, [claude_bin] + defaults + ["--resume", session_id] + ea + nf
        )

    logger.info("[SESSION_BOOT] No sessionId for takeover — continuing last")
    return _exec_in_tmux(branch, "", claude_bin, [claude_bin] + defaults + ["--continue"] + ea + nf)


def _is_session_file_present(pid: int | None) -> bool:
    """Check if a CC session file exists for the given PID."""
    if pid is None:
        return False
    session_file = Path.home() / ".claude" / "sessions" / f"{pid}.json"
    return session_file.exists()


def _menu_single_session(
    session: dict,
    branch: str,
    claude_bin: str,
    defaults: list[str],
    extra_args: list[str] | None,
) -> dict:
    """Handle menu for a single live session."""
    label = _session_label(session, branch)
    is_bg = session.get("kind") in ("bg", "background")
    sys.stderr.write(f"\n{branch} — live chat: {label}\n")
    if is_bg:
        sys.stderr.write("  [Enter]  resume this chat   (stops bg, reopens as normal chat)\n")
        sys.stderr.write("  [n]      start new chat   (stops bg first)\n")
        sys.stderr.write("  [c]      close it and exit   (stops bg)\n\n")
    else:
        sys.stderr.write("  [Enter]  resume this chat\n")
        sys.stderr.write("  [n]      start new chat   (closes the one above first)\n")
        sys.stderr.write("  [c]      close it and exit\n\n")

    choice = _read_choice()

    if choice in ("", "r"):
        return _resume_session(session, branch, claude_bin, defaults, extra_args)
    if choice == "n":
        return _menu_single_new(session, is_bg, branch, claude_bin, defaults, extra_args)
    if choice == "c":
        return _menu_single_close(session, is_bg, branch, claude_bin)
    if choice in ("exit", "q", "quit"):
        return {"exit_code": 0, "action": "quit"}
    sys.stderr.write("  Unknown choice. Exiting.\n")
    return {"exit_code": 1, "error": "unknown choice"}


def _menu_single_new(
    session: dict,
    is_bg: bool,
    branch: str,
    claude_bin: str,
    defaults: list[str],
    extra_args: list[str] | None,
) -> dict:
    """Handle 'n' choice for single session — stop current, start fresh."""
    if is_bg:
        stop = _daemon_stop(claude_bin, branch, session.get("pid"))
        if not stop["ok"]:
            return {"exit_code": 1, "error": stop["error"]}
    else:
        _stop_session(session, claude_bin)
    return _start_fresh(branch, claude_bin, defaults, extra_args)


def _menu_single_close(session: dict, is_bg: bool, branch: str, claude_bin: str) -> dict:
    """Handle 'c' choice for single session — close and exit."""
    if is_bg:
        stop = _daemon_stop(claude_bin, branch, session.get("pid"))
        if not stop["ok"]:
            return {"exit_code": 1, "error": stop["error"]}
        sys.stderr.write(f"  Stopped bg session PID {session.get('pid')}.\n")
    else:
        result = _stop_session(session, claude_bin)
        sys.stderr.write(f"  {result}\n")
    return {"exit_code": 0, "action": "closed"}


def _menu_live(
    live: list[dict],
    branch: str,
    claude_bin: str,
    defaults: list[str],
    extra_args: list[str] | None,
) -> dict:
    """Display menu when live session(s) exist."""
    if len(live) == 1:
        return _menu_single_session(live[0], branch, claude_bin, defaults, extra_args)

    sys.stderr.write(f"\n{branch} — {len(live)} live sessions:\n")
    for i, session in enumerate(live, 1):
        label = _session_label(session, branch)
        sys.stderr.write(f"  [{i}]  {label}\n")
    sys.stderr.write("  [n]  start new chat\n")
    sys.stderr.write("  [c]  close all and exit\n\n")

    choice = _read_choice()

    if choice == "c":
        return _close_all(live, branch, claude_bin)

    if choice == "n":
        return _new_over_all(live, branch, claude_bin, defaults, extra_args)

    if choice in ("exit", "q", "quit"):
        return {"exit_code": 0, "action": "quit"}

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(live):
            return _resume_session(live[idx], branch, claude_bin, defaults, extra_args)
    except (ValueError, IndexError):
        logger.info("[SESSION_BOOT] Invalid menu choice: %r", choice)

    sys.stderr.write("  Pick a number, 'n', or 'c'. Exiting.\n")
    return {"exit_code": 1, "error": "unknown choice"}


def _close_all(live: list[dict], branch: str, claude_bin: str) -> dict:
    """Close all sessions — stop what's stoppable, honest about bg."""
    non_bg = [s for s in live if s.get("kind") not in ("bg", "background")]
    bg = [s for s in live if s.get("kind") in ("bg", "background")]
    for s in non_bg:
        result = _stop_session(s, claude_bin)
        sys.stderr.write(f"  {result}\n")
    if bg:
        stop = _daemon_stop(claude_bin, branch, bg[0].get("pid"))
        if stop["ok"]:
            sys.stderr.write(f"  Stopped {len(bg)} bg session(s) via daemon stop.\n")
        else:
            for s in bg:
                sys.stderr.write(f"  PID {s.get('pid')}: bg session remains — daemon stop failed\n")
    return {"exit_code": 0, "action": "closed_all"}


def _new_over_all(
    live: list[dict],
    branch: str,
    claude_bin: str,
    defaults: list[str],
    extra_args: list[str] | None,
) -> dict:
    """Start new chat, stopping what's stoppable first."""
    non_bg = [s for s in live if s.get("kind") not in ("bg", "background")]
    bg = [s for s in live if s.get("kind") in ("bg", "background")]
    for s in non_bg:
        result = _stop_session(s, claude_bin)
        sys.stderr.write(f"  {result}\n")
    if bg:
        stop = _daemon_stop(claude_bin, branch, bg[0].get("pid"))
        if not stop["ok"]:
            sys.stderr.write("  Cannot start new — bg session(s) still running.\n")
            return {"exit_code": 1, "error": "daemon stop failed, aborting to preserve one-brain"}
    return _start_fresh(branch, claude_bin, defaults, extra_args)


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
        nf = _name_flag(branch, extra_args=extra_args)
        cmd = [claude_bin] + defaults + ["--continue"] + list(extra_args or []) + nf
        return _exec_in_tmux(branch, "", claude_bin, cmd)
    elif choice == "n":
        return _start_fresh(branch, claude_bin, defaults, extra_args)
    elif choice in ("exit", "q", "quit"):
        return {"exit_code": 0, "action": "quit"}
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

    claude_cmd = [claude_bin] + defaults + _name_flag(branch, extra_args=extra_args)
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
