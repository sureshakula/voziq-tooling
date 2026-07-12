# =================== AIPass ====================
# Name: test_prax_monitor_bot.py
# Description: Tests for PraxMonitorBot — Prax Monitor TG chat command receiver
# Version: 1.0.0
# Created: 2026-07-12
# Modified: 2026-07-12
# =============================================

"""
Tests for PraxMonitorBot — command receiver for the Prax Monitor TG chat.

Tests cover:
  - /pause writes paused=true to control file
  - /resume writes paused=false to control file
  - /errors writes level=errors
  - /all writes level=all
  - /status shows current state and relay liveness
  - Free-text and file uploads rejected
  - Command routing dispatches correctly
  - Control file I/O: read defaults on missing/corrupt, write adds updated_at
  - Slash-menu includes all custom commands
  - Write failure sends error message
"""

import json

import pytest
from unittest.mock import patch, MagicMock

from aipass.skills.lib.telegram.apps.handlers.prax_monitor_bot import PraxMonitorBot


# =============================================
# HELPERS
# =============================================


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
    """Patch heavy BaseBot dependencies to allow lightweight instantiation."""
    patches = [
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path),
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.signal.signal"),
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.atexit.register"),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture
def ctrl_file(tmp_path):
    """Provide a tmp control file path and patch the module constant."""
    f = tmp_path / "prax_monitor_control.json"
    with patch("aipass.skills.lib.telegram.apps.handlers.prax_monitor_bot.CONTROL_FILE", f):
        yield f


def _make_bot(tmp_path, _patch_base_bot_deps):
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    return PraxMonitorBot(
        bot_id="prax_monitor",
        bot_token="123:FAKETOKEN",
        work_dir=workdir,
        bot_name="Prax Monitor Bot",
        allowed_user_ids=[111],
        branch_name=None,
    )


# =============================================
# 1. /PAUSE
# =============================================


class TestPause:
    def test_pause_writes_control(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message"):
            bot._handle_pause(42)

        data = json.loads(ctrl_file.read_text())
        assert data["paused"] is True
        assert "updated_at" in data

    def test_pause_sends_confirmation(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._handle_pause(42)
        assert "paused" in mock_send.call_args[0][1].lower()

    def test_pause_preserves_level(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": False, "level": "errors"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message"):
            bot._handle_pause(42)

        data = json.loads(ctrl_file.read_text())
        assert data["paused"] is True
        assert data["level"] == "errors"

    def test_pause_write_failure(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "_write_control", return_value=False),
            patch.object(bot, "send_message") as mock_send,
        ):
            bot._handle_pause(42)
        assert "failed" in mock_send.call_args[0][1].lower()


# =============================================
# 2. /RESUME
# =============================================


class TestResume:
    def test_resume_writes_control(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": True, "level": "all"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message"):
            bot._handle_resume(42)

        data = json.loads(ctrl_file.read_text())
        assert data["paused"] is False

    def test_resume_sends_confirmation(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._handle_resume(42)
        assert "resumed" in mock_send.call_args[0][1].lower()

    def test_resume_shows_level_in_message(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": True, "level": "errors"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._handle_resume(42)
        assert "errors" in mock_send.call_args[0][1]


# =============================================
# 3. /ERRORS
# =============================================


class TestErrors:
    def test_errors_writes_level(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message"):
            bot._handle_errors(42)

        data = json.loads(ctrl_file.read_text())
        assert data["level"] == "errors"

    def test_errors_sends_confirmation(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._handle_errors(42)
        assert "errors & warnings" in mock_send.call_args[0][1].lower()

    def test_errors_preserves_paused(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": True, "level": "all"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message"):
            bot._handle_errors(42)

        data = json.loads(ctrl_file.read_text())
        assert data["paused"] is True
        assert data["level"] == "errors"


# =============================================
# 4. /ALL
# =============================================


class TestAll:
    def test_all_writes_level(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": False, "level": "errors"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message"):
            bot._handle_all(42)

        data = json.loads(ctrl_file.read_text())
        assert data["level"] == "all"

    def test_all_sends_confirmation(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._handle_all(42)
        msg = mock_send.call_args[0][1]
        assert "all" in msg.lower()


# =============================================
# 5. /STATUS
# =============================================


class TestStatus:
    def test_status_shows_state(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": False, "level": "all", "updated_at": "2026-07-12T10:00:00Z"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "send_message") as mock_send,
            patch.object(PraxMonitorBot, "_check_relay_alive", return_value=True),
        ):
            bot._handle_prax_status(42)
        msg = mock_send.call_args[0][1]
        assert "active" in msg
        assert "all levels" in msg
        assert "running" in msg

    def test_status_shows_paused(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": True, "level": "errors"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "send_message") as mock_send,
            patch.object(PraxMonitorBot, "_check_relay_alive", return_value=False),
        ):
            bot._handle_prax_status(42)
        msg = mock_send.call_args[0][1]
        assert "paused" in msg
        assert "errors & warnings" in msg
        assert "not detected" in msg

    def test_status_defaults_when_no_file(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "send_message") as mock_send,
            patch.object(PraxMonitorBot, "_check_relay_alive", return_value=False),
        ):
            bot._handle_prax_status(42)
        msg = mock_send.call_args[0][1]
        assert "active" in msg
        assert "all levels" in msg


# =============================================
# 6. FREE-TEXT & FILE REJECTION
# =============================================


class TestRejection:
    def test_freetext_rejected(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot.handle_message(42, "hello there", {})
        assert "commands" in mock_send.call_args[0][1].lower()

    def test_file_rejected(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot.handle_file(42, {"document": {}})
        assert "don't process files" in mock_send.call_args[0][1].lower()


# =============================================
# 7. COMMAND ROUTING
# =============================================


class TestCommandRouting:
    def test_pause_dispatched(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_handle_pause") as mock:
            assert bot._dispatch_command(42, ("pause", "")) is True
            mock.assert_called_once_with(42)

    def test_resume_dispatched(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_handle_resume") as mock:
            assert bot._dispatch_command(42, ("resume", "")) is True
            mock.assert_called_once_with(42)

    def test_errors_dispatched(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_handle_errors") as mock:
            assert bot._dispatch_command(42, ("errors", "")) is True
            mock.assert_called_once_with(42)

    def test_all_dispatched(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_handle_all") as mock:
            assert bot._dispatch_command(42, ("all", "")) is True
            mock.assert_called_once_with(42)

    def test_status_dispatched(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_handle_prax_status") as mock:
            assert bot._dispatch_command(42, ("status", "")) is True
            mock.assert_called_once_with(42)

    def test_unknown_falls_through_to_parent(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message"):
            result = bot._dispatch_command(42, ("help", ""))
        assert result is True


# =============================================
# 8. CONTROL FILE I/O
# =============================================


class TestControlFileIO:
    def test_read_defaults_when_missing(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._read_control()
        assert result == {"paused": False, "level": "all"}

    def test_read_defaults_on_corrupt(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text("not json{{{")
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._read_control()
        assert result == {"paused": False, "level": "all"}

    def test_read_defaults_on_non_dict(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text('"just a string"')
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._read_control()
        assert result == {"paused": False, "level": "all"}

    def test_read_returns_data(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        ctrl_file.write_text(json.dumps({"paused": True, "level": "errors"}))
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._read_control()
        assert result["paused"] is True
        assert result["level"] == "errors"

    def test_write_adds_timestamp(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot._write_control({"paused": False, "level": "all"})
        data = json.loads(ctrl_file.read_text())
        assert "updated_at" in data
        assert "T" in data["updated_at"]

    def test_write_roundtrip(self, tmp_path, _patch_base_bot_deps, ctrl_file):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot._write_control({"paused": True, "level": "errors"})
        result = bot._read_control()
        assert result["paused"] is True
        assert result["level"] == "errors"
        assert "updated_at" in result


# =============================================
# 9. SLASH MENU
# =============================================


class TestSlashMenu:
    def test_custom_commands_include_all(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        cmds = bot.get_custom_commands()
        assert "pause" in cmds
        assert "resume" in cmds
        assert "errors" in cmds
        assert "all" in cmds
        assert "monitor" in cmds

    def test_custom_commands_have_descriptions(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        cmds = bot.get_custom_commands()
        for cmd in ("pause", "resume", "errors", "all"):
            assert "description" in cmds[cmd]
            assert "menu_text" in cmds[cmd]


# =============================================
# 10. RELAY LIVENESS CHECK
# =============================================


class TestRelayAlive:
    def test_alive_when_active(self):
        mock_result = MagicMock()
        mock_result.stdout = "active\n"
        with patch(
            "aipass.skills.lib.telegram.apps.handlers.prax_monitor_bot.subprocess.run", return_value=mock_result
        ):
            assert PraxMonitorBot._check_relay_alive() is True

    def test_not_alive_when_inactive(self):
        mock_result = MagicMock()
        mock_result.stdout = "inactive\n"
        with patch(
            "aipass.skills.lib.telegram.apps.handlers.prax_monitor_bot.subprocess.run", return_value=mock_result
        ):
            assert PraxMonitorBot._check_relay_alive() is False

    def test_not_alive_on_error(self):
        with patch(
            "aipass.skills.lib.telegram.apps.handlers.prax_monitor_bot.subprocess.run",
            side_effect=OSError("no systemctl"),
        ):
            assert PraxMonitorBot._check_relay_alive() is False
