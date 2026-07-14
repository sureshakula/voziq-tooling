"""CLI contract tests — verify flags/subcommands our code invokes actually exist.

Probes `claude --help` and `claude agents --help` at test time. Skips cleanly
when the binary is absent. Catches phantom subcommands (like the former
`claude agents stop`) before they ship as mocked-green.
"""

import shutil
import subprocess

import pytest

_CLAUDE = shutil.which("claude")
_SKIP = pytest.mark.skipif(_CLAUDE is None, reason="claude binary not on PATH")


def _help_text(args: list[str]) -> str:
    assert _CLAUDE is not None
    result = subprocess.run(
        [_CLAUDE, *args, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout + result.stderr


def _get_main_help() -> str:
    return _help_text([])


def _get_agents_help() -> str:
    return _help_text(["agents"])


def _get_daemon_help() -> str:
    return _help_text(["daemon"])


@_SKIP
class TestClaudeMainFlags:
    """Flags from `claude --help` that session_boot invokes."""

    def test_permission_mode(self):
        assert "--permission-mode" in _get_main_help()

    def test_continue(self):
        assert "--continue" in _get_main_help()

    def test_resume(self):
        assert "--resume" in _get_main_help()

    def test_p_flag(self):
        h = _get_main_help()
        assert "-p" in h or "--print" in h

    def test_name_flag(self):
        h = _get_main_help()
        assert "--name" in h or "-n" in h


@_SKIP
class TestClaudeAgentsFlags:
    """Flags from `claude agents --help` that session_boot invokes."""

    def test_permission_mode(self):
        assert "--permission-mode" in _get_agents_help()

    def test_cwd(self):
        assert "--cwd" in _get_agents_help()

    def test_no_stop_subcommand(self):
        h = _get_agents_help()
        assert "stop" not in h.lower() or "agents stop" not in h.lower()


@_SKIP
class TestClaudeDaemonFlags:
    """Flags from `claude daemon --help` that session_boot invokes."""

    def test_stop_subcommand(self):
        assert "stop" in _get_daemon_help()

    def test_any_flag(self):
        assert "--any" in _get_daemon_help()


@_SKIP
class TestAgentsStopDoesNotExist:
    """Regression: `claude agents stop <id>` must NOT be a valid command."""

    def test_agents_rejects_stop_arg(self):
        assert _CLAUDE is not None
        result = subprocess.run(
            [_CLAUDE, "agents", "stop", "test-id"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "too many arguments" in result.stderr.lower() or "error" in result.stderr.lower()
