# =================== AIPass ====================
# Name: test_email.py
# Version: 1.3.0
# Description: Tests for email notification handler
# Branch: hooks
# Created: 2026-05-21
# Modified: 2026-06-09
# =============================================

"""Tests for handlers/notification/email.py."""

import json
from pathlib import Path
from unittest.mock import patch


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

        with patch(
            "aipass.hooks.apps.handlers.notification.email._find_branch_root",
            return_value=tmp_path,
        ):
            result = handle({})

        assert "1 new email" in result["stdout"]
        assert "drone @ai_mail inbox" in result["stdout"]
        assert result["exit_code"] == 0

    def test_handle_sets_sound_when_new_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "new", "subject": "test"}]}),
            encoding="utf-8",
        )

        with patch(
            "aipass.hooks.apps.handlers.notification.email._find_branch_root",
            return_value=tmp_path,
        ):
            result = handle({})

        assert result["sound"] == "email notification: 1 new email"

    def test_handle_no_sound_when_no_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "read"}]}),
            encoding="utf-8",
        )

        with patch(
            "aipass.hooks.apps.handlers.notification.email._find_branch_root",
            return_value=tmp_path,
        ):
            result = handle({})

        assert result.get("sound", "") == ""

    def test_handle_returns_empty_when_no_new_emails(self, tmp_path):
        from aipass.hooks.apps.handlers.notification.email import handle

        inbox_dir = tmp_path / ".ai_mail.local"
        inbox_dir.mkdir()
        inbox_file = inbox_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps({"messages": [{"status": "read", "subject": "old"}]}),
            encoding="utf-8",
        )

        with patch(
            "aipass.hooks.apps.handlers.notification.email._find_branch_root",
            return_value=tmp_path,
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

        with patch(
            "aipass.hooks.apps.handlers.notification.email._find_branch_root",
            return_value=tmp_path,
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
