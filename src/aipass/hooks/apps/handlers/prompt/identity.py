# =================== AIPass ====================
# Name: identity.py
# Version: 1.0.0
# Description: Injects branch identity from passport.json (UserPromptSubmit)
# Branch: hooks
# Layer: apps/handlers/prompt
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Reads .trinity/passport.json and outputs formatted identity for prompt injection."""

import json
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger


def _find_passport(cwd: str) -> Path | None:
    """Walk up from CWD looking for .trinity/passport.json."""
    search = Path(cwd).resolve()
    home = Path.home()
    while search != home and search.parent != search:
        passport = search / ".trinity" / "passport.json"
        if passport.exists():
            return passport
        search = search.parent
    return None


def _format_identity(data: dict) -> str:
    lines: list[str] = []

    branch = data.get("branch_info", {})
    identity = data.get("identity", {})
    name = branch.get("branch_name") or identity.get("name", "UNKNOWN")
    lines.append(f"# {name} Identity")
    lines.append(f"Path: {branch.get('path', 'unknown')}")
    lines.append(f"Email: {branch.get('email', 'unknown')}")

    if identity.get("role"):
        lines.append(f"Role: {identity['role']}")

    traits = identity.get("traits") or data.get("traits")
    if traits:
        if isinstance(traits, list):
            lines.append("Traits: " + " | ".join(traits))
        else:
            lines.append(f"Traits: {traits}")

    if identity.get("purpose"):
        lines.append(f"Purpose: {identity['purpose']}")

    what_i_do = identity.get("what_i_do", [])
    if what_i_do:
        lines.append("Do: " + " | ".join(what_i_do[:4]))

    what_i_dont_do = identity.get("what_i_dont_do", [])
    if what_i_dont_do:
        lines.append("Don't: " + " | ".join(what_i_dont_do[:3]))

    principles = data.get("principles", [])
    if principles:
        lines.append("Principles: " + " * ".join(principles))

    return "\n".join(lines)


def handle(hook_data: dict) -> dict:
    """Inject branch identity from passport.json into prompt context."""
    try:
        cwd = hook_data.get("cwd", "") or str(Path.cwd())
        passport = _find_passport(cwd)
        if not passport:
            return {"stdout": "", "exit_code": 0}

        data = json.loads(passport.read_text(encoding="utf-8"))
        output = _format_identity(data)
        if not output:
            return {"stdout": "", "exit_code": 0}

        return {"stdout": f"\n{output}", "exit_code": 0, "sound": "identity"}

    except Exception as exc:
        logger.info("[HOOKS] identity: unexpected error: %s", exc)
        return {"stdout": "", "exit_code": 0}
