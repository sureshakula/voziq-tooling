# =================== AIPass ====================
# Name: dispatch_monitor.py
# Description: Agent Lifecycle Monitor
# Version: 1.0.0
# Created: 2026-03-02
# Modified: 2026-03-02
# =============================================

"""
Agent Lifecycle Monitor

Wraps a Claude agent spawn. Instead of fire-and-forget Popen, this process:
1. Runs claude and WAITS for it to complete
2. Checks exit code
3. On failure: sends return-to-sender bounce email
4. Always cleans up the dispatch lock

Spawned by wake.py in place of claude directly. The lock PID points to
the monitor (which stays alive as long as claude does), so lock validity
is guaranteed.
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.ai_mail.apps.handlers.json import json_handler


def _send_bounce(branch_email: str, reason: str, sender: str,
                 lock_file: str, stderr_log: str) -> bool:
    """Send return-to-sender bounce email via drone."""
    subject = f"BOUNCE: Dispatch to {branch_email} failed"

    # Read last few lines of stderr log for diagnostics
    stderr_tail = ""
    try:
        with open(stderr_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        stderr_tail = "".join(lines[-20:]).strip()
    except (OSError, FileNotFoundError):
        stderr_tail = "(no stderr captured)"

    body = (
        f"Agent at {branch_email} exited abnormally.\n\n"
        f"Reason: {reason}\n\n"
        f"Stderr (last 20 lines):\n{stderr_tail}\n\n"
        f"Lock file cleaned automatically.\n"
        f"Re-dispatch if task was not completed."
    )

    # Send via drone (resolves paths, handles routing)
    try:
        result = subprocess.run(
            ["drone", "@ai_mail", "send", sender, subject, body],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(lock_file).parent.parent)
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        # Fallback: write bounce to a file if email fails
        try:
            bounce_file = Path(lock_file).parent / "last_bounce.json"
            with open(bounce_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "branch": branch_email,
                    "reason": reason,
                    "sender": sender,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "stderr_tail": stderr_tail
                }, f, indent=2)
        except OSError:
            logger.info("[monitor] Failed to write bounce file fallback")
        return False


def main():
    """
    Usage: dispatch_monitor.py <branch_email> <lock_file> <sender> <stderr_log> -- <claude_args...>

    Runs claude, waits for completion, handles cleanup.
    """
    if len(sys.argv) < 6 or "--" not in sys.argv:
        logger.warning("[monitor] Invalid arguments: %s", sys.argv)
        sys.exit(1)

    sep_idx = sys.argv.index("--")
    branch_email = sys.argv[1]
    lock_file = sys.argv[2]
    sender = sys.argv[3]
    stderr_log = sys.argv[4]
    claude_cmd = sys.argv[sep_idx + 1:]

    if not claude_cmd:
        logger.warning("[monitor] No claude command after --")
        sys.exit(1)

    json_handler.log_operation("dispatch_monitor_start", {"branch": branch_email, "sender": sender})

    # Open stderr log for claude output
    try:
        stderr_fh = open(stderr_log, 'a', encoding='utf-8')
        stderr_fh.write(f"\n--- Monitor for {branch_email} started at "
                        f"{time.strftime('%Y-%m-%dT%H:%M:%S')} (PID {os.getpid()}) ---\n")
        stderr_fh.flush()
    except OSError:
        stderr_fh = subprocess.DEVNULL

    # Prepare env — strip CLAUDE* vars and AIPASS_BOT_ID
    spawn_env = os.environ.copy()
    spawn_env["AIPASS_SPAWNED"] = "1"
    spawn_env["AIPASS_SESSION_TYPE"] = "dispatched"
    for key in list(spawn_env.keys()):
        if key.startswith("CLAUDE") or key == "AIPASS_BOT_ID":
            spawn_env.pop(key)
    # Strip caller identity vars to prevent dispatch context leakage.
    spawn_env.pop("AIPASS_CALLER_BRANCH", None)
    spawn_env.pop("AIPASS_CALLER_CWD", None)
    # Set CWD-independent branch identity so agent knows who it is
    # even after cd'ing away. Drone reads this as fallback for caller detection.
    spawn_env["AIPASS_BRANCH_NAME"] = branch_email.lstrip("@")

    # Extract CWD from lock file path (branch_path/.ai_mail.local/.dispatch.lock)
    lock_path = Path(lock_file)
    branch_path = lock_path.parent.parent
    cwd = str(branch_path)

    start_time = time.time()

    # Run claude — BLOCKING. Monitor stays alive as long as agent is working.
    stdout_log = str(branch_path / ".ai_mail.local" / "agent_stdout.log")
    try:
        stdout_fh = open(stdout_log, 'w', encoding='utf-8')
    except OSError:
        stdout_fh = subprocess.DEVNULL
    try:
        result = subprocess.run(
            claude_cmd,
            stdout=stdout_fh if isinstance(stdout_fh, int) else stdout_fh,
            stderr=stderr_fh,
            cwd=cwd,
            env=spawn_env,
            timeout=7200  # 2 hour hard timeout
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        exit_code = -1
        reason = "Agent timed out (2 hour limit)"
        _send_bounce(branch_email, reason, sender, lock_file, stderr_log)
    except Exception as e:
        exit_code = -2
        reason = f"Monitor error: {type(e).__name__}: {e}"
        _send_bounce(branch_email, reason, sender, lock_file, stderr_log)

    duration = int(time.time() - start_time)

    # Close stdout log
    if not isinstance(stdout_fh, int):
        try:
            stdout_fh.close()
        except OSError:
            pass

    # Check for max-turns hit (Claude exits 0 but output contains stop_reason)
    max_turns_hit = False
    try:
        with open(stdout_log, 'r', encoding='utf-8') as f:
            stdout_content = f.read()
        if '"stop_reason":"max_turns"' in stdout_content or '"stop_reason": "max_turns"' in stdout_content:
            max_turns_hit = True
            logger.warning("[monitor] %s HIT MAX TURNS after %ds — work may be incomplete", branch_email, duration)
    except OSError:
        pass

    # Log completion
    if not isinstance(stderr_fh, int):
        try:
            suffix = " [MAX TURNS HIT]" if max_turns_hit else ""
            stderr_fh.write(f"\n--- Agent exited: code={exit_code}, duration={duration}s{suffix} ---\n")
            stderr_fh.flush()
            stderr_fh.close()
        except OSError:
            logger.info("[monitor] Failed to write agent exit log")

    # Check exit code and handle failure
    if exit_code != 0:
        reason = f"Exit code {exit_code} after {duration}s"

        # Check stderr log for clues
        try:
            with open(stderr_log, 'r', encoding='utf-8') as f:
                content = f.read()
            if "rate_limit" in content.lower() or "429" in content:
                reason = f"API rate limit hit (exit {exit_code}, {duration}s)"
            elif "overloaded" in content.lower() or "529" in content:
                reason = f"API overloaded (exit {exit_code}, {duration}s)"
            elif "network" in content.lower() or "connection" in content.lower():
                reason = f"Network error (exit {exit_code}, {duration}s)"
        except OSError:
            logger.info("[monitor] Failed to read stderr log for diagnostics")

        _send_bounce(branch_email, reason, sender, lock_file, stderr_log)

    # Always clean up lock file — monitor handles this, agent doesn't need to
    try:
        if os.path.exists(lock_file):
            os.unlink(lock_file)
    except OSError:
        logger.info("[monitor] Failed to clean up lock file %s", lock_file)

    # Log completion to Prax
    status = "completed" if exit_code == 0 else f"FAILED (code {exit_code})"
    if max_turns_hit:
        status = f"MAX TURNS HIT ({duration}s)"
    logger.info("[monitor] %s agent %s — %ds", branch_email, status, duration)

    # Desktop notification on completion
    try:
        from aipass.ai_mail.apps.handlers.notify import send_notification
        icon = "dialog-information" if exit_code == 0 else "dialog-warning"
        send_notification(
            f"Agent {branch_email} {status}", f"Duration: {duration}s",
            source=branch_email.lstrip("@"), icon=icon
        )
    except Exception:
        logger.info("[monitor] Desktop notification unavailable")

    sys.exit(0 if exit_code == 0 else 1)


if __name__ == "__main__":
    main()
