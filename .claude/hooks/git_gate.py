#!/usr/bin/env python3
"""PreToolUse Gate — blocks raw git/gh writes + edits to settings/hooks files.

Dispatched agents spawn with --permission-mode bypassPermissions, which skips
all permissions.deny rules in every settings tier. PreToolUse hooks remain the
only mechanical chokepoint that survives. This hook gates the dangerous
shortcuts and redirects callers to drone.

Allows: read-only git/gh, all unrelated tool calls, devpulse-from-its-own-branch
        edits to the enforcement layer itself.
Blocks: git write verbs, gh state-changing subcommands, edits to .claude
        settings.json / hooks/ and .git/hooks/.

DPLAN-0162.
"""

import json
import os
import re
import sys
from pathlib import Path

BLOCKED_GIT_VERBS = (
    "commit",
    "push",
    "pull",
    "merge",
    "rebase",
    "reset",
    "checkout",
    "switch",
    "cherry-pick",
    "revert",
    "rm",
    "mv",
    "restore",
    "clean",
    "config",
)

BLOCKED_GIT_RE = re.compile(
    r"(?<![@\w/.])git\s+(?:--?[A-Za-z][A-Za-z0-9_-]*(?:[= ][^\s]+)?\s+)*"
    r"(" + "|".join(BLOCKED_GIT_VERBS) + r")\b"
)

# Full binary path bypass: /usr/bin/git, /usr/local/bin/git, ./git, etc.
BLOCKED_GIT_PATH_RE = re.compile(
    r"/git\s+(?:--?[A-Za-z][A-Za-z0-9_-]*(?:[= ][^\s]+)?\s+)*"
    r"(" + "|".join(BLOCKED_GIT_VERBS) + r")\b"
)

BLOCKED_GIT_STASH_RE = re.compile(r"(?<![@\w/.])git\s+stash\s+(drop|clear|pop|apply)\b")

BLOCKED_GIT_BRANCH_RE = re.compile(
    r"(?<![@\w/.])git\s+branch\s+.*(-[dDmMcC]\b|--delete|--move|--copy|--force|--set-upstream-to|--unset-upstream)"
)

BLOCKED_GIT_TAG_RE = re.compile(r"(?<![@\w/.])git\s+tag\s+.*(-d\b|--delete|--force|-f\b)")

BLOCKED_GIT_REMOTE_RE = re.compile(
    r"(?<![@\w/.])git\s+remote\s+(add|remove|rename|set-url|set-branches|set-head|prune)\b"
)

BLOCKED_GH_API_RE = re.compile(
    r"(?<![@\w/.])gh\s+api\b.*("
    r"-X\s+(POST|PUT|PATCH|DELETE)"
    r"|--method\s+(POST|PUT|PATCH|DELETE)"
    r"|-f\b|--field\b|-F\b|--raw-field\b|--input\b"
    r")"
)

BLOCKED_GH_RE = re.compile(
    r"(?<![@\w/.])gh\s+(pr|issue|repo|release|workflow|run|cache|secret|variable|gist)"
    r"\s+(?!list\b|view\b|status\b|diff\b|checks\b|comments\b)\w[\w-]*"
)

# Full binary path for gh: /usr/bin/gh, /usr/local/bin/gh, etc.
BLOCKED_GH_PATH_RE = re.compile(
    r"/gh\s+(pr|issue|repo|release|workflow|run|cache|secret|variable|gist)"
    r"\s+(?!list\b|view\b|status\b|diff\b|checks\b|comments\b)\w[\w-]*"
)

BLOCKED_EDIT_PATTERNS = [
    re.compile(r"/\.claude/settings(\.local)?\.json$"),
    re.compile(r"/\.claude/hooks/"),
    re.compile(r"/\.git/hooks/"),
]

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Branches trusted to edit the enforcement layer itself (mirrors pre_edit_gate).
TRUSTED_HOOK_EDITORS = ("devpulse", "seedgo")

GIT_REDIRECT = (
    "Raw git write commands are blocked. Use drone instead:\n"
    "  drone @git status                   # what changed\n"
    "  drone @git diff                     # see changes\n"
    "  drone @git log                      # commit history\n"
    "  drone @git commit 'msg' --all       # commit all changes (devpulse only)\n"
    '  drone @git dev-pr "description"     # PR dev to main (devpulse only)\n'
    "  drone @git smart-sync               # fetch + rebase\n"
    "Read-only git (status, log, diff, show, fetch, ls-files) is allowed."
)

GH_REDIRECT = (
    "Raw gh write commands are blocked. Use drone for git ops:\n"
    '  drone @git dev-pr "description"     # PR dev to main\n'
    "  drone @git merge <PR#>              # merge a PR (devpulse only)\n"
    "  drone @git issue list/create/view   # gh issue passthrough\n"
    "Read-only gh (list, view, status, diff, checks, comments) is allowed."
)

EDIT_REDIRECT = (
    "{path} is protected — settings.json, .claude/hooks/, and .git/hooks/ "
    "govern the enforcement layer itself.\n"
    "If a real change is needed, ask devpulse to make it directly."
)


def _block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def _cwd_branch(cwd: str) -> str:
    """Extract AIPass branch name from CWD (src/aipass/{branch}/ pattern)."""
    parts = Path(cwd).parts
    for i, part in enumerate(parts):
        if part == "aipass" and i > 0 and parts[i - 1] == "src" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def _is_project_owner(cwd: str) -> bool:
    """Check if the current branch's passport has citizenship.owner: true."""
    p = Path(cwd)
    for d in [p] + list(p.parents):
        passport = d / ".trinity" / "passport.json"
        if passport.is_file():
            try:
                data = json.loads(passport.read_text(encoding="utf-8"))
                return bool(data.get("citizenship", {}).get("owner"))
            except Exception:
                return False
        if (d / ".git").exists():
            break
    return False


def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        cwd = data.get("cwd") or os.getcwd()

        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            if not cmd:
                return

            # Subprocess bypass detection — scan raw command for git/gh inside
            # subprocess/os execution patterns before stripping quotes.
            if re.search(r"subprocess\.\w+|os\.system|os\.popen|Popen|(?<!\w)popen\s*\(|(?<!\w)system\s*\(", cmd):
                if re.search(r"\bgit\b|\bgh\b", cmd):
                    _block(GIT_REDIRECT)

            # Script-file bypass detection — read file contents when an interpreter runs a file.
            script_match = re.search(
                r"(?:^|[;&|]\s*)(?:bash|sh|source|python3?|\.)\s+([^\s;&|]+)", cmd
            )
            if script_match:
                script_path = script_match.group(1)
                if not script_path.startswith("-"):
                    if not os.path.isabs(script_path):
                        script_path = os.path.join(cwd, script_path)
                    try:
                        content = Path(script_path).read_text(encoding="utf-8", errors="ignore")
                        if BLOCKED_GIT_RE.search(content) or BLOCKED_GIT_PATH_RE.search(content):
                            _block(GIT_REDIRECT)
                        if re.search(r"\bgit\b|\bgh\b", content):
                            if re.search(r"subprocess|os\.system|os\.popen|Popen", content):
                                _block(GIT_REDIRECT)
                        if BLOCKED_GH_RE.search(content) or BLOCKED_GH_PATH_RE.search(content):
                            if not (_cwd_branch(cwd) in TRUSTED_HOOK_EDITORS or _is_project_owner(cwd)):
                                _block(GH_REDIRECT)
                    except (OSError, UnicodeDecodeError):
                        pass

            # Pipe-to-shell and stdin redirect: cat file | bash, bash < file
            pipe_match = re.search(r"(?:cat|head|tail)\s+([^\s;&|]+)\s*\|\s*(?:bash|sh)\b", cmd)
            if not pipe_match:
                pipe_match = re.search(r"(?:bash|sh)\s*<\s*([^\s;&|]+)", cmd)
            if pipe_match:
                piped_path = pipe_match.group(1)
                if not os.path.isabs(piped_path):
                    piped_path = os.path.join(cwd, piped_path)
                try:
                    content = Path(piped_path).read_text(encoding="utf-8", errors="ignore")
                    if BLOCKED_GIT_RE.search(content) or BLOCKED_GIT_PATH_RE.search(content):
                        _block(GIT_REDIRECT)
                except (OSError, UnicodeDecodeError):
                    pass

            # xargs with git/gh — command construction bypass
            if re.search(r"\bxargs\b.*\bgit\b|\bxargs\b.*\bgh\b", cmd):
                _block(GIT_REDIRECT)

            # Variable assignment bypass: cmd=git; $cmd commit
            if re.search(r"=\s*git\b|=\s*gh\b", cmd):
                if re.search(r"\$\w*\s+" + "(" + "|".join(BLOCKED_GIT_VERBS) + ")", cmd):
                    _block(GIT_REDIRECT)

            # Strip quoted strings before matching — text inside "..." or '...' is data
            # (PR descriptions, commit messages, examples in docs), not code to enforce.
            scan = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cmd)
            scan = re.sub(r"'(?:[^'\\]|\\.)*'", "''", cmd)
            if (
                BLOCKED_GIT_RE.search(scan)
                or BLOCKED_GIT_PATH_RE.search(scan)
                or BLOCKED_GIT_STASH_RE.search(scan)
                or BLOCKED_GIT_BRANCH_RE.search(scan)
                or BLOCKED_GIT_TAG_RE.search(scan)
                or BLOCKED_GIT_REMOTE_RE.search(scan)
            ):
                _block(GIT_REDIRECT)
            if BLOCKED_GH_API_RE.search(scan) or BLOCKED_GH_RE.search(scan) or BLOCKED_GH_PATH_RE.search(scan):
                if not (_cwd_branch(cwd) in TRUSTED_HOOK_EDITORS or _is_project_owner(cwd)):
                    _block(GH_REDIRECT)
            return

        if tool_name in EDIT_TOOLS:
            file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
            if not file_path:
                return
            for pat in BLOCKED_EDIT_PATTERNS:
                if pat.search(file_path):
                    # Trusted-editor bypass: devpulse working from its own branch
                    # is the maintainer of the enforcement layer.
                    if _cwd_branch(cwd) in TRUSTED_HOOK_EDITORS:
                        return
                    _block(EDIT_REDIRECT.format(path=file_path))
            return

    except Exception:
        return


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hook_log import run_and_log

    run_and_log("PreToolUse", "provider", __file__, main)
