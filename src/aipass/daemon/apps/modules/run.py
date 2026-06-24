# =================== AIPass ====================
# Name: run.py
# Description: Manual one-tick scheduler command (drone @daemon run)
# Version: 1.0.0
# Created: 2026-06-15
# Modified: 2026-06-15
# =============================================

"""
Manual one-tick scheduler — discover .daemon/ jobs, fire due ones via wake_branch.

Handles 'drone @daemon run': one discover -> due-check -> fire pass.
Part of the DPLAN-0204 decentralized scheduler redesign.
"""

import sys
import time
from pathlib import Path
from typing import List

from aipass.prax import logger
from aipass.cli.apps.modules import console
from aipass.daemon.apps.handlers.json import json_handler
from aipass.daemon.apps.handlers.schedule.discovery import discover_jobs
from aipass.daemon.apps.handlers.schedule.runstate import (
    load_runstate,
    save_runstate,
    is_job_due,
    update_job_runstate,
    job_key,
    prune_orphans,
)

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]
    logger.info("[run] fcntl unavailable (Windows)")

_DAEMON_ROOT = Path(__file__).resolve().parents[2]  # src/aipass/daemon/
LOCK_FILE = _DAEMON_ROOT / "daemon_json" / "schedule.lock"

HANDLED_COMMANDS = {"run"}


def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("[bold cyan]run Module[/bold cyan]")
    console.print()
    console.print("[dim]Decentralized scheduler — one discover/due/fire tick[/dim]")
    console.print()
    console.print("[yellow]Reads:[/yellow]")
    console.print("  [cyan]*[/cyan] src/aipass/*/.daemon/*.json [dim](per-branch schedule files)[/dim]")
    console.print("  [cyan]*[/cyan] daemon_json/daemon_runstate.json [dim](last_run/next_run state)[/dim]")
    console.print()
    console.print("[yellow]Fires via:[/yellow]")
    console.print("  [cyan]*[/cyan] wake_branch() [dim](ai_mail dispatch — direct import)[/dim]")
    console.print()


def print_help():
    """Display usage information."""
    console.print("\n[bold cyan]run — Decentralized Scheduler Tick[/bold cyan]")
    console.print("\n[yellow]USAGE:[/yellow]")
    console.print("  drone @daemon run           Run one discover/due/fire pass")
    console.print("  drone @daemon run --dry-run  Show what would fire without firing")
    console.print("  drone @daemon run --help     Show this help message")
    console.print("\n[yellow]DESCRIPTION:[/yellow]")
    console.print("  Sweeps src/aipass/*/.daemon/*.json for scheduled jobs,")
    console.print("  evaluates due-ness, and wakes each due branch via wake_branch().")
    console.print()


def _log(message: str) -> None:
    """Print timestamped log line."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"[{timestamp}] {message}")


def _fire_job(job: dict) -> bool:
    """Fire a single job via direct wake_branch import (DPLAN-0204 path A)."""
    # Cross-branch handler import authorized by DPLAN-0204 §2.8
    from aipass.ai_mail.apps.handlers.dispatch.wake import wake_branch  # noqa: E402

    owner = job["owner"]
    prompt = job["prompt"]
    wake = job.get("wake", {})
    fresh = wake.get("fresh", True)
    model = wake.get("model")

    _log(f"FIRE: {owner}/{job['id']} -> wake_branch({owner}, fresh={fresh}, model={model})")

    try:
        status, ok = wake_branch(
            owner,
            custom_message=prompt,
            fresh=fresh,
            auto=True,
            sender="@daemon",
            model=model,
        )
        if ok:
            _log(f"OK: {owner}/{job['id']} — {status.summary}")
            logger.info("[run] Fired %s/%s successfully", owner, job["id"])
        else:
            _log(f"FAIL: {owner}/{job['id']} — {status.summary}")
            logger.warning("[run] Failed to fire %s/%s: %s", owner, job["id"], status.summary)
        return ok
    except Exception as e:
        logger.error("[run] Exception firing %s/%s: %s", owner, job["id"], e)
        _log(f"ERROR: {owner}/{job['id']} — {e}")
        return False


def run_tick(dry_run: bool = False) -> dict:
    """
    Execute one discover -> due-check -> fire pass.

    Returns summary dict with counts.
    """
    results = {
        "discovered": 0,
        "enabled": 0,
        "due": 0,
        "fired": 0,
        "failed": 0,
        "skipped": 0,
    }

    json_handler.log_operation("scheduler_tick", {"dry_run": dry_run})

    # Step 1: Discover
    _log("Discovering .daemon/ schedule files...")
    jobs = discover_jobs()
    results["discovered"] = len(jobs)

    if not jobs:
        _log("No jobs discovered.")
        return results

    # Step 2: Filter enabled
    enabled = [j for j in jobs if j.get("enabled", True)]
    results["enabled"] = len(enabled)
    _log(f"Found {len(jobs)} job(s), {len(enabled)} enabled")

    if not enabled:
        _log("No enabled jobs.")
        return results

    # Step 3: Load runstate and check due
    runstate = load_runstate()

    # Prune orphan runstate entries
    active_keys = {job_key(j["owner"], j["id"]) for j in jobs}
    prune_orphans(runstate, active_keys)

    due_jobs = [j for j in enabled if is_job_due(j, runstate)]
    results["due"] = len(due_jobs)
    results["skipped"] = len(enabled) - len(due_jobs)

    if not due_jobs:
        _log("No jobs due at this time.")
        for j in enabled:
            _log(f"  {j['owner']}/{j['id']} — not due")
        return results

    _log(f"{len(due_jobs)} job(s) due:")
    for j in due_jobs:
        _log(f"  {j['owner']}/{j['id']} ({j['schedule']['type']})")

    if dry_run:
        _log("DRY RUN — no jobs fired.")
        return results

    # Step 4: Fire due jobs
    for job in due_jobs:
        ok = _fire_job(job)
        if ok:
            results["fired"] += 1
            update_job_runstate(runstate, job["owner"], job["id"], job["schedule"])
            save_runstate(runstate)
        else:
            results["failed"] += 1

        if job != due_jobs[-1]:
            time.sleep(1.0)

    _log(f"Tick complete: {results['fired']} fired, {results['failed']} failed, {results['skipped']} skipped")
    return results


def _run_with_lock(dry_run: bool = False) -> int:
    """Run tick with fcntl lock to prevent concurrent execution."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if fcntl is None:
        _log("fcntl not available (non-Unix), running without lock.")
        results = run_tick(dry_run)
        return 1 if results["failed"] > 0 else 0

    lock_fd = open(LOCK_FILE, "w", encoding="utf-8")  # noqa: SIM115
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        logger.info("[run] Lock acquisition failed (another instance running): %s", e)
        _log("Another scheduler instance is running, skipping.")
        lock_fd.close()
        return 0

    try:
        results = run_tick(dry_run)
        return 1 if results["failed"] > 0 else 0
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'run' command from daemon CLI router."""
    if command not in HANDLED_COMMANDS:
        return False

    if not args:
        pass
    elif args[0] in ("--help", "-h"):
        print_help()
        return True

    dry_run = "--dry-run" in args

    _log("=" * 60)
    _log("Decentralized scheduler tick")

    exit_code = _run_with_lock(dry_run)

    _log("=" * 60)

    if exit_code != 0:
        sys.exit(exit_code)

    return True
