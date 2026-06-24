# =================== AIPass ====================
# Name: test_telegram_response.py
# Version: 1.0.0
# Description: Tests for telegram_response notification handler
# Branch: hooks
# Layer: tests
# Created: 2026-06-15
# Modified: 2026-06-15
# =============================================

"""Tests for handlers/notification/telegram_response.py."""

import io
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# All tests use local imports per project convention.
# The prax logger is mocked at module level to avoid import-time dependency.
LOGGER_PATCH = "aipass.hooks.apps.handlers.notification.telegram_response.logger"
MOD = "aipass.hooks.apps.handlers.notification.telegram_response"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jsonl_line(entry_type: str, text: str = "", *, sidechain: bool = False, tool_result: bool = False) -> str:
    """Build a single JSONL transcript line."""
    if tool_result and entry_type == "user":
        content = [{"type": "tool_result", "content": "ok"}]
    elif text:
        content = [{"type": "text", "text": text}]
    else:
        content = []

    entry: dict = {"type": entry_type, "message": {"content": content}}
    if sidechain:
        entry["isSidechain"] = True
    return json.dumps(entry)


def _make_pending(tmp_path: Path, name: str = "bot-123.json", **overrides) -> Path:
    """Create a pending file with sensible defaults."""
    data = {
        "chat_id": 999,
        "bot_token": "tok:ABC",
        "timestamp": time.time(),
        "work_dir": str(tmp_path),
        **overrides,
    }
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _mock_urlopen_ok():
    """Return a context-manager mock whose read() returns Telegram ok response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({"ok": True}).encode()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _mock_urlopen_fail():
    """Return a context-manager mock whose read() returns Telegram not-ok response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps({"ok": False, "description": "bad"}).encode()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ===========================================================================
# Layer 1 defense — handle() early returns
# ===========================================================================


class TestHandleLayer1Defense:
    """Layer 1: gate-level filtering in handle()."""

    def test_subagent_stop_returns_early(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        with patch(LOGGER_PATCH):
            result = handle({"hook_event_name": "SubagentStop", "session_id": "abc"})

        assert result == {"stdout": "", "exit_code": 0}

    def test_subagent_transcript_path_returns_early(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        with patch(LOGGER_PATCH):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "abc",
                    "transcript_path": "/home/user/.claude/sessions/subagents/12345.jsonl",
                }
            )

        assert result == {"stdout": "", "exit_code": 0}

    def test_no_session_id_returns_early(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        with patch(LOGGER_PATCH):
            result = handle({"hook_event_name": "Stop"})

        assert result == {"stdout": "", "exit_code": 0}

    def test_no_pending_file_returns_early(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        with patch(LOGGER_PATCH), patch(f"{MOD}.find_pending_file", return_value=None):
            result = handle({"hook_event_name": "Stop", "session_id": "abc123"})

        assert result == {"stdout": "", "exit_code": 0}


# ===========================================================================
# find_pending_file
# ===========================================================================


class TestFindPendingFile:
    """Multi-bot pending file resolution."""

    def test_env_bot_id_direct_match(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import find_pending_file

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        data = {"timestamp": time.time(), "work_dir": str(tmp_path)}
        (pending_dir / "bot-42.json").write_text(json.dumps(data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.PENDING_DIR", pending_dir),
            patch.dict("os.environ", {"AIPASS_BOT_ID": "42"}),
        ):
            result = find_pending_file("session-xyz")

        assert result is not None
        assert result.name == "bot-42.json"

    def test_cwd_relative_match(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import find_pending_file

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        work = tmp_path / "project"
        work.mkdir()
        data = {"timestamp": time.time(), "work_dir": str(work)}
        (pending_dir / "bot-7.json").write_text(json.dumps(data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.PENDING_DIR", pending_dir),
            patch.dict("os.environ", {}, clear=True),
            patch(f"{MOD}.Path.cwd", return_value=work / "subdir"),
        ):
            # subdir is relative to work_dir, so it should match
            result = find_pending_file("session-abc")

        assert result is not None
        assert result.name == "bot-7.json"

    def test_no_pending_dir_returns_none(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import find_pending_file

        missing = tmp_path / "nonexistent"

        with patch(LOGGER_PATCH), patch(f"{MOD}.PENDING_DIR", missing):
            result = find_pending_file("session-abc")

        assert result is None

    def test_expired_pending_skipped(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import find_pending_file

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        old_ts = time.time() - 7200  # 2 hours ago
        data = {"timestamp": old_ts, "work_dir": str(tmp_path)}
        (pending_dir / "bot-9.json").write_text(json.dumps(data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.PENDING_DIR", pending_dir),
            patch.dict("os.environ", {"AIPASS_BOT_ID": "9"}),
            patch(f"{MOD}.subprocess.run") as mock_tmux,
        ):
            mock_tmux.side_effect = OSError("no tmux")
            result = find_pending_file("session-xyz")

        assert result is None

    def test_non_expired_pending_returned(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import find_pending_file

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        data = {"timestamp": time.time(), "work_dir": str(tmp_path)}
        (pending_dir / "bot-5.json").write_text(json.dumps(data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.PENDING_DIR", pending_dir),
            patch.dict("os.environ", {"AIPASS_BOT_ID": "5"}),
        ):
            result = find_pending_file("session-abc")

        assert result is not None
        assert result.name == "bot-5.json"

    def test_no_work_dir_in_pending_skipped(self, tmp_path):
        """When CWD fallback is used and pending has no work_dir, skip it."""
        from aipass.hooks.apps.handlers.notification.telegram_response import find_pending_file

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        data = {"timestamp": time.time()}  # no work_dir
        (pending_dir / "bot-1.json").write_text(json.dumps(data), encoding="utf-8")

        with patch(LOGGER_PATCH), patch(f"{MOD}.PENDING_DIR", pending_dir), patch.dict("os.environ", {}, clear=True):
            result = find_pending_file("session-abc")

        assert result is None


# ===========================================================================
# _is_expired
# ===========================================================================


class TestIsExpired:
    """TTL + tmux-alive expiry logic."""

    def test_fresh_not_expired(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _is_expired

        with patch(LOGGER_PATCH):
            assert _is_expired({"timestamp": time.time()}) is False

    def test_old_no_tmux_expired(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _is_expired

        with patch(LOGGER_PATCH), patch(f"{MOD}.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("no tmux")
            assert _is_expired({"timestamp": time.time() - 7200}) is True

    def test_old_tmux_alive_not_expired(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _is_expired

        tmux_result = MagicMock()
        tmux_result.returncode = 0

        with patch(LOGGER_PATCH), patch(f"{MOD}.subprocess.run", return_value=tmux_result):
            result = _is_expired(
                {
                    "timestamp": time.time() - 7200,
                    "session_name": "my-session",
                }
            )

        assert result is False

    def test_old_tmux_dead_expired(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _is_expired

        tmux_result = MagicMock()
        tmux_result.returncode = 1

        with patch(LOGGER_PATCH), patch(f"{MOD}.subprocess.run", return_value=tmux_result):
            result = _is_expired(
                {
                    "timestamp": time.time() - 7200,
                    "session_name": "dead-session",
                }
            )

        assert result is True

    def test_string_timestamp_handling(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _is_expired

        with patch(LOGGER_PATCH):
            assert _is_expired({"timestamp": str(time.time())}) is False

    def test_invalid_string_timestamp_treated_as_zero(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _is_expired

        with patch(LOGGER_PATCH), patch(f"{MOD}.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("no tmux")
            assert _is_expired({"timestamp": "not-a-number"}) is True

    def test_no_session_name_old_expired(self):
        """Old entry with no session_name -> expired (tmux check skipped)."""
        from aipass.hooks.apps.handlers.notification.telegram_response import _is_expired

        with patch(LOGGER_PATCH):
            assert _is_expired({"timestamp": time.time() - 7200}) is True


# ===========================================================================
# extract_assistant_response
# ===========================================================================


class TestExtractAssistantResponse:
    """JSONL transcript extraction with Layer 2 and Layer 3 defenses."""

    def test_normal_extraction(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Hello"),
            _jsonl_line("assistant", "Hi there!"),
            _jsonl_line("assistant", "How can I help?"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        assert result == "Hi there!\n\nHow can I help?"

    def test_sidechain_entries_skipped(self, tmp_path):
        """Layer 2: isSidechain entries are filtered out."""
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Hello"),
            _jsonl_line("assistant", "Sidechain noise", sidechain=True),
            _jsonl_line("assistant", "Real response"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        assert result == "Real response"
        assert "Sidechain noise" not in result

    def test_sidechain_user_message_skipped(self, tmp_path):
        """Layer 2: sidechain user messages are not treated as the last user message."""
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "First real question"),
            _jsonl_line("assistant", "First answer"),
            _jsonl_line("user", "Sidechain user msg", sidechain=True),
            _jsonl_line("assistant", "Sidechain assistant response", sidechain=True),
            _jsonl_line("assistant", "Continuation of first answer"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        # Last real user message is "First real question"; assistants after it (non-sidechain)
        assert result is not None
        assert "First answer" in result
        assert "Continuation of first answer" in result
        assert "Sidechain assistant response" not in result

    def test_start_line_offset(self, tmp_path):
        """Layer 3: transcript_line_after skips earlier entries."""
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Old question"),  # line 0
            _jsonl_line("assistant", "Old answer"),  # line 1
            _jsonl_line("user", "New question"),  # line 2
            _jsonl_line("assistant", "New answer"),  # line 3
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript), start_line=2)

        assert result == "New answer"

    def test_tool_result_only_user_message_skipped(self, tmp_path):
        """User messages that contain only tool_result blocks are not real user messages."""
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Real question"),
            _jsonl_line("assistant", "Starting work..."),
            _jsonl_line("user", tool_result=True),  # tool_result only
            _jsonl_line("assistant", "Done with the work"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        # The last real user message is "Real question", so we get everything after it
        assert result is not None
        assert "Starting work..." in result
        assert "Done with the work" in result

    def test_no_user_message_returns_none(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("assistant", "Hello"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        assert result is None

    def test_empty_transcript_returns_none(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("", encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        assert result is None

    def test_missing_transcript_returns_none(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        with patch(LOGGER_PATCH):
            result = extract_assistant_response("/nonexistent/path.jsonl")

        assert result is None

    def test_corrupt_jsonl_lines_skipped(self, tmp_path):
        """Malformed JSON lines are gracefully skipped."""
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Question"),
            "this is not valid json {{{",
            _jsonl_line("assistant", "Answer"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        assert result == "Answer"

    def test_no_assistant_text_after_user_returns_none(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Question"),
            # No assistant response follows
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        with patch(LOGGER_PATCH):
            result = extract_assistant_response(str(transcript))

        assert result is None


# ===========================================================================
# chunk_text
# ===========================================================================


class TestChunkText:
    """Text splitting for Telegram's 4096-char limit."""

    def test_short_text_single_chunk(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        result = chunk_text("Hello world")
        assert result == ["Hello world"]

    def test_exact_limit_single_chunk(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        text = "x" * 4096
        result = chunk_text(text)
        assert len(result) == 1

    def test_long_text_multiple_chunks(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        text = "Hello world. " * 1000  # ~13000 chars
        result = chunk_text(text, limit=500)
        assert len(result) > 1
        # Reconstruct and verify nothing lost
        for chunk in result:
            assert len(chunk) <= 500

    def test_break_at_sentence_end(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        # Build text where a sentence ends near the limit boundary
        sentence = "A" * 480 + ". "
        text = sentence + "B" * 200
        result = chunk_text(text, limit=500)
        assert len(result) == 2
        assert result[0].endswith(".")

    def test_break_at_paragraph(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        para1 = "A" * 300
        para2 = "B" * 300
        text = para1 + "\n\n" + para2
        result = chunk_text(text, limit=400)
        assert len(result) == 2

    def test_break_at_newline(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        part1 = "A" * 300
        part2 = "B" * 300
        text = part1 + "\n" + part2
        result = chunk_text(text, limit=400)
        assert len(result) == 2

    def test_break_at_space(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        # Words with spaces — no sentence endings, no newlines in the break zone
        text = ("word " * 100).strip()  # ~499 chars
        result = chunk_text(text, limit=200)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 200

    def test_empty_text(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import chunk_text

        result = chunk_text("")
        assert result == [""]


# ===========================================================================
# markdown_to_telegram_html
# ===========================================================================


class TestMarkdownToTelegramHtml:
    """Markdown -> Telegram HTML conversion."""

    def test_code_blocks_preserved(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "Before\n```python\nprint('hello')\n```\nAfter"
        result = markdown_to_telegram_html(text)
        assert '<pre><code class="language-python">' in result
        assert "print(" in result and "hello" in result

    def test_code_block_no_language(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "Before\n```\nsome code\n```\nAfter"
        result = markdown_to_telegram_html(text)
        assert "<pre>" in result
        assert "some code" in result

    def test_inline_code_preserved(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "Use `foo()` here"
        result = markdown_to_telegram_html(text)
        assert "<code>foo()</code>" in result

    def test_bold_converted(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "This is **bold** text"
        result = markdown_to_telegram_html(text)
        assert "<b>bold</b>" in result

    def test_italic_converted(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "This is *italic* text"
        result = markdown_to_telegram_html(text)
        assert "<i>italic</i>" in result

    def test_html_entities_escaped(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "Use <div> & stuff > here"
        result = markdown_to_telegram_html(text)
        assert "&lt;div&gt;" in result
        assert "&amp;" in result

    def test_mixed_content(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "**Bold** and *italic* with `code` and <tag>"
        result = markdown_to_telegram_html(text)
        assert "<b>Bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<code>code</code>" in result
        assert "&lt;tag&gt;" in result

    def test_code_block_content_not_formatted(self):
        """Markdown inside code blocks should not be converted to HTML tags."""
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "```\n**not bold** *not italic*\n```"
        result = markdown_to_telegram_html(text)
        # Inside <pre>, the ** and * should be escaped, not converted
        assert "<b>" not in result.split("<pre>")[1].split("</pre>")[0]
        assert "<i>" not in result.split("<pre>")[1].split("</pre>")[0]

    def test_inline_code_content_not_formatted(self):
        """Markdown inside inline code should not be converted."""
        from aipass.hooks.apps.handlers.notification.telegram_response import markdown_to_telegram_html

        text = "Use `**not bold**` here"
        result = markdown_to_telegram_html(text)
        # The ** should be present as literal text inside <code>
        code_content = result.split("<code>")[1].split("</code>")[0]
        assert "<b>" not in code_content


# ===========================================================================
# send_to_telegram
# ===========================================================================


class TestSendToTelegram:
    """Telegram Bot API send with HTML->plain text fallback."""

    def test_successful_html_send(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import send_to_telegram

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", return_value=_mock_urlopen_ok()):
            result = send_to_telegram("tok:ABC", 123, "Hello")

        assert result is True

    def test_html_fails_plain_text_fallback_succeeds(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import send_to_telegram

        call_count = 0

        def urlopen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("HTML parse error")
            return _mock_urlopen_ok()

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=urlopen_side_effect):
            result = send_to_telegram("tok:ABC", 123, "Hello **bold**")

        assert result is True
        assert call_count == 2

    def test_html_fails_plain_text_also_fails(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import send_to_telegram

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=Exception("network error")):
            result = send_to_telegram("tok:ABC", 123, "Hello")

        assert result is False

    def test_http_error_handling(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import send_to_telegram
        from urllib.error import HTTPError

        call_count = 0

        def urlopen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("HTML error")
            err = HTTPError(
                url="https://api.telegram.org/bot/sendMessage",
                code=400,
                msg="Bad Request",
                hdrs=MagicMock(),  # type: ignore[arg-type]
                fp=io.BytesIO(json.dumps({"description": "bad request"}).encode()),
            )
            raise err

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=urlopen_side_effect):
            result = send_to_telegram("tok:ABC", 123, "Hello")

        assert result is False

    def test_url_error_handling(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import send_to_telegram
        from urllib.error import URLError

        call_count = 0

        def urlopen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("HTML error")
            raise URLError("DNS failure")

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=urlopen_side_effect):
            result = send_to_telegram("tok:ABC", 123, "Hello")

        assert result is False

    def test_reply_to_message_id_included(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import send_to_telegram

        captured_requests = []

        def urlopen_capture(req, **kwargs):
            captured_requests.append(json.loads(req.data.decode()))
            return _mock_urlopen_ok()

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=urlopen_capture):
            send_to_telegram("tok:ABC", 123, "Hello", message_id=456)

        assert captured_requests[0]["reply_to_message_id"] == 456


# ===========================================================================
# edit_telegram_message
# ===========================================================================


class TestEditTelegramMessage:
    """Telegram Bot API edit with HTML->plain text fallback."""

    def test_successful_html_edit(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import edit_telegram_message

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", return_value=_mock_urlopen_ok()):
            result = edit_telegram_message("tok:ABC", 123, 789, "Updated text")

        assert result is True

    def test_html_edit_fails_plain_text_fallback(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import edit_telegram_message

        call_count = 0

        def urlopen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("HTML edit error")
            return _mock_urlopen_ok()

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=urlopen_side_effect):
            result = edit_telegram_message("tok:ABC", 123, 789, "Updated")

        assert result is True

    def test_both_fail_returns_false(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import edit_telegram_message

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=Exception("total failure")):
            result = edit_telegram_message("tok:ABC", 123, 789, "Text")

        assert result is False

    def test_edit_url_uses_editMessageText(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import edit_telegram_message

        captured_urls = []

        def urlopen_capture(req, **kwargs):
            captured_urls.append(req.full_url)
            return _mock_urlopen_ok()

        with patch(LOGGER_PATCH), patch(f"{MOD}.urlopen", side_effect=urlopen_capture):
            edit_telegram_message("tok:ABC", 123, 789, "Text")

        assert "editMessageText" in captured_urls[0]


# ===========================================================================
# handle — integration tests
# ===========================================================================


class TestHandleIntegration:
    """Full handle() flow integration tests."""

    def test_happy_path_send_and_cleanup(self, tmp_path):
        """Full flow: pending exists -> extract -> send -> cleanup."""
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        # Set up transcript
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Hello"),
            _jsonl_line("assistant", "Hi there!"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        # Set up pending file
        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        pending_data = {
            "chat_id": 999,
            "bot_token": "tok:ABC",
            "timestamp": time.time(),
            "work_dir": str(tmp_path),
        }
        pending_file = pending_dir / "bot-1.json"
        pending_file.write_text(json.dumps(pending_data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.find_pending_file", return_value=pending_file),
            patch(f"{MOD}.urlopen", return_value=_mock_urlopen_ok()),
            patch(f"{MOD}._check_log_streamer_active", return_value=False),
            patch(f"{MOD}.Path.cwd", return_value=tmp_path),
        ):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-abc",
                    "transcript_path": str(transcript),
                }
            )

        assert result == {"stdout": "", "exit_code": 0}
        # Pending should be cleaned up on success
        assert not pending_file.exists()

    def test_send_fails_pending_kept(self, tmp_path):
        """When delivery fails, pending file is kept for retry."""
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Hello"),
            _jsonl_line("assistant", "Response"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        pending_data = {
            "chat_id": 999,
            "bot_token": "tok:ABC",
            "timestamp": time.time(),
            "work_dir": str(tmp_path),
        }
        pending_file = pending_dir / "bot-1.json"
        pending_file.write_text(json.dumps(pending_data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.find_pending_file", return_value=pending_file),
            patch(f"{MOD}.urlopen", side_effect=Exception("network down")),
            patch(f"{MOD}._check_log_streamer_active", return_value=False),
            patch(f"{MOD}.time.sleep"),
            patch(f"{MOD}.Path.cwd", return_value=tmp_path),
        ):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-abc",
                    "transcript_path": str(transcript),
                }
            )

        assert result == {"stdout": "", "exit_code": 0}
        # Pending should still exist
        assert pending_file.exists()

    def test_no_response_text_pending_kept(self, tmp_path):
        """When no response text is extracted, pending is kept."""
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("", encoding="utf-8")  # empty transcript

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        pending_data = {
            "chat_id": 999,
            "bot_token": "tok:ABC",
            "timestamp": time.time(),
            "work_dir": str(tmp_path),
        }
        pending_file = pending_dir / "bot-1.json"
        pending_file.write_text(json.dumps(pending_data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.find_pending_file", return_value=pending_file),
            patch(f"{MOD}._check_log_streamer_active", return_value=False),
            patch(f"{MOD}.time.sleep"),
            patch(f"{MOD}.Path.cwd", return_value=tmp_path),
        ):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-abc",
                    "transcript_path": str(transcript),
                    "last_assistant_message": "",
                }
            )

        assert result == {"stdout": "", "exit_code": 0}
        assert pending_file.exists()

    def test_jsonl_retry_mechanism(self, tmp_path):
        """JSONL extraction retries on flush-race (empty first attempt)."""
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        transcript = tmp_path / "transcript.jsonl"
        lines = [
            _jsonl_line("user", "Hello"),
            _jsonl_line("assistant", "Answer"),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        pending_data = {
            "chat_id": 999,
            "bot_token": "tok:ABC",
            "timestamp": time.time(),
            "work_dir": str(tmp_path),
        }
        pending_file = pending_dir / "bot-1.json"
        pending_file.write_text(json.dumps(pending_data), encoding="utf-8")

        # Import to get the original function reference
        from aipass.hooks.apps.handlers.notification.telegram_response import extract_assistant_response

        extract_call_count = 0
        original_extract = extract_assistant_response

        def mock_extract(tp: str, start_line: int = 0) -> str | None:
            nonlocal extract_call_count
            extract_call_count += 1
            if extract_call_count == 1:
                return None  # Simulate flush-race
            return original_extract(tp, start_line=start_line)

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.find_pending_file", return_value=pending_file),
            patch(f"{MOD}.extract_assistant_response", side_effect=mock_extract),
            patch(f"{MOD}.urlopen", return_value=_mock_urlopen_ok()),
            patch(f"{MOD}._check_log_streamer_active", return_value=False),
            patch(f"{MOD}.time.sleep"),
            patch(f"{MOD}.Path.cwd", return_value=tmp_path),
        ):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-abc",
                    "transcript_path": str(transcript),
                }
            )

        assert result == {"stdout": "", "exit_code": 0}
        assert extract_call_count >= 2
        assert not pending_file.exists()

    def test_fallback_to_last_assistant_message(self, tmp_path):
        """When JSONL extraction fails, falls back to last_assistant_message from hook_data."""
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        pending_data = {
            "chat_id": 999,
            "bot_token": "tok:ABC",
            "timestamp": time.time(),
            "work_dir": str(tmp_path),
        }
        pending_file = pending_dir / "bot-1.json"
        pending_file.write_text(json.dumps(pending_data), encoding="utf-8")

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.find_pending_file", return_value=pending_file),
            patch(f"{MOD}.urlopen", return_value=_mock_urlopen_ok()),
            patch(f"{MOD}._check_log_streamer_active", return_value=False),
            patch(f"{MOD}.time.sleep"),
            patch(f"{MOD}.Path.cwd", return_value=tmp_path),
        ):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-abc",
                    "transcript_path": "",
                    "last_assistant_message": "Fallback text",
                }
            )

        assert result == {"stdout": "", "exit_code": 0}
        assert not pending_file.exists()

    def test_missing_chat_id_cleans_pending(self, tmp_path):
        """Pending with missing chat_id is cleaned up."""
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        pending_data = {
            "bot_token": "tok:ABC",
            "timestamp": time.time(),
            # no chat_id
        }
        pending_file = pending_dir / "bot-1.json"
        pending_file.write_text(json.dumps(pending_data), encoding="utf-8")

        with patch(LOGGER_PATCH), patch(f"{MOD}.find_pending_file", return_value=pending_file):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-abc",
                }
            )

        assert result == {"stdout": "", "exit_code": 0}
        assert not pending_file.exists()

    def test_corrupt_pending_file_cleaned(self, tmp_path):
        """Corrupt pending JSON is handled gracefully and cleaned up."""
        from aipass.hooks.apps.handlers.notification.telegram_response import handle

        pending_dir = tmp_path / "telegram_pending"
        pending_dir.mkdir()
        pending_file = pending_dir / "bot-1.json"
        pending_file.write_text("this is not json{{{", encoding="utf-8")

        with patch(LOGGER_PATCH), patch(f"{MOD}.find_pending_file", return_value=pending_file):
            result = handle(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-abc",
                }
            )

        assert result == {"stdout": "", "exit_code": 0}
        assert not pending_file.exists()


# ===========================================================================
# _send_with_retry
# ===========================================================================


class TestSendWithRetry:
    """Retry mechanism with exponential backoff."""

    def test_success_on_first_try(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _send_with_retry

        with patch(LOGGER_PATCH), patch(f"{MOD}.send_to_telegram", return_value=True) as mock_send:
            result = _send_with_retry("tok:ABC", 123, "Hello")

        assert result is True
        assert mock_send.call_count == 1

    def test_success_on_retry(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _send_with_retry

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.send_to_telegram", side_effect=[False, True]) as mock_send,
            patch(f"{MOD}.time.sleep"),
        ):
            result = _send_with_retry("tok:ABC", 123, "Hello")

        assert result is True
        assert mock_send.call_count == 2

    def test_all_retries_fail(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _send_with_retry

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.send_to_telegram", return_value=False) as mock_send,
            patch(f"{MOD}.time.sleep"),
        ):
            result = _send_with_retry("tok:ABC", 123, "Hello", retries=3)

        assert result is False
        assert mock_send.call_count == 3


# ===========================================================================
# _prepend_branch_prefix
# ===========================================================================


class TestPrependBranchPrefix:
    """Branch prefix added to response text."""

    def test_adds_branch_prefix(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.telegram_response import _prepend_branch_prefix

        with patch(LOGGER_PATCH), patch(f"{MOD}.Path.cwd", return_value=tmp_path / "hooks"):
            result = _prepend_branch_prefix("Hello")

        assert result == "@hooks\n\nHello"

    def test_cwd_failure_returns_original(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _prepend_branch_prefix

        with patch(LOGGER_PATCH), patch(f"{MOD}.Path.cwd", side_effect=OSError("no cwd")):
            result = _prepend_branch_prefix("Hello")

        assert result == "Hello"


# ===========================================================================
# _deliver_chunks
# ===========================================================================


class TestDeliverChunks:
    """Chunk delivery with edit/send logic."""

    def test_single_chunk_no_processing_msg(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _deliver_chunks

        with patch(LOGGER_PATCH), patch(f"{MOD}._send_with_retry", return_value=True) as mock_send:
            result = _deliver_chunks(["Hello"], "tok", 123, None, False)

        assert result is True
        mock_send.assert_called_once_with("tok", 123, "Hello")

    def test_single_chunk_with_processing_msg_edits(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _deliver_chunks

        with patch(LOGGER_PATCH), patch(f"{MOD}.edit_telegram_message", return_value=True) as mock_edit:
            result = _deliver_chunks(["Hello"], "tok", 123, 789, False)

        assert result is True
        mock_edit.assert_called_once_with("tok", 123, 789, "Hello")

    def test_single_chunk_edit_fails_falls_back_to_send(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _deliver_chunks

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.edit_telegram_message", return_value=False),
            patch(f"{MOD}._send_with_retry", return_value=True) as mock_send,
        ):
            result = _deliver_chunks(["Hello"], "tok", 123, 789, False)

        assert result is True
        mock_send.assert_called_once()

    def test_logs_active_sends_done_then_sends_new(self):
        """When logs were active, edit processing msg to 'Done.' then send new."""
        from aipass.hooks.apps.handlers.notification.telegram_response import _deliver_chunks

        with (
            patch(LOGGER_PATCH),
            patch(f"{MOD}.edit_telegram_message", return_value=True) as mock_edit,
            patch(f"{MOD}._send_with_retry", return_value=True) as mock_send,
        ):
            result = _deliver_chunks(["Hello"], "tok", 123, 789, True)

        assert result is True
        mock_edit.assert_called_once_with("tok", 123, 789, "Done.")
        mock_send.assert_called_once()

    def test_multiple_chunks_numbering(self):
        from aipass.hooks.apps.handlers.notification.telegram_response import _deliver_chunks

        sent_texts = []

        def capture_send(bot_token, chat_id, text):
            sent_texts.append(text)
            return True

        with patch(LOGGER_PATCH), patch(f"{MOD}._send_with_retry", side_effect=capture_send):
            result = _deliver_chunks(["Part A", "Part B", "Part C"], "tok", 123, None, False)

        assert result is True
        assert "[1/3]" in sent_texts[0]
        assert "[2/3]" in sent_texts[1]
        assert "[3/3]" in sent_texts[2]
