# =================== AIPass ====================
# Name: test_git_gate.py
# Description: Regex coverage for git_gate.py hook (DPLAN-0163)
# Version: 1.0.0
# Created: 2026-05-03
# Modified: 2026-05-03
# =============================================

"""Tests for git_gate.py — PreToolUse hook blocking raw git/gh writes.

NOTE: This test imports git_gate.py from ~/.claude/hooks/ (outside
the branch tree). This is intentional — git_gate is a user-level
hook, not a branch module, so there is no aipass package path for it.
"""

import importlib.util
import re
from pathlib import Path

import pytest

_REPO_HOOK = Path(__file__).resolve().parents[4] / ".claude" / "hooks" / "git_gate.py"
_USER_HOOK = Path.home() / ".claude" / "hooks" / "git_gate.py"
HOOK_PATH = _REPO_HOOK if _REPO_HOOK.is_file() else _USER_HOOK

_spec = importlib.util.spec_from_file_location("git_gate", HOOK_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BLOCKED_GIT_RE = _mod.BLOCKED_GIT_RE
BLOCKED_GIT_STASH_RE = _mod.BLOCKED_GIT_STASH_RE
BLOCKED_GIT_BRANCH_RE = _mod.BLOCKED_GIT_BRANCH_RE
BLOCKED_GIT_TAG_RE = _mod.BLOCKED_GIT_TAG_RE
BLOCKED_GIT_REMOTE_RE = _mod.BLOCKED_GIT_REMOTE_RE
BLOCKED_GH_RE = _mod.BLOCKED_GH_RE
BLOCKED_GH_API_RE = _mod.BLOCKED_GH_API_RE
BLOCKED_EDIT_PATTERNS = _mod.BLOCKED_EDIT_PATTERNS


class TestGitWriteBlocking:
    """Core git write verbs must be blocked."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "git commit -m 'test'",
            "git push origin main",
            "git pull",
            "git merge main",
            "git rebase main",
            "git reset HEAD~1",
            "git checkout -b new-branch",
            "git switch -c new-branch",
            "git cherry-pick abc123",
            "git revert HEAD",
            "git rm file.txt",
            "git mv old.py new.py",
            "git restore --staged file.py",
            "git clean -fd",
            "git config user.name 'x'",
        ],
    )
    def test_blocks_write_verbs(self, cmd):
        """Each blocked git verb triggers the regex."""
        assert BLOCKED_GIT_RE.search(cmd), f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "git stash drop",
            "git stash clear",
            "git stash pop",
            "git stash apply",
        ],
    )
    def test_blocks_stash_destructive(self, cmd):
        """Destructive stash subcommands are blocked."""
        assert BLOCKED_GIT_STASH_RE.search(cmd), f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "git branch -D old",
            "git branch -d old",
            "git branch -m old new",
            "git branch -M old new",
            "git branch -c old new",
            "git branch --delete old",
            "git branch --move old new",
            "git branch --copy old new",
            "git branch --force old",
            "git branch --set-upstream-to=origin/main",
            "git branch --unset-upstream",
        ],
    )
    def test_blocks_branch_destructive(self, cmd):
        """Destructive branch subcommands are blocked."""
        assert BLOCKED_GIT_BRANCH_RE.search(cmd), f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "git tag -d v1.0",
            "git tag --delete v1.0",
            "git tag -f v1.0",
            "git tag --force v1.0",
        ],
    )
    def test_blocks_tag_destructive(self, cmd):
        """Destructive tag operations are blocked."""
        assert BLOCKED_GIT_TAG_RE.search(cmd), f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "git remote add origin url",
            "git remote remove origin",
            "git remote rename old new",
            "git remote set-url origin url",
            "git remote prune origin",
        ],
    )
    def test_blocks_remote_destructive(self, cmd):
        """Destructive remote operations are blocked."""
        assert BLOCKED_GIT_REMOTE_RE.search(cmd), f"Should block: {cmd}"


class TestLongFormFlagBypass:
    """DPLAN-0163 Finding 1: long-form flags must not bypass detection."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "git --config core.hooksPath=/dev/null commit",
            "git --no-pager push",
            "git -c x=y commit",
            "git --git-dir=/x checkout",
            "git --config=core.hooksPath=/dev/null commit",
            "git --no-pager -c x=y push",
            "git --work-tree=/tmp commit -m 'x'",
            "git -C /some/path commit",
            "git --bare push origin main",
        ],
    )
    def test_blocks_long_form_flag_bypass(self, cmd):
        """Long-form flags before the verb must not hide the write verb."""
        assert BLOCKED_GIT_RE.search(cmd), f"Should block: {cmd}"


class TestEscapedQuoteBypass:
    """DPLAN-0163 Finding 2: escaped quotes must not break quote-stripping.

    The gate strips quoted strings before scanning, so commit messages
    containing git verbs don't trigger false positives. Escaped quotes
    inside those strings must not break the stripping.
    """

    @pytest.mark.parametrize(
        "cmd,should_block",
        [
            ('echo "git commit inside quotes"', False),
            ("echo 'git push inside single quotes'", False),
            ('echo "msg \\"escaped\\" inner"', False),
            ("echo 'msg \\'escaped\\' inner'", False),
            ('drone @git pr "fix: git commit msg"', False),
            ('git commit -m "msg \\"escaped\\""', True),
        ],
    )
    def test_escaped_quote_stripping(self, cmd, should_block):
        """Escaped quotes inside strings must not leak verb matches."""
        scan = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cmd)
        scan = re.sub(r"'(?:[^'\\]|\\.)*'", "''", scan)
        matched = bool(BLOCKED_GIT_RE.search(scan))
        assert matched == should_block, (
            f"{'Should block' if should_block else 'Should allow'}: {cmd}\n  After strip: {scan}"
        )


class TestReadOnlyAllowed:
    """Read-only git commands must not be blocked."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "git status",
            "git log --oneline",
            "git diff",
            "git diff --staged",
            "git show HEAD",
            "git fetch",
            "git fetch origin",
            "git ls-files",
            "git log --graph --all",
            "git stash list",
            "git stash show",
            "git rev-parse HEAD",
            "git describe --tags",
            "git remote -v",
            "git blame file.py",
            "git shortlog -sn",
            "git branch",
            "git branch -r",
            "git branch -a",
            "git branch --list",
            "git branch -v",
            "git branch --show-current",
            "git branch --contains abc123",
            "git tag",
            "git tag -l",
            "git tag --list",
            "git remote",
            "git remote show origin",
        ],
    )
    def test_allows_read_only(self, cmd):
        """Read-only git subcommands must pass through."""
        assert not BLOCKED_GIT_RE.search(cmd), f"Should allow: {cmd}"
        assert not BLOCKED_GIT_STASH_RE.search(cmd), f"Should allow: {cmd}"
        assert not BLOCKED_GIT_BRANCH_RE.search(cmd), f"Should allow: {cmd}"
        assert not BLOCKED_GIT_TAG_RE.search(cmd), f"Should allow: {cmd}"
        assert not BLOCKED_GIT_REMOTE_RE.search(cmd), f"Should allow: {cmd}"


class TestDroneNotBlocked:
    """Drone commands must never be blocked."""

    @pytest.mark.parametrize(
        "cmd",
        [
            'drone @git pr "description"',
            'drone @git system-pr "fix"',
            "drone @git smart-sync",
            "drone @git sync",
            "drone @git status",
            "drone @git merge 42",
        ],
    )
    def test_allows_drone(self, cmd):
        """Drone-wrapped git ops are not raw git — must pass."""
        assert not BLOCKED_GIT_RE.search(cmd), f"Should allow: {cmd}"


class TestGhBlocking:
    """gh write subcommands blocked, read-only allowed."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "gh pr create --title x",
            "gh pr merge 42",
            "gh pr close 42",
            "gh issue create",
            "gh issue close 5",
            "gh release create v1",
            "gh repo create x",
            "gh api repos/x/pulls -X POST",
        ],
    )
    def test_blocks_gh_writes(self, cmd):
        """State-changing gh subcommands are blocked."""
        blocked = BLOCKED_GH_RE.search(cmd) or BLOCKED_GH_API_RE.search(cmd)
        assert blocked, f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "gh pr list",
            "gh pr view 42",
            "gh pr status",
            "gh pr diff 42",
            "gh pr checks 42",
            "gh issue list",
            "gh issue view 5",
            "gh issue status",
        ],
    )
    def test_allows_gh_reads(self, cmd):
        """Read-only gh subcommands must pass through."""
        assert not BLOCKED_GH_RE.search(cmd), f"Should allow: {cmd}"
        assert not BLOCKED_GH_API_RE.search(cmd), f"Should allow: {cmd}"


class TestEditBlocking:
    """Protected file paths must be blocked by edit patterns."""

    @pytest.mark.parametrize(
        "path",
        [
            "/home/user/.claude/settings.json",
            "/home/user/.claude/settings.local.json",
            "/home/user/.claude/hooks/git_gate.py",
            "/home/user/.claude/hooks/pre_edit_gate.py",
            "/repo/.git/hooks/pre-commit",
        ],
    )
    def test_blocks_protected_paths(self, path):
        """Enforcement-layer files are protected from edits."""
        matched = any(p.search(path) for p in BLOCKED_EDIT_PATTERNS)
        assert matched, f"Should block edit: {path}"

    @pytest.mark.parametrize(
        "path",
        [
            "/home/user/project/src/main.py",
            "/home/user/.claude/CLAUDE.md",
            "/home/user/project/.git/config",
            "/home/user/project/src/aipass/devpulse/apps/handler.py",
        ],
    )
    def test_allows_normal_paths(self, path):
        """Normal project files are not blocked."""
        matched = any(p.search(path) for p in BLOCKED_EDIT_PATTERNS)
        assert not matched, f"Should allow edit: {path}"


_PY3 = "python3"


class TestBypassDetection:
    """Issue #561: bypass vectors that circumvent regex scanning."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        """Create test script files for bypass detection tests."""
        self.gate = HOOK_PATH
        self.cwd = str(tmp_path)
        evil_sh = tmp_path / "evil.sh"
        evil_sh.write_text("#!/bin/bash\ngit commit -m hack\ngit push\n", encoding="utf-8")
        self.evil_sh = str(evil_sh)
        evil_py = tmp_path / "evil.py"
        evil_py.write_text("import subprocess\nsubprocess.run(['git','push'])\n", encoding="utf-8")
        self.evil_py = str(evil_py)
        safe_sh = tmp_path / "safe.sh"
        safe_sh.write_text("#!/bin/bash\necho hello\nls -la\n", encoding="utf-8")
        self.safe_sh = str(safe_sh)

    def _run(self, cmd):
        """Pipe a command to git_gate.py and return exit code."""
        import json
        import subprocess
        import sys

        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": self.cwd})
        result = subprocess.run(
            [sys.executable, str(self.gate)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode

    @pytest.mark.parametrize(
        "cmd",
        [
            f"{_PY3} -c \"import subprocess; subprocess.run(['git','commit'])\"",
            f"{_PY3} -c \"import os; os.system('git push')\"",
            f"{_PY3} -c \"from subprocess import Popen; Popen(['gh','pr','create'])\"",
            f"{_PY3} -c \"from os import popen; popen('git merge')\"",
            f"{_PY3} -c \"from os import system; system('git push')\"",
        ],
    )
    def test_blocks_subprocess_bypass(self, cmd):
        """Subprocess wrapping git/gh is detected and blocked."""
        assert self._run(cmd) == 2, f"Should block subprocess bypass: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "/usr/bin/git commit -m test",
            "/usr/local/bin/git push",
            "/snap/bin/gh pr create --title x",
        ],
    )
    def test_blocks_full_path_bypass(self, cmd):
        """Full binary paths to git/gh are detected and blocked."""
        assert self._run(cmd) == 2, f"Should block full path: {cmd}"

    def test_blocks_bash_script_with_git(self):
        """Script containing git commands is blocked when run via bash."""
        assert self._run(f"bash {self.evil_sh}") == 2

    def test_blocks_sh_script_with_git(self):
        """Script containing git commands is blocked when run via sh."""
        assert self._run(f"sh {self.evil_sh}") == 2

    def test_blocks_source_script_with_git(self):
        """Script containing git commands is blocked when sourced."""
        assert self._run(f"source {self.evil_sh}") == 2

    def test_blocks_dot_source_script_with_git(self):
        """Script containing git commands is blocked via dot-source."""
        assert self._run(f". {self.evil_sh}") == 2

    def test_blocks_python_script_with_git(self):
        """Python script containing subprocess+git is blocked."""
        assert self._run(f"{_PY3} {self.evil_py}") == 2

    def test_blocks_cat_pipe_bash(self):
        """Piping script contents to bash is detected and blocked."""
        assert self._run(f"cat {self.evil_sh} | bash") == 2

    def test_blocks_bash_stdin_redirect(self):
        """Stdin redirect to bash is detected and blocked."""
        assert self._run(f"bash < {self.evil_sh}") == 2

    def test_blocks_xargs_git(self):
        """Using xargs to construct git commands is blocked."""
        assert self._run("echo commit | xargs git") == 2

    def test_blocks_variable_expansion(self):
        """Variable assignment of git followed by execution is blocked."""
        assert self._run("cmd=git; $cmd commit -m test") == 2

    def test_allows_safe_script(self):
        """Script without git commands passes through."""
        assert self._run(f"bash {self.safe_sh}") == 0

    def test_allows_subprocess_no_git(self):
        """Subprocess calls without git/gh are allowed."""
        assert self._run(f"{_PY3} -c \"import subprocess; subprocess.run(['ls'])\"") == 0

    def test_allows_read_only_full_path(self):
        """Read-only git via full path is allowed."""
        assert self._run("/usr/bin/git log --oneline") == 0

    def test_allows_nonexistent_script(self):
        """Nonexistent script passes through gracefully."""
        assert self._run("bash /tmp/nonexistent_xyz.sh") == 0

    def test_allows_echo(self):
        """Normal commands without git are allowed."""
        assert self._run("echo hello world") == 0


# =============================================
