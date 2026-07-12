# =================== AIPass ====================
# Name: registry_gate.py
# Version: 1.0.0
# Description: Blocks raw writes, edits, and deletions of *_REGISTRY.json (PreToolUse)
# Branch: hooks
# Layer: apps/handlers/security
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""Blocks raw writes, edits, and deletions of *_REGISTRY.json files.

Sealed-authority enforcement: the registry is the single source of truth
for project ownership. Only drone @spawn (tier-gated) may write it.
"""

import json
import re
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger


REGISTRY_RE = re.compile(r"\w+_REGISTRY\.json$")

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

REGISTRY_REDIRECT = (
    "{file} is a sealed registry — direct writes are blocked.\nUse drone @spawn to manage registry entries."
)

_BLOCK_ALLOW = {"stdout": "", "exit_code": 0}

_REDIRECT_RE = re.compile(r">{1,2}\s*\S*_REGISTRY\.json\b")
_TEE_RE = re.compile(r"\btee\b[^&;|]*\S*_REGISTRY\.json\b")
_SED_I_RE = re.compile(r"\bsed\b\s[^&;|]*-i[^&;|]*\S*_REGISTRY\.json\b")


def _block(reason: str) -> dict:
    return {"stdout": json.dumps({"decision": "block", "reason": reason}), "exit_code": 2, "sound": "registry gate"}


def _is_registry_file(name: str) -> bool:
    return bool(REGISTRY_RE.search(Path(name).name))


def _strip_quotes(cmd: str) -> str:
    cmd = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cmd)
    cmd = re.sub(r"'(?:[^'\\]|\\.)*'", "''", cmd)
    return cmd


def _split_clauses(cmd: str) -> list[str]:
    parts = re.split(r"&&|\|\||[;|]", cmd)
    clauses: list[str] = []
    for part in parts:
        clauses.extend(re.split(r"[$()`]", part))
    return clauses


def _is_drone_spawn(clause: str) -> bool:
    stripped = clause.strip()
    return stripped.startswith("drone @spawn") or stripped.startswith("drone spawn")


def _clause_targets_registry(clause: str) -> bool:
    if _is_drone_spawn(clause):
        return False

    if _REDIRECT_RE.search(clause):
        return True
    if _TEE_RE.search(clause):
        return True
    if _SED_I_RE.search(clause):
        return True

    tokens = clause.split()
    if not tokens:
        return False

    for i, tok in enumerate(tokens):
        if tok in ("mv",) or tok.endswith("/mv"):
            if i > 0 and tokens[i - 1] == "drone":
                continue
            remaining = tokens[i + 1 :]
            args = [t for t in remaining if not t.startswith("-")]
            for arg in args:
                if _is_registry_file(arg):
                    return True

        if tok in ("cp",) or tok.endswith("/cp"):
            if i > 0 and tokens[i - 1] == "drone":
                continue
            remaining = tokens[i + 1 :]
            args = [t for t in remaining if not t.startswith("-")]
            if len(args) >= 2 and _is_registry_file(args[-1]):
                return True

        if tok in ("rm", "unlink") or tok.endswith("/rm"):
            if i > 0 and tokens[i - 1] == "drone":
                continue
            remaining = tokens[i + 1 :]
            for arg in remaining:
                if arg.startswith("-"):
                    continue
                if _is_registry_file(arg):
                    return True

    return False


def _find_registry_name(text: str) -> str:
    match = REGISTRY_RE.search(text)
    return match.group(0) if match else "*_REGISTRY.json"


def _check_bash(tool_input: dict) -> dict:
    cmd = tool_input.get("command", "")
    if not cmd:
        return _BLOCK_ALLOW

    if "_REGISTRY.json" not in cmd:
        return _BLOCK_ALLOW

    scan = _strip_quotes(cmd)

    if "_REGISTRY.json" not in scan:
        return _BLOCK_ALLOW

    for clause in _split_clauses(scan):
        if _clause_targets_registry(clause):
            return _block(REGISTRY_REDIRECT.format(file=_find_registry_name(clause)))

    return _BLOCK_ALLOW


def _check_edit(tool_input: dict) -> dict:
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return _BLOCK_ALLOW
    if _is_registry_file(file_path):
        return _block(REGISTRY_REDIRECT.format(file=Path(file_path).name))
    return _BLOCK_ALLOW


def handle(hook_data: dict) -> dict:
    """Block raw writes, edits, and deletions of *_REGISTRY.json files.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (block JSON or empty) and exit_code.
    """
    try:
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        if tool_name == "Bash":
            return _check_bash(tool_input)
        if tool_name in EDIT_TOOLS:
            return _check_edit(tool_input)
        return _BLOCK_ALLOW
    except Exception as exc:
        logger.info("[HOOKS] registry_gate: unexpected error (allowing): %s", exc)
        return _BLOCK_ALLOW
