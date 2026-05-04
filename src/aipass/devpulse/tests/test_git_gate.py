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

HOOK_PATH = Path.home() / ".claude" / "hooks" / "git_gate.py"

_spec = importlib.util.spec_from_file_location("git_gate", HOOK_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BLOCKED_GIT_RE = _mod.BLOCKED_GIT_RE
BLOCKED_GIT_STASH_RE = _mod.BLOCKED_GIT_STASH_RE
BLOCKED_GH_RE = _mod.BLOCKED_GH_RE
BLOCKED_GH_API_RE = _mod.BLOCKED_GH_API_RE
BLOCKED_EDIT_PATTERNS = _mod.BLOCKED_EDIT_PATTERNS


class TestGitWriteBlocking:
    """Core git write verbs must be blocked."""

    @pytest.mark.parametrize("cmd", [
        "git commit -m 'test'",
        "git push origin main",
        "git pull",
        "git merge main",
        "git rebase main",
        "git reset HEAD~1",
        "git checkout -b new-branch",
        "git switch -c new-branch",
        "git branch -D old",
        "git cherry-pick abc123",
        "git revert HEAD",
        "git rm file.txt",
        "git mv old.py new.py",
        "git restore --staged file.py",
        "git clean -fd",
        "git config user.name 'x'",
        "git tag v1.0",
    ])
    def test_blocks_write_verbs(self, cmd):
        """Each blocked git verb triggers the regex."""
        assert BLOCKED_GIT_RE.search(cmd), f"Should block: {cmd}"

    @pytest.mark.parametrize("cmd", [
        "git stash drop",
        "git stash clear",
        "git stash pop",
        "git stash apply",
    ])
    def test_blocks_stash_destructive(self, cmd):
        """Destructive stash subcommands are blocked."""
        assert BLOCKED_GIT_STASH_RE.search(cmd), f"Should block: {cmd}"


class TestLongFormFlagBypass:
    """DPLAN-0163 Finding 1: long-form flags must not bypass detection."""

    @pytest.mark.parametrize("cmd", [
        "git --config core.hooksPath=/dev/null commit",
        "git --no-pager push",
        "git -c x=y commit",
        "git --git-dir=/x checkout",
        "git --config=core.hooksPath=/dev/null commit",
        "git --no-pager -c x=y push",
        "git --work-tree=/tmp commit -m 'x'",
        "git -C /some/path commit",
        "git --bare push origin main",
    ])
    def test_blocks_long_form_flag_bypass(self, cmd):
        """Long-form flags before the verb must not hide the write verb."""
        assert BLOCKED_GIT_RE.search(cmd), f"Should block: {cmd}"


class TestEscapedQuoteBypass:
    """DPLAN-0163 Finding 2: escaped quotes must not break quote-stripping.

    The gate strips quoted strings before scanning, so commit messages
    containing git verbs don't trigger false positives. Escaped quotes
    inside those strings must not break the stripping.
    """

    @pytest.mark.parametrize("cmd,should_block", [
        ('echo "git commit inside quotes"', False),
        ("echo 'git push inside single quotes'", False),
        ('echo "msg \\"escaped\\" inner"', False),
        ("echo 'msg \\'escaped\\' inner'", False),
        ('drone @git pr "fix: git commit msg"', False),
        ('git commit -m "msg \\"escaped\\""', True),
    ])
    def test_escaped_quote_stripping(self, cmd, should_block):
        """Escaped quotes inside strings must not leak verb matches."""
        scan = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cmd)
        scan = re.sub(r"'(?:[^'\\]|\\.)*'", "''", scan)
        matched = bool(BLOCKED_GIT_RE.search(scan))
        assert matched == should_block, (
            f"{'Should block' if should_block else 'Should allow'}: {cmd}\n"
            f"  After strip: {scan}"
        )


class TestReadOnlyAllowed:
    """Read-only git commands must not be blocked."""

    @pytest.mark.parametrize("cmd", [
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
    ])
    def test_allows_read_only(self, cmd):
        """Read-only git subcommands must pass through."""
        assert not BLOCKED_GIT_RE.search(cmd), f"Should allow: {cmd}"
        assert not BLOCKED_GIT_STASH_RE.search(cmd), f"Should allow: {cmd}"


class TestDroneNotBlocked:
    """Drone commands must never be blocked."""

    @pytest.mark.parametrize("cmd", [
        'drone @git pr "description"',
        'drone @git system-pr "fix"',
        "drone @git smart-sync",
        "drone @git sync",
        "drone @git status",
        "drone @git merge 42",
    ])
    def test_allows_drone(self, cmd):
        """Drone-wrapped git ops are not raw git — must pass."""
        assert not BLOCKED_GIT_RE.search(cmd), f"Should allow: {cmd}"


class TestGhBlocking:
    """gh write subcommands blocked, read-only allowed."""

    @pytest.mark.parametrize("cmd", [
        "gh pr create --title x",
        "gh pr merge 42",
        "gh pr close 42",
        "gh issue create",
        "gh issue close 5",
        "gh release create v1",
        "gh repo create x",
        "gh api repos/x/pulls",
    ])
    def test_blocks_gh_writes(self, cmd):
        """State-changing gh subcommands are blocked."""
        blocked = BLOCKED_GH_RE.search(cmd) or BLOCKED_GH_API_RE.search(cmd)
        assert blocked, f"Should block: {cmd}"

    @pytest.mark.parametrize("cmd", [
        "gh pr list",
        "gh pr view 42",
        "gh pr status",
        "gh pr diff 42",
        "gh pr checks 42",
        "gh issue list",
        "gh issue view 5",
        "gh issue status",
    ])
    def test_allows_gh_reads(self, cmd):
        """Read-only gh subcommands must pass through."""
        assert not BLOCKED_GH_RE.search(cmd), f"Should allow: {cmd}"
        assert not BLOCKED_GH_API_RE.search(cmd), f"Should allow: {cmd}"


class TestEditBlocking:
    """Protected file paths must be blocked by edit patterns."""

    @pytest.mark.parametrize("path", [
        "/home/user/.claude/settings.json",
        "/home/user/.claude/settings.local.json",
        "/home/user/.claude/hooks/git_gate.py",
        "/home/user/.claude/hooks/pre_edit_gate.py",
        "/repo/.git/hooks/pre-commit",
    ])
    def test_blocks_protected_paths(self, path):
        """Enforcement-layer files are protected from edits."""
        matched = any(p.search(path) for p in BLOCKED_EDIT_PATTERNS)
        assert matched, f"Should block edit: {path}"

    @pytest.mark.parametrize("path", [
        "/home/user/project/src/main.py",
        "/home/user/.claude/CLAUDE.md",
        "/home/user/project/.git/config",
        "/home/user/project/src/aipass/devpulse/apps/handler.py",
    ])
    def test_allows_normal_paths(self, path):
        """Normal project files are not blocked."""
        matched = any(p.search(path) for p in BLOCKED_EDIT_PATTERNS)
        assert not matched, f"Should allow edit: {path}"


# =============================================
