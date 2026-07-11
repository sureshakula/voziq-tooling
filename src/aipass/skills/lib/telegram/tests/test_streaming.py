# =================== AIPass ====================
# Name: test_streaming.py
# Description: Tests for streaming edit-in-place (FPLAN-0297)
# Version: 1.0.0
# Created: 2026-07-01
# Modified: 2026-07-01
# =============================================

"""
Tests for streaming edit-in-place (FPLAN-0297).

Covers:
  - _format_content_block: single block → plain text
  - _format_stream_entries: batch block-mapping
  - _tail_transcript_bytes: incremental byte-offset JSONL tail
  - _stream_edit: 429/not-modified handling
  - _streaming_loop: full loop behaviour (throttle, rollover, fallback)
  - write_pending_file: streaming flag in pending file
  - Batch mode unchanged when stream=False
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aipass.skills.lib.telegram.apps.handlers.base_bot import BaseBot


# =============================================
# Fixtures
# =============================================


@pytest.fixture
def _patch_deps(tmp_path):
    """Patch signal and atexit for safe BaseBot construction."""
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


def _make_bot(tmp_path, _patch_deps, stream=False):
    """Create a BaseBot with test defaults."""
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path):
        bot = BaseBot(
            bot_id="stream_test",
            bot_token="123:FAKETOKEN",
            work_dir=workdir,
            bot_name="Stream Test Bot",
            allowed_user_ids=[111],
            branch_name="testbranch",
            stream=stream,
        )
    bot.send_message = MagicMock(return_value={"ok": True, "message_id": 1})
    bot.edit_message = MagicMock(return_value=True)
    return bot


def _write_transcript(path, entries):
    """Write JSONL entries to a file. Returns the file path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    path.write_bytes(content.encode("utf-8"))
    return path


def _assistant_entry(content_blocks, sidechain=False):
    """Build a transcript entry with assistant role."""
    entry: dict = {"message": {"role": "assistant", "content": content_blocks}}
    if sidechain:
        entry["isSidechain"] = True  # type: ignore[assignment]
    return entry


def _user_entry(text="hello"):
    """Build a transcript entry with user role."""
    return {"message": {"role": "user", "content": text}}


# =============================================
# 1. _format_content_block
# =============================================


class TestFormatContentBlock:
    """Unit tests for _format_content_block."""

    def test_text_block(self):
        result = BaseBot._format_content_block({"type": "text", "text": "Hello world"})
        assert result == "Hello world"

    def test_text_block_empty(self):
        result = BaseBot._format_content_block({"type": "text", "text": "   "})
        assert result is None

    def test_thinking_block(self):
        result = BaseBot._format_content_block({"type": "thinking", "thinking": "Let me think..."})
        assert result == "Thinking..."

    def test_tool_use_block(self):
        result = BaseBot._format_content_block({"type": "tool_use", "name": "Bash", "input": {}})
        assert result == "Running Bash..."

    def test_tool_use_no_name(self):
        result = BaseBot._format_content_block({"type": "tool_use"})
        assert result == "Running tool..."

    def test_unknown_type(self):
        result = BaseBot._format_content_block({"type": "server_tool_use"})
        assert result is None

    def test_not_dict(self):
        result = BaseBot._format_content_block("not a dict")
        assert result is None


# =============================================
# 2. _format_stream_entries
# =============================================


class TestFormatStreamEntries:
    """Unit tests for _format_stream_entries."""

    def test_text_entry(self):
        entries = [_assistant_entry([{"type": "text", "text": "Answer here"}])]
        result = BaseBot._format_stream_entries(entries)
        assert result == "Answer here\n"

    def test_thinking_then_text(self):
        entries = [
            _assistant_entry(
                [
                    {"type": "thinking", "thinking": "hmm"},
                    {"type": "text", "text": "Done"},
                ]
            )
        ]
        result = BaseBot._format_stream_entries(entries)
        assert result == "Thinking...\nDone\n"

    def test_tool_use_entry(self):
        entries = [_assistant_entry([{"type": "tool_use", "name": "Read"}])]
        result = BaseBot._format_stream_entries(entries)
        assert result == "Running Read...\n"

    def test_skips_user_role(self):
        entries = [_user_entry("hello")]
        result = BaseBot._format_stream_entries(entries)
        assert result == ""

    def test_skips_sidechain(self):
        entries = [_assistant_entry([{"type": "text", "text": "side"}], sidechain=True)]
        result = BaseBot._format_stream_entries(entries)
        assert result == ""

    def test_multiple_entries(self):
        entries = [
            _assistant_entry([{"type": "tool_use", "name": "Bash"}]),
            _assistant_entry([{"type": "text", "text": "Result"}]),
        ]
        result = BaseBot._format_stream_entries(entries)
        assert result == "Running Bash...\nResult\n"

    def test_string_content(self):
        entries = [{"message": {"role": "assistant", "content": "plain string"}}]
        result = BaseBot._format_stream_entries(entries)
        assert result == "plain string\n"

    def test_empty_entries(self):
        result = BaseBot._format_stream_entries([])
        assert result == ""


# =============================================
# 3. _tail_transcript_bytes
# =============================================


class TestTailTranscriptBytes:
    """Unit tests for _tail_transcript_bytes."""

    def test_new_lines_parsed(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps)
        transcript = tmp_path / "test.jsonl"
        entries = [_assistant_entry([{"type": "text", "text": "Hello"}])]
        _write_transcript(transcript, entries)

        result_entries, new_offset = bot._tail_transcript_bytes(transcript, 0)
        assert len(result_entries) == 1
        assert result_entries[0]["message"]["content"][0]["text"] == "Hello"
        assert new_offset > 0

    def test_no_new_content(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps)
        transcript = tmp_path / "test.jsonl"
        _write_transcript(transcript, [_assistant_entry([{"type": "text", "text": "Hi"}])])
        size = transcript.stat().st_size

        result_entries, new_offset = bot._tail_transcript_bytes(transcript, size)
        assert result_entries == []
        assert new_offset == size

    def test_partial_line_not_consumed(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps)
        transcript = tmp_path / "test.jsonl"
        complete = json.dumps(_assistant_entry([{"type": "text", "text": "A"}]))
        partial = '{"incomplete": true'
        transcript.write_bytes((complete + "\n" + partial).encode("utf-8"))

        result_entries, new_offset = bot._tail_transcript_bytes(transcript, 0)
        assert len(result_entries) == 1
        assert new_offset == len(complete.encode("utf-8")) + 1  # includes the \n

    def test_none_path(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps)
        result_entries, offset = bot._tail_transcript_bytes(None, 0)
        assert result_entries == []
        assert offset == 0

    def test_missing_file(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps)
        missing = tmp_path / "nonexistent.jsonl"
        result_entries, offset = bot._tail_transcript_bytes(missing, 0)
        assert result_entries == []
        assert offset == 0

    def test_incremental_reads(self, tmp_path, _patch_deps):
        """Two reads: first gets initial content, second gets appended content."""
        bot = _make_bot(tmp_path, _patch_deps)
        transcript = tmp_path / "test.jsonl"
        entry1 = _assistant_entry([{"type": "text", "text": "First"}])
        _write_transcript(transcript, [entry1])

        entries1, offset1 = bot._tail_transcript_bytes(transcript, 0)
        assert len(entries1) == 1

        entry2 = _assistant_entry([{"type": "text", "text": "Second"}])
        with open(transcript, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry2) + "\n")

        entries2, offset2 = bot._tail_transcript_bytes(transcript, offset1)
        assert len(entries2) == 1
        assert entries2[0]["message"]["content"][0]["text"] == "Second"
        assert offset2 > offset1


# =============================================
# 4. _stream_edit
# =============================================


class TestStreamEdit:
    """Unit tests for _stream_edit (429/not-modified handling)."""

    def test_success(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps)
        response = json.dumps({"ok": True}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = response
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.urlopen", return_value=mock_resp):
            ok, retry = bot._stream_edit(123, 456, "hello")
        assert ok is True
        assert retry == 0.0

    def test_429_returns_retry_after(self, tmp_path, _patch_deps):
        from urllib.error import HTTPError

        bot = _make_bot(tmp_path, _patch_deps)

        body = json.dumps(
            {
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests: retry after 15",
                "parameters": {"retry_after": 15},
            }
        ).encode("utf-8")
        err = HTTPError("url", 429, "Too Many Requests", None, None)  # type: ignore[arg-type]
        err.read = MagicMock(return_value=body)

        with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.urlopen", side_effect=err):
            ok, retry = bot._stream_edit(123, 456, "hello")
        assert ok is False
        assert retry == 15.0

    def test_400_not_modified_treated_as_ok(self, tmp_path, _patch_deps):
        from urllib.error import HTTPError

        bot = _make_bot(tmp_path, _patch_deps)

        body = json.dumps(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: message is not modified",
            }
        ).encode("utf-8")
        err = HTTPError("url", 400, "Bad Request", None, None)  # type: ignore[arg-type]
        err.read = MagicMock(return_value=body)

        with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.urlopen", side_effect=err):
            ok, retry = bot._stream_edit(123, 456, "same text")
        assert ok is True
        assert retry == 0.0

    def test_other_error(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps)
        with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.urlopen", side_effect=ConnectionError("fail")):
            ok, retry = bot._stream_edit(123, 456, "hello")
        assert ok is False
        assert retry == 0.0


# =============================================
# 5. Pending file streaming flag
# =============================================


class TestPendingFileStreaming:
    """Tests for streaming flag in write_pending_file."""

    def test_no_streaming_key_when_off(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps, stream=False)
        with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path):
            bot.pending_file = tmp_path / "bot-stream_test.json"
            bot.write_pending_file(123, 1, 2)
        data = json.loads(bot.pending_file.read_text(encoding="utf-8"))
        assert "streaming" not in data

    def test_streaming_true_when_on(self, tmp_path, _patch_deps):
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        with patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path):
            bot.pending_file = tmp_path / "bot-stream_test.json"
            bot.write_pending_file(123, 1, 2)
        data = json.loads(bot.pending_file.read_text(encoding="utf-8"))
        assert data["streaming"] is True


# =============================================
# 6. Batch mode unchanged
# =============================================


class TestBatchModeUnchanged:
    """Prove batch mode (stream=False) is byte-for-byte unchanged."""

    def test_heartbeat_uses_edit_message_not_stream(self, tmp_path, _patch_deps):
        """When stream=False, heartbeat calls edit_message (batch), not _stream_edit."""
        bot = _make_bot(tmp_path, _patch_deps, stream=False)
        bot._stream_edit = MagicMock(return_value=(True, 0.0))
        bot._tmux_session_exists = MagicMock(return_value=True)

        call_count = [0]

        def delivered_after_one():
            call_count[0] += 1
            return call_count[0] >= 2

        bot._is_pending_delivered = delivered_after_one
        bot._heartbeat_stop = threading.Event()
        bot._start_heartbeat(123, 456)
        if bot._heartbeat_thread:
            bot._heartbeat_thread.join(timeout=35)
        bot._stream_edit.assert_not_called()
        bot.edit_message.assert_called()

    def test_stream_false_no_transcript_tail(self, tmp_path, _patch_deps):
        """When stream=False, _tail_transcript_bytes is never called."""
        bot = _make_bot(tmp_path, _patch_deps, stream=False)
        bot._tail_transcript_bytes = MagicMock()
        bot._heartbeat_stop = threading.Event()

        call_count = [0]

        def delivered_after_first():
            call_count[0] += 1
            return call_count[0] >= 1

        bot._is_pending_delivered = delivered_after_first
        bot._start_heartbeat(123, 456)
        if bot._heartbeat_thread:
            bot._heartbeat_thread.join(timeout=5)
        bot._tail_transcript_bytes.assert_not_called()


# =============================================
# 7. Streaming loop integration
# =============================================


class TestStreamingLoop:
    """Integration tests for _streaming_loop."""

    def test_edits_with_transcript_content(self, tmp_path, _patch_deps):
        """Streaming loop edits the processing message with transcript text."""
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        transcript = tmp_path / "transcript.jsonl"
        bot._active_transcript_path = transcript

        entry = _assistant_entry([{"type": "text", "text": "Live answer"}])
        _write_transcript(transcript, [entry])

        bot._stream_edit = MagicMock(return_value=(True, 0.0))

        call_count = [0]

        def stop_after_three():
            call_count[0] += 1
            return call_count[0] >= 3

        bot._is_pending_delivered = stop_after_three
        bot._tmux_session_exists = MagicMock(return_value=True)

        # Write transcript AFTER byte_offset init (simulating turn content arriving)
        original_stat = Path.stat

        def fake_stat(self_path):
            if self_path == transcript:
                # Return 0 size initially so the loop reads from start
                return type("FakeStat", (), {"st_size": 0})()
            return original_stat(self_path)

        bot._heartbeat_stop = threading.Event()
        with patch.object(Path, "stat", fake_stat):
            bot._streaming_loop(123, 456, time.time())

        assert bot._stream_edit.call_count >= 1
        edit_text = bot._stream_edit.call_args[0][2]
        assert "Live answer" in edit_text

    def test_skips_unchanged_buffer(self, tmp_path, _patch_deps):
        """Streaming loop does not edit when buffer hasn't changed."""
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        transcript = tmp_path / "transcript.jsonl"
        bot._active_transcript_path = transcript
        _write_transcript(transcript, [])

        call_count = [0]

        def stop_after_three():
            call_count[0] += 1
            return call_count[0] >= 3

        bot._is_pending_delivered = stop_after_three
        bot._tmux_session_exists = MagicMock(return_value=True)
        bot._stream_edit = MagicMock(return_value=(True, 0.0))
        bot._heartbeat_stop = threading.Event()

        bot._streaming_loop(123, 456, time.time())

        # Should show "Processing..." but not re-edit identical text
        first_call_text = bot._stream_edit.call_args_list[0][0][2] if bot._stream_edit.call_count > 0 else ""
        for call_args in bot._stream_edit.call_args_list[1:]:
            assert call_args[0][2] != first_call_text or "Processing..." not in first_call_text

    def test_4096_rollover(self, tmp_path, _patch_deps):
        """Buffer exceeding 4096 chars triggers message rollover."""
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        transcript = tmp_path / "transcript.jsonl"
        bot._active_transcript_path = transcript

        big_text = "A" * 5000
        entry = _assistant_entry([{"type": "text", "text": big_text}])
        _write_transcript(transcript, [entry])

        bot._stream_edit = MagicMock(return_value=(True, 0.0))
        bot.send_message = MagicMock(return_value={"message_id": 999})

        call_count = [0]

        def stop_after_three():
            call_count[0] += 1
            return call_count[0] >= 3

        bot._is_pending_delivered = stop_after_three
        bot._tmux_session_exists = MagicMock(return_value=True)
        bot._heartbeat_stop = threading.Event()

        with patch.object(Path, "stat", lambda s: type("S", (), {"st_size": 0})()):
            bot._streaming_loop(123, 456, time.time())

        # Should have called send_message for the rollover
        bot.send_message.assert_called()

    def test_429_pauses_edits(self, tmp_path, _patch_deps):
        """After a 429, streaming loop skips edits until retry_after elapses."""
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        transcript = tmp_path / "transcript.jsonl"
        bot._active_transcript_path = transcript

        entry = _assistant_entry([{"type": "text", "text": "data"}])
        _write_transcript(transcript, [entry])

        edit_calls = [0]

        def rate_limited_edit(_chat, _msg, _text):
            edit_calls[0] += 1
            if edit_calls[0] == 1:
                return False, 9999.0  # huge backoff
            return True, 0.0

        bot._stream_edit = MagicMock(side_effect=rate_limited_edit)

        tick = [0]

        def stop_after_three():
            tick[0] += 1
            return tick[0] >= 3

        bot._is_pending_delivered = stop_after_three
        bot._tmux_session_exists = MagicMock(return_value=True)
        bot._heartbeat_stop = threading.Event()

        with patch.object(Path, "stat", lambda s: type("S", (), {"st_size": 0})()):
            bot._streaming_loop(123, 456, time.time())

        # Only 1 edit attempt — subsequent ticks skipped due to 429 backoff
        assert bot._stream_edit.call_count == 1

    def test_fallback_to_batch_when_no_transcript(self, tmp_path, _patch_deps):
        """When stream=True but no transcript path, falls back to batch heartbeat."""
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        bot._active_transcript_path = None  # no transcript
        bot._stream_edit = MagicMock(return_value=(True, 0.0))
        bot._tmux_session_exists = MagicMock(return_value=True)

        call_count = [0]

        def delivered_after_one():
            call_count[0] += 1
            return call_count[0] >= 2

        bot._is_pending_delivered = delivered_after_one
        bot._heartbeat_stop = threading.Event()
        bot._start_heartbeat(123, 456)
        if bot._heartbeat_thread:
            bot._heartbeat_thread.join(timeout=35)

        # Batch mode: edit_message called, _stream_edit not called
        bot.edit_message.assert_called()
        bot._stream_edit.assert_not_called()

    def test_mid_loop_delivery_breaks_without_edit(self, tmp_path, _patch_deps):
        """If _is_pending_delivered flips True mid-loop, loop breaks with no _stream_edit."""
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        transcript = tmp_path / "transcript.jsonl"
        bot._active_transcript_path = transcript

        entry = _assistant_entry([{"type": "text", "text": "Should not be sent"}])
        _write_transcript(transcript, [entry])

        delivered = [False]

        def flip_on_second_check():
            if delivered[0]:
                return True
            delivered[0] = True
            return False

        bot._is_pending_delivered = flip_on_second_check
        bot._tmux_session_exists = MagicMock(return_value=True)
        bot._stream_edit = MagicMock(return_value=(True, 0.0))
        bot._heartbeat_stop = threading.Event()

        with patch.object(Path, "stat", lambda s: type("S", (), {"st_size": 0})()):
            bot._streaming_loop(123, 456, time.time())

        bot._stream_edit.assert_not_called()

    def test_stream_flag_wired_from_init(self, tmp_path, _patch_deps):
        """stream=True in constructor sets self._stream."""
        bot = _make_bot(tmp_path, _patch_deps, stream=True)
        assert bot._stream is True

    def test_stream_default_false(self, tmp_path, _patch_deps):
        """stream defaults to False."""
        bot = _make_bot(tmp_path, _patch_deps)
        assert bot._stream is False
