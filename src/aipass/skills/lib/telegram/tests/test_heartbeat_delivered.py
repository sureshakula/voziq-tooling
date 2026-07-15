# =================== AIPass ====================
# Name: test_heartbeat_delivered.py
# Description: Tests for heartbeat delivered-flag fix (DPLAN-0223)
# Version: 1.0.0
# Created: 2026-06-29
# Modified: 2026-06-29
# =============================================

"""
Tests for heartbeat delivered-flag fix (DPLAN-0223).

The heartbeat now stops when the pending file contains 'delivered': true
(set by @hooks _advance_pending), instead of waiting for file deletion.

Tests cover:
  - Heartbeat stops when pending file has delivered=true
  - Heartbeat continues when pending file exists but not delivered
  - Heartbeat stops when pending file is absent (backward compat)
  - Multi-Stop keeps file alive (delivered flag, not deletion)
  - Reply not clobbered: heartbeat does NOT edit after delivery
"""

import json
import time
import pytest
from unittest.mock import patch

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


def _make_bot(tmp_path, _patch_base_bot_deps, pending_dir=None):
    pdir = pending_dir or tmp_path
    with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", pdir):
        workdir = tmp_path / "workdir"
        workdir.mkdir(exist_ok=True)
        bot = BaseBot(
            bot_id="heartbeat_test",
            bot_token="123:FAKETOKEN",
            work_dir=workdir,
            bot_name="Heartbeat Test Bot",
            allowed_user_ids=[111],
            branch_name=None,
        )
    bot.pending_file = pdir / "bot-heartbeat_test.json"
    return bot


# =============================================
# 1. _is_pending_delivered
# =============================================


class TestIsPendingDelivered:
    """Verify _is_pending_delivered reads the delivered flag correctly."""

    def test_returns_true_when_delivered(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(json.dumps({"chat_id": 42, "delivered": True}), encoding="utf-8")
        assert bot._is_pending_delivered() is True

    def test_returns_false_when_not_delivered(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(json.dumps({"chat_id": 42}), encoding="utf-8")
        assert bot._is_pending_delivered() is False

    def test_returns_true_when_file_absent(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        assert not bot.pending_file.exists()
        assert bot._is_pending_delivered() is True

    def test_returns_false_on_corrupt_json(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text("not json", encoding="utf-8")
        assert bot._is_pending_delivered() is False

    def test_returns_false_when_delivered_is_false(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(json.dumps({"chat_id": 42, "delivered": False}), encoding="utf-8")
        assert bot._is_pending_delivered() is False


# =============================================
# 2. HEARTBEAT STOPS ON DELIVERED
# =============================================


class TestHeartbeatStopsOnDelivered:
    """Heartbeat thread exits when pending file has delivered=true."""

    def test_heartbeat_stops_when_delivered_mid_loop(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(json.dumps({"chat_id": 42}), encoding="utf-8")

        call_count = 0

        def fake_edit(chat_id, msg_id, text):
            nonlocal call_count
            call_count += 1
            # Simulate delivery on first heartbeat edit
            bot.pending_file.write_text(json.dumps({"chat_id": 42, "delivered": True}), encoding="utf-8")

        with (
            patch.object(bot, "edit_message", side_effect=fake_edit),
            patch.object(bot, "_tmux_session_exists", return_value=True),
            patch("aipass.skills.lib.telegram.apps.handlers.base_bot.HEARTBEAT_INTERVAL", 0.1),
        ):
            bot._start_heartbeat(42, 999)
            time.sleep(0.5)
            bot._stop_heartbeat()

        # Should have stopped after 1 edit (when delivered was set)
        assert call_count <= 2

    def test_heartbeat_continues_when_not_delivered(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(json.dumps({"chat_id": 42}), encoding="utf-8")

        call_count = 0

        def fake_edit(chat_id, msg_id, text):
            nonlocal call_count
            call_count += 1

        with (
            patch.object(bot, "edit_message", side_effect=fake_edit),
            patch.object(bot, "_tmux_session_exists", return_value=True),
            patch("aipass.skills.lib.telegram.apps.handlers.base_bot.HEARTBEAT_INTERVAL", 0.1),
        ):
            bot._start_heartbeat(42, 999)
            time.sleep(0.5)
            bot._stop_heartbeat()

        # Should have ticked multiple times since never delivered
        assert call_count >= 2

    def test_heartbeat_stops_when_file_absent(self, tmp_path, _patch_base_bot_deps):
        """Backward compat: heartbeat still stops when file is gone."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        assert not bot.pending_file.exists()

        with (
            patch.object(bot, "edit_message") as mock_edit,
            patch.object(bot, "_tmux_session_exists", return_value=True),
            patch("aipass.skills.lib.telegram.apps.handlers.base_bot.HEARTBEAT_INTERVAL", 0.1),
        ):
            bot._start_heartbeat(42, 999)
            time.sleep(0.4)
            bot._stop_heartbeat()

        # File never existed, so heartbeat breaks immediately — no edits
        mock_edit.assert_not_called()


# =============================================
# 3. MULTI-STOP KEEPS FILE ALIVE
# =============================================


class TestMultiStopFileAlive:
    """Pending file survives delivery (advanced, not deleted)."""

    def test_pending_file_survives_with_delivered_flag(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)

        initial_data = {"chat_id": 42, "transcript_line_after": 100}
        bot.pending_file.write_text(json.dumps(initial_data), encoding="utf-8")

        # Simulate _advance_pending behavior (what @hooks does)
        data = json.loads(bot.pending_file.read_text(encoding="utf-8"))
        data["delivered"] = True
        data["transcript_line_after"] = 200
        bot.pending_file.write_text(json.dumps(data), encoding="utf-8")

        # File still exists
        assert bot.pending_file.exists()
        # But heartbeat sees it as delivered
        assert bot._is_pending_delivered() is True
        # Cursor advanced
        reloaded = json.loads(bot.pending_file.read_text(encoding="utf-8"))
        assert reloaded["transcript_line_after"] == 200

    def test_new_message_overwrites_delivered(self, tmp_path, _patch_base_bot_deps):
        """A new write_pending_file clears the delivered flag."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)

        # Simulate previous delivery
        bot.pending_file.write_text(json.dumps({"chat_id": 42, "delivered": True}), encoding="utf-8")
        assert bot._is_pending_delivered() is True

        # Now write a new pending (as handle_message does)
        with patch.object(bot, "_get_transcript_line_count", return_value=300):
            bot.write_pending_file(42, 999, 1000)

        # delivered flag should be gone
        assert bot._is_pending_delivered() is False
        data = json.loads(bot.pending_file.read_text(encoding="utf-8"))
        assert "delivered" not in data


# =============================================
# 4. REPLY NOT CLOBBERED
# =============================================


class TestReplyNotClobbered:
    """After delivery, heartbeat must NOT edit the message (no clobber)."""

    def test_no_edit_after_delivered(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        # Start with delivered=true (simulates hooks already delivered before heartbeat tick)
        bot.pending_file.write_text(json.dumps({"chat_id": 42, "delivered": True}), encoding="utf-8")

        with (
            patch.object(bot, "edit_message") as mock_edit,
            patch.object(bot, "_tmux_session_exists", return_value=True),
            patch("aipass.skills.lib.telegram.apps.handlers.base_bot.HEARTBEAT_INTERVAL", 0.1),
        ):
            bot._start_heartbeat(42, 999)
            time.sleep(0.4)
            bot._stop_heartbeat()

        # Heartbeat saw delivered immediately, never edited
        mock_edit.assert_not_called()


# =============================================
# 5. STALE THREAD CANNOT EDIT (generation counter)
# =============================================


class TestStaleThreadCannotEdit:
    """A heartbeat thread from a previous generation must not edit after a new start."""

    def test_stale_thread_blocked_by_gen(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(json.dumps({"chat_id": 42}), encoding="utf-8")

        edits_by_msg = {}

        def track_edit(chat_id, msg_id, text):
            edits_by_msg.setdefault(msg_id, []).append(text)

        with (
            patch.object(bot, "edit_message", side_effect=track_edit),
            patch.object(bot, "_tmux_session_exists", return_value=True),
            patch("aipass.skills.lib.telegram.apps.handlers.base_bot.HEARTBEAT_INTERVAL", 0.1),
        ):
            # Start heartbeat for msg 100
            bot._start_heartbeat(42, 100)
            time.sleep(0.3)
            # Start new heartbeat for msg 200 (bumps gen, stops old)
            bot._start_heartbeat(42, 200)
            time.sleep(0.3)
            bot._stop_heartbeat()

        # msg 200 should have edits, msg 100 should have stopped
        assert 200 in edits_by_msg
        # After new start, no further edits to msg 100
        edits_100_count = len(edits_by_msg.get(100, []))
        edits_200_count = len(edits_by_msg.get(200, []))
        assert edits_200_count >= 1
        # Old thread may have gotten 1-2 edits before gen mismatch, but not indefinite
        assert edits_100_count <= 3

    def test_gen_increments_on_each_start(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text(json.dumps({"chat_id": 42, "delivered": True}), encoding="utf-8")

        assert bot._heartbeat_gen == 0
        with patch.object(bot, "edit_message"):
            bot._start_heartbeat(42, 100)
            assert bot._heartbeat_gen == 1
            bot._start_heartbeat(42, 200)
            assert bot._heartbeat_gen == 2
            bot._stop_heartbeat()


# =============================================
# 6. RAPID-FIRE: stranded placeholder finalized
# =============================================


class TestRapidFireFinalize:
    """When a new message overwrites undelivered pending, the old placeholder is finalized."""

    def test_superseded_placeholder_edited(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)

        # Simulate undelivered pending from msg 100 with processing_message_id 500
        prev_pending = {
            "chat_id": 42,
            "message_id": 100,
            "processing_message_id": 500,
            "timestamp": time.time(),
        }
        bot.pending_file.write_text(json.dumps(prev_pending), encoding="utf-8")

        with patch.object(bot, "edit_message") as mock_edit:
            bot._finalize_superseded_pending(200)

        mock_edit.assert_called_once_with(42, 500, "⏭ Superseded by newer message")

    def test_no_finalize_when_delivered(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)

        prev_pending = {
            "chat_id": 42,
            "message_id": 100,
            "processing_message_id": 500,
            "delivered": True,
            "timestamp": time.time(),
        }
        bot.pending_file.write_text(json.dumps(prev_pending), encoding="utf-8")

        with patch.object(bot, "edit_message") as mock_edit:
            bot._finalize_superseded_pending(200)

        mock_edit.assert_not_called()

    def test_no_finalize_when_no_pending(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        assert not bot.pending_file.exists()

        with patch.object(bot, "edit_message") as mock_edit:
            bot._finalize_superseded_pending(200)

        mock_edit.assert_not_called()

    def test_no_crash_on_corrupt_pending(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.pending_file.parent.mkdir(parents=True, exist_ok=True)
        bot.pending_file.write_text("not json{{{", encoding="utf-8")

        with patch.object(bot, "edit_message") as mock_edit:
            bot._finalize_superseded_pending(200)

        mock_edit.assert_not_called()
