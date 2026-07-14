# =================== AIPass ====================
# Name: test_inbound_reliability.py
# Description: Tests for inbound message reliability hardening in BaseBot
# Version: 1.0.0
# Created: 2026-07-14
# Modified: 2026-07-14
# =============================================

"""
Tests for inbound reliability hardening in handle_message.

Tests cover:
  - Stale pending cleaned before writing new pending
  - Warning logged when overwriting undelivered pending
  - No warning when previous pending was delivered
  - Corrupt pending file doesn't crash
"""

import json
import time

import pytest
from unittest.mock import patch

from aipass.skills.lib.telegram.apps.handlers.base_bot import BaseBot


# =============================================
# HELPERS
# =============================================


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
    """Patch heavy BaseBot dependencies for lightweight instantiation."""
    patches = [
        patch(
            "aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR",
            tmp_path,
        ),
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.signal.signal"),
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.atexit.register"),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


def _make_bot(tmp_path, _patch_base_bot_deps):
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    return BaseBot(
        bot_id="test_bot",
        bot_token="123:FAKETOKEN",
        work_dir=workdir,
        bot_name="Test Bot",
        allowed_user_ids=[111],
        branch_name="testbranch",
    )


# =============================================
# TESTS
# =============================================


class TestInboundReliability:
    def test_clean_stale_called_before_write(self, tmp_path, _patch_base_bot_deps):
        """handle_message calls clean_stale_pending before write_pending_file."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        call_order = []

        with (
            patch.object(
                bot,
                "ensure_tmux_session",
                return_value=True,
            ),
            patch.object(bot, "send_message", return_value={"message_id": 1}),
            patch.object(
                bot,
                "clean_stale_pending",
                side_effect=lambda: call_order.append("clean"),
            ),
            patch.object(
                bot,
                "write_pending_file",
                side_effect=lambda *a: (call_order.append("write"), True)[1],
            ),
            patch.object(bot, "inject_message", return_value=True),
            patch.object(bot, "_start_heartbeat"),
        ):
            bot.handle_message(42, "hello", {"message_id": 100})

        assert call_order == ["clean", "write"]

    def test_warns_on_undelivered_overwrite(self, tmp_path, _patch_base_bot_deps, caplog):
        """Warning logged when overwriting a pending file that wasn't delivered."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)

        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(
            json.dumps(
                {
                    "chat_id": 42,
                    "message_id": 50,
                    "delivered": False,
                    "timestamp": time.time(),
                }
            )
        )

        with (
            patch.object(bot, "ensure_tmux_session", return_value=True),
            patch.object(bot, "send_message", return_value={"message_id": 1}),
            patch.object(bot, "clean_stale_pending"),
            patch.object(bot, "write_pending_file", return_value=True),
            patch.object(bot, "inject_message", return_value=True),
            patch.object(bot, "_start_heartbeat"),
        ):
            bot.handle_message(42, "new msg", {"message_id": 200})

        assert any("Overwriting undelivered pending" in r.message for r in caplog.records)
        assert any("msg_id=50" in r.message for r in caplog.records)

    def test_no_warn_when_delivered(self, tmp_path, _patch_base_bot_deps, caplog):
        """No warning when previous pending was already delivered."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)

        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(
            json.dumps(
                {
                    "chat_id": 42,
                    "message_id": 50,
                    "delivered": True,
                    "timestamp": time.time(),
                }
            )
        )

        with (
            patch.object(bot, "ensure_tmux_session", return_value=True),
            patch.object(bot, "send_message", return_value={"message_id": 1}),
            patch.object(bot, "clean_stale_pending"),
            patch.object(bot, "write_pending_file", return_value=True),
            patch.object(bot, "inject_message", return_value=True),
            patch.object(bot, "_start_heartbeat"),
        ):
            bot.handle_message(42, "new msg", {"message_id": 200})

        assert not any("Overwriting undelivered pending" in r.message for r in caplog.records)

    def test_corrupt_pending_no_crash(self, tmp_path, _patch_base_bot_deps):
        """Corrupt pending file doesn't crash handle_message."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)

        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text("not json{{{")

        with (
            patch.object(bot, "ensure_tmux_session", return_value=True),
            patch.object(bot, "send_message", return_value={"message_id": 1}),
            patch.object(bot, "clean_stale_pending"),
            patch.object(bot, "write_pending_file", return_value=True),
            patch.object(bot, "inject_message", return_value=True),
            patch.object(bot, "_start_heartbeat"),
        ):
            bot.handle_message(42, "hello", {"message_id": 100})

    def test_no_pending_file_no_crash(self, tmp_path, _patch_base_bot_deps):
        """Missing pending file doesn't crash handle_message."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)

        with (
            patch.object(bot, "ensure_tmux_session", return_value=True),
            patch.object(bot, "send_message", return_value={"message_id": 1}),
            patch.object(bot, "clean_stale_pending"),
            patch.object(bot, "write_pending_file", return_value=True),
            patch.object(bot, "inject_message", return_value=True),
            patch.object(bot, "_start_heartbeat"),
        ):
            bot.handle_message(42, "hello", {"message_id": 100})
