# =================== AIPass ====================
# Name: test_presence_pointer.py
# Description: Tests for FPLAN-0289 P2 — bot follows central presence pointer, never spawns
# Version: 1.0.0
# Created: 2026-06-29
# Modified: 2026-06-29
# =============================================

"""
Tests for the presence pointer integration (FPLAN-0289 P2).

Covers:
  - _find_presence_file: walks up from work_dir to locate PRESENCE.central.json
  - _read_presence_pointer: reads pointer, validates PID liveness, returns entry
  - _find_tmux_for_presence: attach_handle preference, tmux CWD scan fallback
  - ensure_tmux_session: presence-first resolution, legacy spawn retired
  - handle_message: no-session error message
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from apps.handlers.base_bot import BaseBot  # type: ignore[import-not-found]


# =============================================
# Fixtures
# =============================================


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
    """Patch signal and atexit for safe BaseBot construction."""
    patches = [
        patch("apps.handlers.base_bot.PENDING_DIR", tmp_path),
        patch("apps.handlers.base_bot.signal.signal"),
        patch("apps.handlers.base_bot.atexit.register"),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


def _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse"):
    """Create a BaseBot with test defaults."""
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    with patch("apps.handlers.base_bot.PENDING_DIR", tmp_path):
        bot = BaseBot(
            bot_id="presence_test",
            bot_token="123:FAKETOKEN",
            work_dir=workdir,
            bot_name="Presence Test Bot",
            allowed_user_ids=[111],
            branch_name=branch_name,
        )
    bot.send_message = MagicMock(return_value={"ok": True, "message_id": 1})
    return bot


def _write_presence(tmp_path, data):
    """Write a PRESENCE.central.json reachable from bot's work_dir."""
    ai_central = tmp_path / ".ai_central"
    ai_central.mkdir(exist_ok=True)
    presence_file = ai_central / "PRESENCE.central.json"
    presence_file.write_text(json.dumps(data), encoding="utf-8")
    return presence_file


# =============================================
# 1. _find_presence_file
# =============================================


class TestFindPresenceFile:
    """Locate PRESENCE.central.json by walking up from work_dir."""

    def test_finds_file_in_parent(self, tmp_path, _patch_base_bot_deps):
        """Finds PRESENCE.central.json in parent of work_dir."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        _write_presence(tmp_path, {})
        result = bot._find_presence_file()
        assert result is not None
        assert result.name == "PRESENCE.central.json"

    def test_returns_none_when_absent(self, tmp_path, _patch_base_bot_deps):
        """Returns None when no .ai_central/ exists."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._find_presence_file()
        assert result is None

    def test_walks_up_multiple_levels(self, tmp_path, _patch_base_bot_deps):
        """Walks up multiple parent directories to find .ai_central/."""
        deep_dir = tmp_path / "a" / "b" / "c" / "workdir"
        deep_dir.mkdir(parents=True)
        _write_presence(tmp_path, {})
        with patch("apps.handlers.base_bot.PENDING_DIR", tmp_path):
            bot = BaseBot(
                bot_id="deep_test",
                bot_token="t",
                work_dir=deep_dir,
                branch_name="test",
            )
        result = bot._find_presence_file()
        assert result is not None


# =============================================
# 2. _read_presence_pointer
# =============================================


class TestReadPresencePointer:
    """Read pointer, validate PID liveness, return entry or None."""

    def test_returns_entry_for_live_pid(self, tmp_path, _patch_base_bot_deps):
        """Returns entry dict when PID is alive."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        my_pid = os.getpid()
        _write_presence(
            tmp_path,
            {
                "devpulse": {
                    "pid": my_pid,
                    "session_id": "sess1",
                    "work_dir": str(tmp_path),
                    "session_type": "interactive",
                    "attach_handle": "",
                    "started": "2026-06-29T10:00:00",
                    "last_seen": "2026-06-29T10:01:00",
                }
            },
        )
        result = bot._read_presence_pointer()
        assert result is not None
        assert result["pid"] == my_pid
        assert result["session_type"] == "interactive"

    def test_returns_none_for_dead_pid(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the recorded PID is not running."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        _write_presence(
            tmp_path,
            {
                "devpulse": {
                    "pid": 99999999,
                    "work_dir": str(tmp_path),
                }
            },
        )
        result = bot._read_presence_pointer()
        assert result is None

    def test_returns_none_when_branch_missing(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the bot's branch has no entry."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse")
        _write_presence(tmp_path, {"other_branch": {"pid": os.getpid(), "work_dir": str(tmp_path)}})
        result = bot._read_presence_pointer()
        assert result is None

    def test_returns_none_when_file_empty(self, tmp_path, _patch_base_bot_deps):
        """Returns None when presence file is empty JSON object."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        _write_presence(tmp_path, {})
        result = bot._read_presence_pointer()
        assert result is None

    def test_returns_none_when_no_presence_file(self, tmp_path, _patch_base_bot_deps):
        """Returns None when no PRESENCE.central.json exists."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._read_presence_pointer()
        assert result is None

    def test_returns_none_when_corrupt_json(self, tmp_path, _patch_base_bot_deps):
        """Returns None when presence file contains invalid JSON."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        ai_central = tmp_path / ".ai_central"
        ai_central.mkdir()
        (ai_central / "PRESENCE.central.json").write_text("not json!", encoding="utf-8")
        result = bot._read_presence_pointer()
        assert result is None

    def test_returns_none_when_no_pid(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the entry has no pid field."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        _write_presence(tmp_path, {"devpulse": {"work_dir": str(tmp_path)}})
        result = bot._read_presence_pointer()
        assert result is None

    def test_uses_work_dir_name_when_no_branch_name(self, tmp_path, _patch_base_bot_deps):
        """Falls back to work_dir.name as branch key when branch_name is None."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse")
        bot.branch_name = None
        workdir_name = bot.work_dir.name
        _write_presence(tmp_path, {workdir_name: {"pid": os.getpid(), "work_dir": str(tmp_path)}})
        result = bot._read_presence_pointer()
        assert result is not None

    def test_permission_error_treats_as_alive(self, tmp_path, _patch_base_bot_deps):
        """PermissionError on os.kill means process exists — treat as alive."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        _write_presence(tmp_path, {"devpulse": {"pid": 1, "work_dir": str(tmp_path)}})
        with patch("os.kill", side_effect=PermissionError("denied")):
            result = bot._read_presence_pointer()
        assert result is not None


# =============================================
# 3. _find_tmux_for_presence
# =============================================


class TestFindTmuxForPresence:
    """Find tmux session via attach_handle or CWD scan."""

    def test_uses_attach_handle_when_present(self, tmp_path, _patch_base_bot_deps):
        """Returns attach_handle directly when the tmux session exists."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        entry = {"attach_handle": "my-session", "work_dir": str(tmp_path)}
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = bot._find_tmux_for_presence(entry)
        assert result == "my-session"

    def test_attach_handle_falls_back_on_missing_session(self, tmp_path, _patch_base_bot_deps):
        """Falls back to CWD scan when attach_handle session doesn't exist."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        entry = {"attach_handle": "dead-session", "work_dir": str(tmp_path)}

        def _side_effect(cmd, **kwargs):
            mock = MagicMock()
            if "has-session" in cmd:
                mock.returncode = 1
            elif "list-panes" in cmd:
                mock.returncode = 0
                mock.stdout = f"live-session:{tmp_path}\n"
            return mock

        with patch("subprocess.run", side_effect=_side_effect):
            result = bot._find_tmux_for_presence(entry)
        assert result == "live-session"

    def test_cwd_scan_matches_work_dir(self, tmp_path, _patch_base_bot_deps):
        """CWD scan finds the session whose pane path matches work_dir."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        entry = {"attach_handle": "", "work_dir": str(tmp_path / "workdir")}
        pane_output = f"dev-session:{tmp_path / 'workdir'}\nother:{tmp_path / 'other'}\n"
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout=pane_output),
        ):
            result = bot._find_tmux_for_presence(entry)
        assert result == "dev-session"

    def test_returns_none_when_no_match(self, tmp_path, _patch_base_bot_deps):
        """Returns None when no tmux pane CWD matches the work_dir."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        entry = {"attach_handle": "", "work_dir": "/no/such/dir"}
        pane_output = f"session1:{tmp_path}\n"
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout=pane_output),
        ):
            result = bot._find_tmux_for_presence(entry)
        assert result is None

    def test_returns_none_when_no_work_dir(self, tmp_path, _patch_base_bot_deps):
        """Returns None immediately when work_dir is empty."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        entry = {"attach_handle": "", "work_dir": ""}
        result = bot._find_tmux_for_presence(entry)
        assert result is None

    def test_returns_none_when_tmux_unavailable(self, tmp_path, _patch_base_bot_deps):
        """Returns None when tmux is not installed."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        entry = {"attach_handle": "", "work_dir": str(tmp_path)}
        with patch("subprocess.run", side_effect=FileNotFoundError("tmux")):
            result = bot._find_tmux_for_presence(entry)
        assert result is None

    def test_empty_attach_handle_skipped(self, tmp_path, _patch_base_bot_deps):
        """Empty attach_handle skips has-session check, goes straight to CWD scan."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        entry = {"attach_handle": "", "work_dir": str(tmp_path / "workdir")}
        pane_output = f"found:{tmp_path / 'workdir'}\n"
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout=pane_output),
        ):
            result = bot._find_tmux_for_presence(entry)
        assert result == "found"


# =============================================
# 4. ensure_tmux_session — presence-first
# =============================================


class TestEnsureWithPresence:
    """ensure_tmux_session follows presence pointer first."""

    def test_attaches_via_presence_pointer(self, tmp_path, _patch_base_bot_deps):
        """Attaches to live session found via presence pointer."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        _write_presence(
            tmp_path,
            {
                "devpulse": {
                    "pid": os.getpid(),
                    "work_dir": str(tmp_path / "workdir"),
                    "session_type": "interactive",
                    "attach_handle": "live-session",
                }
            },
        )
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = bot.ensure_tmux_session()
        assert result is True
        assert bot.session_name == "live-session"
        assert bot._using_shared_session is True

    def test_presence_fallback_to_shared_session(self, tmp_path, _patch_base_bot_deps):
        """When presence pointer is empty, falls back to shared_session config."""
        workdir = tmp_path / "workdir"
        workdir.mkdir(exist_ok=True)
        _write_presence(tmp_path, {})
        with patch("apps.handlers.base_bot.PENDING_DIR", tmp_path):
            bot = BaseBot(
                bot_id="fb_test",
                bot_token="t",
                work_dir=workdir,
                branch_name="devpulse",
                shared_session="explicit-session",
            )
        bot.send_message = MagicMock()
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = bot.ensure_tmux_session()
        assert result is True
        assert bot.session_name == "explicit-session"

    def test_no_session_returns_false_never_spawns(self, tmp_path, _patch_base_bot_deps):
        """When no presence and no shared session, returns False — never spawns."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = bot.ensure_tmux_session()
        assert result is False
        assert bot._using_shared_session is False

    def test_presence_rebinds_on_pointer_change(self, tmp_path, _patch_base_bot_deps):
        """Bot re-reads presence on each call, rebinding to new session."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        my_pid = os.getpid()

        _write_presence(
            tmp_path,
            {
                "devpulse": {
                    "pid": my_pid,
                    "work_dir": str(tmp_path / "workdir"),
                    "attach_handle": "session-v1",
                }
            },
        )
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            bot.ensure_tmux_session()
        assert bot.session_name == "session-v1"

        _write_presence(
            tmp_path,
            {
                "devpulse": {
                    "pid": my_pid,
                    "work_dir": str(tmp_path / "workdir"),
                    "attach_handle": "session-v2",
                }
            },
        )
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            bot.ensure_tmux_session()
        assert bot.session_name == "session-v2"

    def test_stale_presence_ignored(self, tmp_path, _patch_base_bot_deps):
        """Dead PID in presence pointer is treated as absent."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        _write_presence(
            tmp_path,
            {
                "devpulse": {
                    "pid": 99999999,
                    "work_dir": str(tmp_path / "workdir"),
                    "attach_handle": "dead-session",
                }
            },
        )
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = bot.ensure_tmux_session()
        assert result is False

    def test_presence_with_tmux_scan_fallback(self, tmp_path, _patch_base_bot_deps):
        """When attach_handle is empty, bot finds tmux session by CWD scan."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        workdir = str(bot.work_dir)
        _write_presence(
            tmp_path,
            {
                "devpulse": {
                    "pid": os.getpid(),
                    "work_dir": workdir,
                    "attach_handle": "",
                }
            },
        )

        def _side_effect(cmd, **kwargs):
            mock = MagicMock()
            if "list-panes" in cmd:
                mock.returncode = 0
                mock.stdout = f"found-session:{workdir}\n"
            else:
                mock.returncode = 1
            return mock

        with patch("subprocess.run", side_effect=_side_effect):
            result = bot.ensure_tmux_session()
        assert result is True
        assert bot.session_name == "found-session"


# =============================================
# 5. handle_message — no-session error
# =============================================


class TestHandleMessageNoSession:
    """Error message when no live session is available."""

    def test_shows_branch_name_in_error(self, tmp_path, _patch_base_bot_deps):
        """Error message includes the branch name."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="api")
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            bot.handle_message(42, "hello", {"message_id": 1})
        msg = bot.send_message.call_args[0][1]
        assert "No live Claude session" in msg
        assert "api" in msg

    def test_shows_work_dir_name_when_no_branch_name(self, tmp_path, _patch_base_bot_deps):
        """Falls back to work_dir name in error when branch_name is None."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.branch_name = None
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            bot.handle_message(42, "hello", {"message_id": 1})
        msg = bot.send_message.call_args[0][1]
        assert "No live Claude session" in msg
