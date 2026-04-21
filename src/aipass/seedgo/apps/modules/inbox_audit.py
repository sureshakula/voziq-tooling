# =================== AIPass ====================
# Name: inbox_audit.py
# Description: Inbox ID validator — scans all inbox.json files for non-8-hex ids
# Version: 1.0.0
# Created: 2026-04-21
# Modified: 2026-04-21
# =============================================

"""Inbox ID validator for the drone @seedgo audit inbox-ids command.

Walks all .ai_mail.local/inbox.json files in the AIPass repo and flags any
message ids that are not 8-character lowercase hex strings.  Alerts devpulse
when violations are found.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from aipass.prax import logger
from aipass.cli import console, header
from aipass.seedgo.apps.handlers.json import json_handler

_HEX8_RE = re.compile(r"^[0-9a-f]{8}$")


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in (current, *current.parents):
        if (parent / ".git").exists():
            return parent
    return current


def _scan_inbox(inbox_path: Path) -> List[dict]:
    """Return a list of violation dicts for messages with bad ids in *inbox_path*."""
    violations: List[dict] = []
    try:
        data = json.loads(inbox_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[inbox_audit] could not read %s: %s", inbox_path, exc)
        return violations

    for msg in data.get("messages", []):
        msg_id = msg.get("id", "")
        if not _HEX8_RE.match(str(msg_id)):
            violations.append(
                {
                    "inbox": str(inbox_path),
                    "id": msg_id,
                    "subject": msg.get("subject", ""),
                    "from": msg.get("from", ""),
                }
            )
    return violations


def _run_inbox_id_scan() -> int:
    """Scan all inbox.json files; return number of violations found."""
    json_handler.log_operation("inbox_audit_scan", {})
    repo_root = _find_repo_root()
    inbox_files = list(repo_root.rglob(".ai_mail.local/inbox.json"))

    console.print()
    header("SEEDGO — Inbox ID Validator")
    console.print(f"[dim]Scanning {len(inbox_files)} inbox file(s) for non-8-hex message ids...[/dim]")
    console.print()

    all_violations: List[dict] = []
    for inbox_path in sorted(inbox_files):
        violations = _scan_inbox(inbox_path)
        all_violations.extend(violations)

    if not all_violations:
        console.print("[green]✓[/green] All message ids are valid 8-char hex strings.")
        console.print()
        return 0

    console.print(f"[red]✗[/red] Found [bold]{len(all_violations)}[/bold] id violation(s):\n")
    for v in all_violations:
        rel = Path(v["inbox"]).relative_to(repo_root) if Path(v["inbox"]).is_absolute() else v["inbox"]
        console.print(
            f"  [red]•[/red] [bold]{rel}[/bold]  id=[yellow]{v['id']!r}[/yellow]  from={v['from']}  subject={v['subject']!r}"
        )

    console.print()
    console.print("[yellow]Action:[/yellow] Alert devpulse — run:")
    console.print(
        f'  [green]drone @ai_mail email @devpulse "inbox-id violations" '
        f'"Found {len(all_violations)} bad message id(s) — run drone @seedgo audit inbox-ids for details"[/green]'
    )
    console.print()
    return len(all_violations)


def print_introspection() -> None:
    """Show inbox_audit module structure."""
    console.print("[bold cyan]inbox_audit[/bold cyan] — Inbox ID validator")
    console.print("  Connected Handlers: none (uses stdlib + pathlib only)")
    console.print("  Command: drone @seedgo audit inbox-ids")


def handle_command(command: str, args: List[str]) -> bool:
    """Handle `audit inbox-ids` — return True only for that exact subcommand."""
    if command not in ("audit", "standards_audit"):
        return False
    if not args:
        print_introspection()
        return True
    if args[0] in ("--help", "-h", "help"):
        console.print("Usage: drone @seedgo audit inbox-ids")
        console.print("  Scans all .ai_mail.local/inbox.json files for non-8-hex message ids.")
        return True
    if args[0] != "inbox-ids":
        return False
    _run_inbox_id_scan()
    return True
