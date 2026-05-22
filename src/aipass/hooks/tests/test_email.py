# =================== AIPass ====================
# Name: test_email.py
# Version: 1.1.0
# Description: Tests for email notification handler
# Branch: hooks
# Created: 2026-05-21
# Modified: 2026-05-21
# =============================================

"""Tests for handlers/notification/email.py."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestEmailHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.email import handle

        with patch(
            "aipass.hooks.apps.handlers.notification.email._find_branch_root",
            return_value=None,
        ):
            result = handle({})

        assert isinstance(result, dict)
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_handle_returns_notification_when_new_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "new", "subject": "test"}]}),
            encoding="utf-8",
        )

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_branch_root",
                return_value=tmp_path,
            ),
            patch("aipass.hooks.apps.handlers.notification.email._speak"),
        ):
            result = handle({})

        assert "1 new email" in result["stdout"]
        assert "drone @ai_mail inbox" in result["stdout"]
        assert result["exit_code"] == 0

    def test_handle_speaks_when_new_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "new", "subject": "test"}]}),
            encoding="utf-8",
        )

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_branch_root",
                return_value=tmp_path,
            ),
            patch("aipass.hooks.apps.handlers.notification.email._speak") as mock_speak,
        ):
            handle({})

        mock_speak.assert_called_once_with("email notification: 1 new email")

    def test_handle_does_not_speak_when_no_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "read"}]}),
            encoding="utf-8",
        )

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_branch_root",
                return_value=tmp_path,
            ),
            patch("aipass.hooks.apps.handlers.notification.email._speak") as mock_speak,
        ):
            handle({})

        mock_speak.assert_not_called()

    def test_handle_returns_empty_when_no_new_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "read", "subject": "old"}]}),
            encoding="utf-8",
        )

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_branch_root",
                return_value=tmp_path,
            ),
            patch("aipass.hooks.apps.handlers.notification.email._speak"),
        ):
            result = handle({})

        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_handle_plural_for_multiple_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps(
                {
                    "messages": [
                        {"status": "new", "subject": "one"},
                        {"status": "new", "subject": "two"},
                        {"status": "new", "subject": "three"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_branch_root",
                return_value=tmp_path,
            ),
            patch("aipass.hooks.apps.handlers.notification.email._speak"),
        ):
            result = handle({})

        assert "3 new emails" in result["stdout"]


class TestCountNewEmails:
    """Inbox counting logic tests."""

    def test_counts_new_status(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _count_new_emails

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps(
                {
                    "messages": [
                        {"status": "new"},
                        {"status": "new"},
                        {"status": "read"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        assert _count_new_emails(tmp_path) == 2

    def test_counts_unread_without_status(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _count_new_emails

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"subject": "no status field"}]}),
            encoding="utf-8",
        )

        assert _count_new_emails(tmp_path) == 1

    def test_skips_read_messages(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _count_new_emails

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "read"}, {"read": True}]}),
            encoding="utf-8",
        )

        assert _count_new_emails(tmp_path) == 0

    def test_handles_bare_list_format(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _count_new_emails

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps([{"status": "new"}, {"status": "read"}]),
            encoding="utf-8",
        )

        assert _count_new_emails(tmp_path) == 1

    def test_falls_back_to_legacy_path(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _count_new_emails

        inbox_dir = tmp_path / "ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "new"}]}),
            encoding="utf-8",
        )

        assert _count_new_emails(tmp_path) == 1

    def test_returns_zero_when_no_inbox(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _count_new_emails

        assert _count_new_emails(tmp_path) == 0

    def test_returns_zero_on_corrupt_json(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _count_new_emails

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text("not valid json{{{", encoding="utf-8")

        assert _count_new_emails(tmp_path) == 0


class TestFindBranchRoot:
    """Branch root discovery tests."""

    def test_finds_branch_with_trinity(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _find_branch_root

        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        apps = tmp_path / "apps"
        apps.mkdir()

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email.Path.cwd",
                return_value=tmp_path,
            ),
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_repo_root",
                return_value=tmp_path.parent,
            ),
        ):
            result = _find_branch_root()

        assert result == tmp_path

    def test_returns_none_when_no_markers(self):
        from aipass.hooks.apps.handlers.notification.email import _find_branch_root

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email.Path.cwd",
                return_value=Path("/tmp/bare"),
            ),
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_repo_root",
                return_value=None,
            ),
        ):
            result = _find_branch_root()

        assert result is None

    def test_returns_none_at_repo_root(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import _find_branch_root

        with (
            patch(
                "aipass.hooks.apps.handlers.notification.email.Path.cwd",
                return_value=tmp_path,
            ),
            patch(
                "aipass.hooks.apps.handlers.notification.email._find_repo_root",
                return_value=tmp_path,
            ),
        ):
            result = _find_branch_root()

        assert result is None


class TestSpeakFunction:
    """Piper TTS tests."""

    def test_speak_calls_piper_then_aplay(self):
        from aipass.hooks.apps.handlers.notification.email import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.email.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.email.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.email.subprocess") as mock_sub,
            patch("aipass.hooks.apps.handlers.notification.email.tempfile") as mock_tmp,
            patch("aipass.hooks.apps.handlers.notification.email.Path") as mock_path,
        ):
            mock_piper_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file
            mock_sub.run.return_value = MagicMock(returncode=0)
            mock_path.return_value.exists.return_value = True

            _speak("test text")

        mock_sub.run.assert_called_once()
        mock_sub.Popen.assert_called_once()

    def test_speak_skips_when_piper_missing(self):
        from aipass.hooks.apps.handlers.notification.email import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.email.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.email.subprocess") as mock_sub,
        ):
            mock_piper_bin.exists.return_value = False
            _speak("test")

        mock_sub.run.assert_not_called()

    def test_speak_graceful_on_timeout(self):
        import subprocess as real_sub
        from aipass.hooks.apps.handlers.notification.email import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.email.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.email.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.email.subprocess") as mock_sub,
            patch("aipass.hooks.apps.handlers.notification.email.tempfile") as mock_tmp,
        ):
            mock_piper_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file
            mock_sub.run.side_effect = real_sub.TimeoutExpired("piper", 5)
            mock_sub.TimeoutExpired = real_sub.TimeoutExpired

            _speak("test")

    def test_speak_graceful_on_os_error(self):
        from aipass.hooks.apps.handlers.notification.email import _speak

        with (
            patch("aipass.hooks.apps.handlers.notification.email.PIPER_BIN") as mock_piper_bin,
            patch("aipass.hooks.apps.handlers.notification.email.PIPER_VOICE") as mock_voice,
            patch("aipass.hooks.apps.handlers.notification.email.subprocess.run", side_effect=OSError("broken")),
            patch("aipass.hooks.apps.handlers.notification.email.tempfile") as mock_tmp,
        ):
            mock_piper_bin.exists.return_value = True
            mock_voice.exists.return_value = True
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.wav"
            mock_tmp.NamedTemporaryFile.return_value = mock_file

            _speak("test")
