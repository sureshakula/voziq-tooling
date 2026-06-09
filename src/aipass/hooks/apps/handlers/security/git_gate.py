# =================== AIPass ====================
# Name: git_gate.py
# Version: 1.0.0
# Description: Blocks raw git/gh commands and protected file edits (PreToolUse)
# Branch: hooks
# Layer: apps/handlers/security
# Created: 2026-05-21
# Modified: 2026-05-21
# =============================================

"""Blocks raw git/gh commands and edits to settings/hooks files."""

import json
import os
import re
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger


RAW_GIT_RE = re.compile(r"(?<![@\w/.])git\s")
RAW_GH_RE = re.compile(r"(?<![@\w/.])gh\s")

GH_ALLOWED_SUBCOMMANDS = ("api",)

READ_ALLOWED_GIT_SUBCOMMANDS = frozenset(
    {
        "ls-files",
        "ls-tree",
        "show",
        "cat-file",
        "rev-parse",
        "rev-list",
        "log",
        "status",
        "diff",
        "blame",
        "describe",
        "for-each-ref",
        "show-ref",
        "symbolic-ref",
        "shortlog",
        "grep",
        "archive",
        "count-objects",
        "var",
        "help",
        "version",
    }
)

_GIT_OPTS_WITH_ARG = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--exec-path", "--namespace"})

BLOCKED_EDIT_PATTERNS = [
    re.compile(r"/\.claude/settings(\.local)?\.json$"),
    re.compile(r"/\.claude/hooks/"),
    re.compile(r"/\.git/hooks/"),
]

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

TRUSTED_HOOK_EDITORS = ("devpulse", "seedgo")

GIT_GH_REDIRECT = (
    "Write git commands are blocked. Read-only verbs (status, log, diff, show, etc.) are allowed raw.\n"
    "For write operations, use drone:\n"
    "  drone @git smart-sync     # fetch + rebase\n"
    "  drone @git sync           # checkout main + pull\n"
    "  drone @git issue list     # GitHub issues\n"
    "  drone @git run list       # CI runs\n"
    "  drone @git workflow run   # trigger workflows"
)

EDIT_REDIRECT = (
    "{path} is protected — settings.json, .claude/hooks/, and .git/hooks/ "
    "govern the enforcement layer itself.\n"
    "If a real change is needed, ask devpulse to make it directly."
)

_BLOCK_ALLOW = {"stdout": "", "exit_code": 0}


def _cwd_branch(cwd: str) -> str:
    parts = Path(cwd).parts
    for i, part in enumerate(parts):
        if part == "aipass" and i > 0 and parts[i - 1] == "src" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def _is_allowed_gh(cmd: str) -> bool:
    match = re.search(r"(?<![@\w/.])gh\s+(\w+)", cmd)
    if match:
        return match.group(1) in GH_ALLOWED_SUBCOMMANDS
    return False


def _split_clauses(cmd: str) -> list[str]:
    """Split on compound operators and subshell boundaries."""
    parts = re.split(r"&&|\|\||[;|]", cmd)
    clauses: list[str] = []
    for part in parts:
        clauses.extend(re.split(r"[$()`]", part))
    return clauses


def _extract_git_verb(tokens: list[str]) -> str | None:
    """Extract the git subcommand verb, skipping global options."""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("-"):
            return tok
        if tok in _GIT_OPTS_WITH_ARG:
            i += 2
            continue
        i += 1
    return None


def _all_git_reads(scan: str) -> bool:
    """Return True only if every git invocation in scan is a read-only verb."""
    found_any = False
    for clause in _split_clauses(scan):
        for m in RAW_GIT_RE.finditer(clause):
            found_any = True
            after = clause[m.end() :].split()
            verb = _extract_git_verb(after)
            if verb is None or verb not in READ_ALLOWED_GIT_SUBCOMMANDS:
                return False
    return found_any


def _block(reason: str) -> dict:
    return {"stdout": json.dumps({"decision": "block", "reason": reason}), "exit_code": 2, "sound": "git gate"}


def _check_bash(tool_input: dict) -> dict:
    cmd = tool_input.get("command", "")
    if not cmd:
        return _BLOCK_ALLOW
    scan = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cmd)
    scan = re.sub(r"'(?:[^'\\]|\\.)*'", "''", scan)
    if RAW_GIT_RE.search(scan) and not _all_git_reads(scan):
        return _block(GIT_GH_REDIRECT)
    if RAW_GH_RE.search(scan) and not _is_allowed_gh(cmd):
        return _block(GIT_GH_REDIRECT)
    return _BLOCK_ALLOW


def _check_edit(tool_input: dict, cwd: str) -> dict:
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return _BLOCK_ALLOW
    for pat in BLOCKED_EDIT_PATTERNS:
        if pat.search(file_path):
            if _cwd_branch(cwd) in TRUSTED_HOOK_EDITORS:
                return _BLOCK_ALLOW
            return _block(EDIT_REDIRECT.format(path=file_path))
    return _BLOCK_ALLOW


def handle(hook_data: dict) -> dict:
    """Block raw git/gh commands and protected file edits.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (block JSON or empty) and exit_code.
    """
    try:
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})
        cwd = hook_data.get("cwd", "") or os.getcwd()
        if tool_name == "Bash":
            return _check_bash(tool_input)
        if tool_name in EDIT_TOOLS:
            return _check_edit(tool_input, cwd)
        return _BLOCK_ALLOW
    except Exception as exc:
        logger.info("[HOOKS] git_gate: unexpected error (allowing): %s", exc)
        return _BLOCK_ALLOW
