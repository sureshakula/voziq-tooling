# =================== AIPass ====================
# Name: test_attach_only.py
# Description: Tests for attach-only mode (TDPLAN-0009 Stage 1)
# Version: 1.0.0
# Created: 2026-06-29
# Modified: 2026-06-29
# =============================================

"""
Tests for attach-only mode (TDPLAN-0009 Stage 1).

The bot attaches to a pre-existing tmux session and never spawns its own.
When attach_only=True + shared_session is set:
  - Attaches to existing named tmux session (no spawn)
  - Missing session → loud error, NO spawn of telegram-{bot_id}
  - Persistent mapping file written with all CONTRACT fields + seeded cursor
  - No lock created for the shared session
  - inject_message reaches the session (unchanged, tested via existing tests)
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from aipass.skills.lib.telegram.apps.handlers.base_bot import BaseBot


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
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


def _make_bot(tmp_path, _patch_base_bot_deps, attach_only=False, shared_session=None):
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path):
        bot = BaseBot(
            bot_id="mirror_test",
            bot_token="123:FAKETOKEN",
            work_dir=workdir,
            bot_name="Mirror Test Bot",
            allowed_user_ids=[111],
            branch_name="devpulse",
            shared_session=shared_session,
            attach_only=attach_only,
        )
    bot.send_message = MagicMock(return_value={"ok": True, "message_id": 1})
    return bot


# =============================================
# 1. ensure_tmux_session — attach-only behavior
# =============================================


class TestAttachOnly:
    """Attach-only mode: attach to existing session, never spawn."""

    def test_attaches_to_existing_session(self, tmp_path, _patch_base_bot_deps):
        """When shared session exists, bot attaches and returns True."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")

        result_obj = MagicMock()
        result_obj.returncode = 0
        with patch("subprocess.run", return_value=result_obj):
            assert bot.ensure_tmux_session() is True
        assert bot.session_name == "devpulse"
        assert bot._using_shared_session is True

    def test_missing_session_returns_false(self, tmp_path, _patch_base_bot_deps):
        """When shared session is missing, attach-only returns False (no spawn)."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")

        result_obj = MagicMock()
        result_obj.returncode = 1
        with patch("subprocess.run", return_value=result_obj):
            assert bot.ensure_tmux_session() is False
        # Session name should NOT fall back to telegram-{bot_id}
        assert bot._using_shared_session is False

    def test_missing_session_does_not_spawn(self, tmp_path, _patch_base_bot_deps):
        """Attach-only never creates a telegram-{bot_id} session."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")

        result_obj = MagicMock()
        result_obj.returncode = 1
        with patch("subprocess.run", return_value=result_obj) as mock_run:
            bot.ensure_tmux_session()
            # Should only have checked has-session, never new-session
            calls = [str(c) for c in mock_run.call_args_list]
            for call in calls:
                assert "new-session" not in call

    def test_no_shared_session_config_returns_false(self, tmp_path, _patch_base_bot_deps):
        """Attach-only without shared_session configured returns False."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session=None)
        assert bot.ensure_tmux_session() is False

    def test_non_attach_mode_falls_back_on_missing(self, tmp_path, _patch_base_bot_deps):
        """Without attach_only, missing shared session falls back to own session."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=False, shared_session="devpulse")

        has_session = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=has_session):
            # Falls back to telegram-{bot_id} and tries to spawn — we just check the name
            bot.ensure_tmux_session()
        assert bot.session_name == "telegram-mirror_test"

    def test_handle_message_shows_error_on_attach_fail(self, tmp_path, _patch_base_bot_deps):
        """handle_message shows specific error when no live session found."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")

        result_obj = MagicMock()
        result_obj.returncode = 1
        with patch("subprocess.run", return_value=result_obj):
            bot.handle_message(42, "hello", {"message_id": 1})

        msg = bot.send_message.call_args[0][1]
        assert "No live Claude session" in msg
        assert "devpulse" in msg


# =============================================
# 2. Mirror mapping file (THE CONTRACT)
# =============================================


class TestMirrorMapping:
    """Persistent mapping file written at attach with CONTRACT fields."""

    def test_mapping_written_on_attach(self, tmp_path, _patch_base_bot_deps):
        """Mapping file written when attach-only bot attaches to existing session."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")
        bot._active_chat_id = 42

        mapping_dir = tmp_path / ".aipass" / "telegram_bots"
        result_obj = MagicMock()
        result_obj.returncode = 0
        with (
            patch("subprocess.run", return_value=result_obj),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            bot.ensure_tmux_session()

        mapping_file = mapping_dir / "bot-mirror_test.json"
        assert mapping_file.exists()
        data = json.loads(mapping_file.read_text())
        assert data["chat_id"] == 42
        assert data["bot_token"] == "123:FAKETOKEN"
        assert data["session_name"] == "devpulse"
        assert data["mirror"] is True
        assert "transcript_line_after" in data
        assert data["work_dir"] == str(tmp_path / "workdir")

    def test_mapping_uses_config_chat_id(self, tmp_path, _patch_base_bot_deps):
        """Mapping uses _config_chat_id when _active_chat_id is not set."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")
        bot._config_chat_id = 99

        mapping_dir = tmp_path / ".aipass" / "telegram_bots"
        result_obj = MagicMock()
        result_obj.returncode = 0
        with (
            patch("subprocess.run", return_value=result_obj),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            bot.ensure_tmux_session()

        mapping_file = mapping_dir / "bot-mirror_test.json"
        assert mapping_file.exists()
        data = json.loads(mapping_file.read_text())
        assert data["chat_id"] == 99

    def test_mapping_deferred_when_no_chat_id(self, tmp_path, _patch_base_bot_deps):
        """Mapping deferred if no chat_id at attach time."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")

        mapping_dir = tmp_path / ".aipass" / "telegram_bots"
        result_obj = MagicMock()
        result_obj.returncode = 0
        with (
            patch("subprocess.run", return_value=result_obj),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            bot.ensure_tmux_session()

        mapping_file = mapping_dir / "bot-mirror_test.json"
        assert not mapping_file.exists()
        assert bot._mirror_mapping_written is False

    def test_mapping_written_once(self, tmp_path, _patch_base_bot_deps):
        """Mapping file only written once (idempotent)."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")
        bot._active_chat_id = 42

        result_obj = MagicMock()
        result_obj.returncode = 0
        with (
            patch("subprocess.run", return_value=result_obj),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            bot.ensure_tmux_session()
            bot.ensure_tmux_session()

        assert bot._mirror_mapping_written is True

    def test_mapping_not_written_for_non_attach(self, tmp_path, _patch_base_bot_deps):
        """Non-attach-only bots don't write mirror mapping."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=False, shared_session="devpulse")
        bot._active_chat_id = 42

        mapping_dir = tmp_path / ".aipass" / "telegram_bots"
        result_obj = MagicMock()
        result_obj.returncode = 0
        with (
            patch("subprocess.run", return_value=result_obj),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            bot.ensure_tmux_session()

        mapping_file = mapping_dir / "bot-mirror_test.json"
        assert not mapping_file.exists()


# =============================================
# 3. Lock file skipped in attach-only
# =============================================


class TestAttachOnlyLock:
    """Lock file still created in attach-only (prevents duplicate pollers)."""

    def test_lock_still_created_in_attach_mode(self, tmp_path, _patch_base_bot_deps):
        """run() still creates lock in attach-only mode (one poller per bot_id)."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True, shared_session="devpulse")

        with (
            patch.object(bot, "_check_lock", return_value=False) as mock_check,
            patch.object(bot, "_create_lock") as mock_create,
            patch.object(bot, "verify_connection", return_value=True),
            patch.object(bot, "_set_command_menu"),
            patch.object(bot, "_boot_monitor"),
            patch.object(bot, "clean_stale_pending"),
            patch.object(bot, "_load_offset", return_value=0),
            patch.object(bot, "poll_updates", side_effect=KeyboardInterrupt),
            patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path),
        ):
            bot.run()

        mock_check.assert_called_once()
        mock_create.assert_called_once()

    def test_lock_created_in_normal_mode(self, tmp_path, _patch_base_bot_deps):
        """run() creates lock in normal (non-attach) mode."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=False)

        with (
            patch.object(bot, "_check_lock", return_value=False),
            patch.object(bot, "_create_lock") as mock_create,
            patch.object(bot, "verify_connection", return_value=True),
            patch.object(bot, "_set_command_menu"),
            patch.object(bot, "_boot_monitor"),
            patch.object(bot, "clean_stale_pending"),
            patch.object(bot, "_load_offset", return_value=0),
            patch.object(bot, "poll_updates", side_effect=KeyboardInterrupt),
            patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path),
        ):
            bot.run()

        mock_create.assert_called_once()


# =============================================
# 4. Config loading
# =============================================


class TestAttachOnlyConfig:
    """attach_only flag passed through config."""

    def test_attach_only_defaults_false(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        assert bot._attach_only is False

    def test_attach_only_set_true(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps, attach_only=True)
        assert bot._attach_only is True
