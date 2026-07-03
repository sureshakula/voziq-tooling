# =================== AIPass ====================
# Name: test_status_reset.py
# Description: Tests for /status conversation vs daemon uptime + /new counter reset
# Version: 1.0.0
# Created: 2026-06-29
# Modified: 2026-06-29
# =============================================

"""
Tests for /status conversation vs daemon uptime + /new counter reset.

Tests cover:
  - /new resets message_count to 0
  - /new resets conversation_start
  - /status shows conversation uptime (not daemon uptime) as primary
  - /status shows daemon uptime separately
  - build_status_text includes daemon_uptime line when provided
  - build_status_text omits daemon_uptime line when not provided
"""

import time
import pytest
from unittest.mock import patch

from apps.handlers.base_bot import BaseBot  # type: ignore[import-not-found]
from apps.handlers.telegram_standards import build_status_text  # type: ignore[import-not-found]


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
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


def _make_bot(tmp_path, _patch_base_bot_deps):
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    return BaseBot(
        bot_id="status_test",
        bot_token="123:FAKETOKEN",
        work_dir=workdir,
        bot_name="Status Test Bot",
        allowed_user_ids=[111],
        branch_name=None,
    )


# =============================================
# 1. /new RESETS COUNTERS
# =============================================


class TestNewResetsCounters:
    """/new resets message_count and conversation_start."""

    def test_new_resets_message_count(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.state["message_count"] = 15

        with (
            patch.object(bot, "send_message"),
            patch.object(bot, "_kill_tmux_session"),
        ):
            bot._dispatch_command(42, ("new", ""))

        assert bot.state["message_count"] == 0

    def test_new_resets_conversation_start(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.state["conversation_start"] = time.time() - 3600  # 1 hour ago

        with (
            patch.object(bot, "send_message"),
            patch.object(bot, "_kill_tmux_session"),
        ):
            before = time.time()
            bot._dispatch_command(42, ("new", ""))
            after = time.time()

        assert before <= bot.state["conversation_start"] <= after

    def test_new_does_not_reset_daemon_start(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        original_start = bot.state["start_time"]
        bot.state["message_count"] = 5

        with (
            patch.object(bot, "send_message"),
            patch.object(bot, "_kill_tmux_session"),
        ):
            bot._dispatch_command(42, ("new", ""))

        assert bot.state["start_time"] == original_start


# =============================================
# 2. /status SHOWS CORRECT UPTIMES
# =============================================


class TestStatusUptimes:
    """/status shows conversation uptime as primary and daemon uptime separately."""

    def test_status_passes_daemon_uptime(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.state["start_time"] = time.time() - 7200  # daemon up 2h
        bot.state["conversation_start"] = time.time() - 300  # conv 5m

        with (
            patch.object(bot, "send_message"),
            patch("apps.handlers.base_bot.build_status_text", wraps=build_status_text) as mock_build,
            patch("apps.handlers.telegram_standards._tmux_session_exists", return_value=True),
        ):
            bot._dispatch_command(42, ("status", ""))

        call_kwargs = mock_build.call_args
        args = call_kwargs[1] if call_kwargs[1] else {}
        if not args:
            _, kwargs = mock_build.call_args
            args = kwargs

        assert "daemon_uptime" in args
        assert "2h" in args["daemon_uptime"]

    def test_status_conversation_uptime_after_new(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.state["start_time"] = time.time() - 7200  # daemon up 2h

        with (
            patch.object(bot, "send_message"),
            patch.object(bot, "_kill_tmux_session"),
        ):
            bot._dispatch_command(42, ("new", ""))

        # Now check /status — conversation uptime should be near 0
        with (
            patch.object(bot, "send_message") as mock_send,
            patch("apps.handlers.telegram_standards._tmux_session_exists", return_value=True),
        ):
            bot._dispatch_command(42, ("status", ""))

        msg = mock_send.call_args[0][1]
        assert "Uptime: 0h 0m" in msg
        assert "Daemon up: 2h" in msg

    def test_status_messages_zero_after_new(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.state["message_count"] = 42

        with (
            patch.object(bot, "send_message"),
            patch.object(bot, "_kill_tmux_session"),
        ):
            bot._dispatch_command(42, ("new", ""))

        with (
            patch.object(bot, "send_message") as mock_send,
            patch("apps.handlers.telegram_standards._tmux_session_exists", return_value=True),
        ):
            bot._dispatch_command(42, ("status", ""))

        msg = mock_send.call_args[0][1]
        assert "Messages: 0" in msg


# =============================================
# 3. build_status_text
# =============================================


class TestBuildStatusText:
    """build_status_text renders daemon_uptime when provided."""

    def test_includes_daemon_uptime(self):
        with patch("apps.handlers.telegram_standards._tmux_session_exists", return_value=True):
            text = build_status_text(
                session_name="telegram-base",
                branch_name="base",
                uptime="0h 5m 0s",
                message_count=3,
                daemon_uptime="12h 0m 0s",
            )
        assert "Daemon up: 12h 0m 0s" in text
        assert "Uptime: 0h 5m 0s" in text

    def test_omits_daemon_uptime_when_none(self):
        with patch("apps.handlers.telegram_standards._tmux_session_exists", return_value=True):
            text = build_status_text(
                session_name="telegram-base",
                branch_name="base",
                uptime="1h 0m 0s",
                message_count=5,
            )
        assert "Daemon up" not in text
        assert "Uptime: 1h 0m 0s" in text

    def test_uptime_before_daemon_uptime(self):
        with patch("apps.handlers.telegram_standards._tmux_session_exists", return_value=True):
            text = build_status_text(
                session_name="telegram-base",
                branch_name="base",
                uptime="0h 1m 0s",
                daemon_uptime="5h 0m 0s",
            )
        uptime_pos = text.index("Uptime:")
        daemon_pos = text.index("Daemon up:")
        assert uptime_pos < daemon_pos


# =============================================
# 4. CONVERSATION_START IN STATE
# =============================================


class TestConversationStartState:
    """conversation_start is initialized and tracked."""

    def test_init_sets_conversation_start(self, tmp_path, _patch_base_bot_deps):
        before = time.time()
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        after = time.time()
        assert before <= bot.state["conversation_start"] <= after

    def test_conversation_start_equals_start_time_at_boot(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        assert abs(bot.state["conversation_start"] - bot.state["start_time"]) < 0.1
