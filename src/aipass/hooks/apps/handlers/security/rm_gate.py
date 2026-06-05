# =================== AIPass ====================
# Name: rm_gate.py
# Version: 1.0.0
# Description: Blocks raw recursive rm commands (PreToolUse)
# Branch: hooks
# Layer: apps/handlers/security
# Created: 2026-06-02
# Modified: 2026-06-02
# =============================================

"""Blocks raw recursive rm and teaches drone rm."""

import json
import re

from aipass.hooks.apps.sound import speak
from aipass.prax.apps.modules.logger import system_logger as logger


RM_REDIRECT = (
    "Raw recursive rm is blocked. Use the safe contained delete instead:\n"
    "  drone rm <path>     # safe delete (allows project + /tmp, refuses outside)\n"
    "\n"
    "This applies to all recursive rm variants (rm -rf, rm -r, rm -R, rm --recursive)."
)

_BLOCK_ALLOW = {"stdout": "", "exit_code": 0}


def _block(reason: str) -> dict:
    return {"stdout": json.dumps({"decision": "block", "reason": reason}), "exit_code": 2}


def _strip_quotes(cmd: str) -> str:
    """Remove quoted strings so their contents aren't scanned."""
    cmd = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cmd)
    cmd = re.sub(r"'(?:[^'\\]|\\.)*'", "''", cmd)
    return cmd


def _split_clauses(cmd: str) -> list[str]:
    """Split on compound operators and subshell boundaries."""
    parts = re.split(r"&&|\|\||[;|]", cmd)
    clauses: list[str] = []
    for part in parts:
        clauses.extend(re.split(r"[$()`]", part))
    return clauses


def _has_recursive_flag(tokens: list[str]) -> bool:
    """Return True if any token before '--' contains a recursive flag."""
    for token in tokens:
        if token == "--":
            break
        if token.startswith("-") and not token.startswith("--"):
            if "r" in token[1:] or "R" in token[1:]:
                return True
        elif token == "--recursive":
            return True
    return False


def _clause_has_raw_recursive_rm(clause: str) -> bool:
    """Return True if a single clause contains a raw recursive rm."""
    tokens = clause.split()
    if not tokens:
        return False
    for i, tok in enumerate(tokens):
        if tok != "rm" and not tok.endswith("/rm"):
            continue
        if i > 0 and tokens[i - 1] == "drone":
            continue
        if _has_recursive_flag(tokens[i + 1 :]):
            return True
    return False


def handle(hook_data: dict) -> dict:
    """Block raw recursive rm commands and teach drone rm.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (block JSON or empty) and exit_code.
    """
    speak("rm gate")

    try:
        tool_name = hook_data.get("tool_name", "")
        if tool_name != "Bash":
            return _BLOCK_ALLOW

        tool_input = hook_data.get("tool_input", {})
        cmd = tool_input.get("command", "")
        if not cmd:
            return _BLOCK_ALLOW

        scan = _strip_quotes(cmd)
        for clause in _split_clauses(scan):
            if _clause_has_raw_recursive_rm(clause):
                return _block(RM_REDIRECT)

        return _BLOCK_ALLOW

    except Exception as exc:
        logger.info("[HOOKS] rm_gate: unexpected error (allowing): %s", exc)
        return _BLOCK_ALLOW
