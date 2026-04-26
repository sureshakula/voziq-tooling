# =================== AIPass ====================
# Name: test_email_module.py
# Description: Tests for email.py and email_send.py orchestrator functions
# Version: 1.0.0
# Created: 2026-04-25
# Modified: 2026-04-25
# =============================================

"""Tests for email.py and email_send.py orchestrator functions.

Covers: handle_inbox, handle_view, handle_close, handle_reply,
handle_sent, handle_contacts, handle_register (email.py),
and handle_send (email_send.py).

All handler dependencies are mocked -- these tests verify orchestration
logic, not business logic.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Autouse fixture: suppress json_handler.log_operation across both modules
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _silence_json_handler():
    """Prevent log_operation from writing real JSON files during tests."""
    with (
        patch("aipass.ai_mail.apps.modules.email.json_handler") as mock_email_jh,
        patch("aipass.ai_mail.apps.modules.email_send.json_handler") as mock_send_jh,
    ):
        mock_email_jh.log_operation.return_value = True
        mock_send_jh.log_operation.return_value = True
        yield


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _write_inbox(tmp_path: Path, messages: list | None = None) -> Path:
    """Create a minimal .ai_mail.local/inbox.json under tmp_path."""
    mailbox = tmp_path / ".ai_mail.local"
    mailbox.mkdir(parents=True, exist_ok=True)
    inbox_file = mailbox / "inbox.json"
    data = {"messages": messages or []}
    inbox_file.write_text(json.dumps(data), encoding="utf-8")
    return inbox_file


# ===========================================================================
# handle_inbox
# ===========================================================================


class TestHandleInbox:
    """Tests for email.handle_inbox orchestrator."""

    def test_inbox_empty_messages(self, tmp_path, monkeypatch):
        """Empty inbox prints 'is empty' message."""
        _write_inbox(tmp_path, messages=[])

        printed: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.resolve_inbox_target",
            lambda first_arg, repo_root, get_branch_fn, get_user_fn: (
                True,
                {
                    "inbox_file": tmp_path / ".ai_mail.local" / "inbox.json",
                    "display_name": "TEST",
                    "target_branch": None,
                    "error": None,
                },
            ),
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.load_inbox",
            lambda f: {"messages": []},
        )
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_inbox

        result = handle_inbox([])
        assert result is True
        assert any("empty" in p.lower() for p in printed)

    def test_inbox_with_messages(self, tmp_path, monkeypatch):
        """Inbox with messages formats and displays them."""
        messages = [
            {"id": "m1", "status": "new", "subject": "Hello"},
            {"id": "m2", "status": "opened", "subject": "World"},
        ]
        _write_inbox(tmp_path, messages=messages)

        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.resolve_inbox_target",
            lambda first_arg, repo_root, get_branch_fn, get_user_fn: (
                True,
                {
                    "inbox_file": tmp_path / ".ai_mail.local" / "inbox.json",
                    "display_name": "TEST",
                    "target_branch": None,
                    "error": None,
                },
            ),
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.load_inbox",
            lambda f: {"messages": messages},
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.format_email_list_item",
            lambda i, msg, show_unread=True: f"[{i}] {msg['subject']}",
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_inbox

        result = handle_inbox([])
        assert result is True
        assert any("Inbox" in p for p in printed)
        assert any("[1]" in p for p in printed)

    def test_inbox_resolve_failure(self, monkeypatch):
        """When resolve_inbox_target fails, handle_inbox returns False."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.resolve_inbox_target",
            lambda first_arg, repo_root, get_branch_fn, get_user_fn: (
                False,
                {"error": "Unknown branch: @fake"},
            ),
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_inbox

        result = handle_inbox(["@fake"])
        assert result is False
        assert any("Unknown" in e for e in errors)


# ===========================================================================
# handle_view
# ===========================================================================


class TestHandleView:
    """Tests for email.handle_view orchestrator."""

    def test_view_no_args_shows_usage(self, monkeypatch):
        """Calling view with no args prints usage error."""
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_view

        result = handle_view([])
        assert result is True
        assert any("Usage" in e for e in errors)

    def test_view_marks_opened_and_prints(self, tmp_path, monkeypatch):
        """View with valid ID marks as opened and prints header + message."""
        email_data = {
            "id": "abc123",
            "from": "@sender",
            "subject": "Test Subject",
            "message": "Test body content",
            "status": "opened",
        }
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.mark_as_opened",
            lambda bp, mid: (True, "Marked as opened", email_data),
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.format_email_header",
            lambda ed: "FROM: @sender | SUBJECT: Test Subject",
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_view

        result = handle_view(["abc123"])
        assert result is True
        assert any("FROM: @sender" in p for p in printed)
        assert any("Test body content" in p for p in printed)

    def test_view_mark_opened_failure(self, tmp_path, monkeypatch):
        """When mark_as_opened fails, error is printed."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.mark_as_opened",
            lambda bp, mid: (False, "Message not found", None),
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_view

        result = handle_view(["missing_id"])
        assert result is True
        assert any("not found" in e.lower() for e in errors)

    def test_view_latest_shortcut(self, tmp_path, monkeypatch):
        """'latest' arg resolves to most recent message ID."""
        inbox_data = {
            "messages": [
                {"id": "old1", "subject": "Old"},
                {"id": "newest", "subject": "Latest"},
            ]
        }
        email_data = {"id": "newest", "subject": "Latest", "message": "Latest body", "from": "@x"}

        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        _write_inbox(tmp_path, messages=inbox_data["messages"])
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.load_inbox",
            lambda f: inbox_data,
        )

        opened_ids: list[str] = []

        def _mock_mark_opened(bp, mid):
            """Track which message IDs were passed to mark_as_opened."""
            opened_ids.append(mid)
            return (True, "Opened", email_data)

        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.mark_as_opened",
            _mock_mark_opened,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.format_email_header",
            lambda ed: "HEADER",
        )
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_view

        result = handle_view(["latest"])
        assert result is True
        assert opened_ids == ["newest"]


# ===========================================================================
# handle_close
# ===========================================================================


class TestHandleClose:
    """Tests for email.handle_close orchestrator."""

    def test_close_no_args_shows_usage(self, monkeypatch):
        """Close with no args prints usage error."""
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_close

        result = handle_close([])
        assert result is True
        assert any("Usage" in e for e in errors)

    def test_close_single_id(self, tmp_path, monkeypatch):
        """Close a single message ID via batch_close."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.batch_close",
            lambda bp, ids, fn: ([("msg1", True, "Closed msg1")], 1, 0),
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.error", lambda msg: None)

        from aipass.ai_mail.apps.modules.email import handle_close

        result = handle_close(["msg1"])
        assert result is True
        assert any("Closed" in p for p in printed)

    def test_close_all(self, tmp_path, monkeypatch):
        """Close 'all' delegates to mark_all_read_and_archive."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.mark_all_read_and_archive",
            lambda bp: (True, "Archived 5 messages", 5),
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_close

        result = handle_close(["all"])
        assert result is True
        assert any("Archived 5" in p for p in printed)

    def test_close_all_failure(self, tmp_path, monkeypatch):
        """Close 'all' failure shows error."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.mark_all_read_and_archive",
            lambda bp: (False, "Nothing to close", 0),
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_close

        result = handle_close(["all"])
        assert result is True
        assert any("Nothing" in e for e in errors)

    def test_close_multiple_ids_triggers_post_ops(self, tmp_path, monkeypatch):
        """Batch close of 2+ IDs triggers batch_close_post_ops."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.batch_close",
            lambda bp, ids, fn: (
                [("m1", True, "Closed m1"), ("m2", True, "Closed m2")],
                2,
                0,
            ),
        )
        post_ops_called = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.batch_close_post_ops",
            lambda bp, push_fn, central_fn, purge_fn: post_ops_called.append(True),
        )
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.error", lambda msg: None)

        from aipass.ai_mail.apps.modules.email import handle_close

        result = handle_close(["m1", "m2"])
        assert result is True
        assert len(post_ops_called) == 1


# ===========================================================================
# handle_reply
# ===========================================================================


class TestHandleReply:
    """Tests for email.handle_reply orchestrator."""

    def test_reply_too_few_args(self, monkeypatch):
        """Reply with < 2 args prints usage error."""
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_reply

        result = handle_reply(["only_id"])
        assert result is True
        assert any("Usage" in e for e in errors)

    def test_reply_message_not_found(self, tmp_path, monkeypatch):
        """Reply to nonexistent message shows error."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.get_email_by_id",
            lambda inbox_file, msg_id: None,
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )
        _write_inbox(tmp_path)

        from aipass.ai_mail.apps.modules.email import handle_reply

        result = handle_reply(["missing_id", "my reply"])
        assert result is True
        assert any("not found" in e.lower() for e in errors)

    def test_reply_success(self, tmp_path, monkeypatch):
        """Successful reply prints success message."""
        original = {"id": "msg1", "from": "@sender", "subject": "Re: test"}
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.get_email_by_id",
            lambda inbox_file, msg_id: original,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.send_reply",
            lambda bp, orig, msg: (True, "Reply sent to @sender", "reply_001"),
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)
        _write_inbox(tmp_path)

        from aipass.ai_mail.apps.modules.email import handle_reply

        result = handle_reply(["msg1", "Thanks!"])
        assert result is True
        assert any("Reply sent" in p for p in printed)

    def test_reply_send_failure(self, tmp_path, monkeypatch):
        """Failed reply shows error message."""
        original = {"id": "msg1", "from": "@sender", "subject": "test"}
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.get_email_by_id",
            lambda inbox_file, msg_id: original,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.send_reply",
            lambda bp, orig, msg: (False, "Delivery failed", None),
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )
        _write_inbox(tmp_path)

        from aipass.ai_mail.apps.modules.email import handle_reply

        result = handle_reply(["msg1", "reply text"])
        assert result is True
        assert any("Delivery failed" in e for e in errors)


# ===========================================================================
# handle_sent
# ===========================================================================


class TestHandleSent:
    """Tests for email.handle_sent orchestrator."""

    def test_sent_no_folder(self, tmp_path, monkeypatch):
        """No sent folder prints 'No sent messages'."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_sent

        result = handle_sent([])
        assert result is True
        assert any("No sent" in p for p in printed)

    def test_sent_with_files(self, tmp_path, monkeypatch):
        """Sent folder with files loads and displays them."""
        sent_folder = tmp_path / ".ai_mail.local" / "sent"
        sent_folder.mkdir(parents=True)
        email_data = {"id": "s1", "to": "@target", "subject": "Sent test"}
        (sent_folder / "email_001.json").write_text(json.dumps(email_data), encoding="utf-8")

        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.load_email_file",
            lambda f: email_data,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.format_email_list_item",
            lambda i, data, show_unread=True: f"[{i}] {data['subject']}",
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_sent

        result = handle_sent([])
        assert result is True
        assert any("Sent Messages" in p for p in printed)
        assert any("[1]" in p for p in printed)

    def test_sent_empty_folder(self, tmp_path, monkeypatch):
        """Sent folder exists but has no JSON files."""
        sent_folder = tmp_path / ".ai_mail.local" / "sent"
        sent_folder.mkdir(parents=True)

        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email._resolve_branch_path",
            lambda: tmp_path,
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_sent

        result = handle_sent([])
        assert result is True
        assert any("No sent" in p for p in printed)


# ===========================================================================
# handle_contacts
# ===========================================================================


class TestHandleContacts:
    """Tests for email.handle_contacts orchestrator."""

    def test_contacts_displays_branches(self, monkeypatch):
        """Contacts lists all registered branches."""
        branches = [
            {"email": "@alpha", "name": "ALPHA", "path": "/src/alpha"},
            {"email": "@beta", "name": "BETA", "path": "/src/beta"},
        ]
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.get_all_branches",
            lambda: branches,
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_contacts

        result = handle_contacts([])
        assert result is True
        assert any("2 branches" in p for p in printed)
        # Branches should appear sorted by email
        alpha_lines = [p for p in printed if "@alpha" in p]
        assert len(alpha_lines) > 0

    def test_contacts_empty(self, monkeypatch):
        """No contacts found prints error."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.get_all_branches",
            lambda: [],
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_contacts

        result = handle_contacts([])
        assert result is True
        assert any("No contacts" in e for e in errors)

    def test_contacts_exception_handled(self, monkeypatch):
        """Exception in get_all_branches is caught and error is shown."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.get_all_branches",
            lambda: (_ for _ in ()).throw(RuntimeError("Registry unavailable")),
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_contacts

        result = handle_contacts([])
        assert result is True
        assert any("Registry unavailable" in e for e in errors)


# ===========================================================================
# handle_register
# ===========================================================================


class TestHandleRegister:
    """Tests for email.handle_register orchestrator."""

    def test_register_too_few_args(self, monkeypatch):
        """Register with < 2 args prints usage error."""
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )

        from aipass.ai_mail.apps.modules.email import handle_register

        result = handle_register(["@branch"])
        assert result is True
        assert any("Usage" in e for e in errors)

    def test_register_success(self, monkeypatch):
        """Successful registration prints green confirmation."""
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        # register_contact is imported locally inside handle_register,
        # so patch at the handler source module
        with patch(
            "aipass.ai_mail.apps.handlers.email.contacts.register_contact",
            return_value=True,
        ):
            from aipass.ai_mail.apps.modules.email import handle_register

            result = handle_register(["@devpulse", "/path/to/inbox"])
        assert result is True
        assert any("Registered" in p and "devpulse" in p for p in printed)

    def test_register_failure(self, monkeypatch):
        """Failed registration prints error."""
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email.error",
            lambda msg: errors.append(msg),
        )
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        with patch(
            "aipass.ai_mail.apps.handlers.email.contacts.register_contact",
            return_value=False,
        ):
            from aipass.ai_mail.apps.modules.email import handle_register

            result = handle_register(["@badstuff", "/path/to/inbox"])
        assert result is True
        assert any("Failed" in e for e in errors)

    def test_register_with_project_arg(self, monkeypatch):
        """Third arg is passed as project name."""
        registered_args: list[tuple] = []

        def _mock_register(name, project, path):
            """Capture register_contact arguments for assertion."""
            registered_args.append((name, project, path))
            return True

        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        with patch(
            "aipass.ai_mail.apps.handlers.email.contacts.register_contact",
            side_effect=_mock_register,
        ):
            from aipass.ai_mail.apps.modules.email import handle_register

            result = handle_register(["@vera", "/path/to/inbox", "VeraStudio"])
        assert result is True
        assert registered_args[0] == ("vera", "VeraStudio", "/path/to/inbox")


# ===========================================================================
# handle_send (from email_send.py)
# ===========================================================================


class TestHandleSend:
    """Tests for email_send.handle_send orchestrator."""

    def test_send_direct_single_recipient(self, monkeypatch):
        """Direct send to a single recipient calls send_to_single."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.parse_send_args",
            lambda args: {
                "mode": "direct",
                "recipients": ["@target"],
                "subject": "Hello",
                "message": "World",
                "auto_execute": False,
                "reply_to": None,
                "no_memory_save": False,
                "from_branch": None,
            },
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_dispatch_target",
            lambda branch, auto, fn: None,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_sender_info",
            lambda fb, rr, amd, gbe, gcu: {
                "email_address": "@ai_mail",
                "display_name": "AI_MAIL",
                "mailbox_path": "/tmp/mailbox",
            },
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.send_to_single",
            lambda *a, **kw: (True, None),
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.console", mock_console)
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.error", lambda msg: None)

        from aipass.ai_mail.apps.modules.email_send import handle_send

        result = handle_send(["@target", "Hello", "World"])
        assert result is True
        assert any("sent" in p.lower() and "@target" in p for p in printed)

    def test_send_error_mode(self, monkeypatch):
        """Parse error returns False and prints error."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.parse_send_args",
            lambda args: {
                "mode": "error",
                "error": "Usage: send @recipient [subject] [message]",
            },
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.error",
            lambda msg: errors.append(msg),
        )
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.console", mock_console)

        from aipass.ai_mail.apps.modules.email_send import handle_send

        result = handle_send(["bad", "args"])
        assert result is False
        assert any("Usage" in e for e in errors)

    def test_send_delivery_failure(self, monkeypatch):
        """When send_to_single returns failure, error is printed."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.parse_send_args",
            lambda args: {
                "mode": "direct",
                "recipients": ["@target"],
                "subject": "Sub",
                "message": "Msg",
                "auto_execute": False,
                "reply_to": None,
                "no_memory_save": False,
                "from_branch": None,
            },
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_dispatch_target",
            lambda branch, auto, fn: None,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_sender_info",
            lambda fb, rr, amd, gbe, gcu: {
                "email_address": "@ai_mail",
                "display_name": "AI_MAIL",
                "mailbox_path": "/tmp/mailbox",
            },
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.send_to_single",
            lambda *a, **kw: (False, "Branch not found"),
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.dispatch_send_error",
            lambda *a, **kw: None,
        )
        errors: list[str] = []
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.error",
            lambda msg: errors.append(msg),
        )
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.console", mock_console)

        from aipass.ai_mail.apps.modules.email_send import handle_send

        result = handle_send(["@target", "Sub", "Msg"])
        assert result is False
        assert any("Branch not found" in e for e in errors)

    def test_send_interactive_mode(self, monkeypatch):
        """Interactive mode is triggered when parse returns mode='interactive'."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.parse_send_args",
            lambda args: {"mode": "interactive"},
        )
        # _send_interactive calls get_all_branches and collect_interactive_input
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.get_all_branches",
            lambda: [{"name": "A", "email": "@a"}],
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.collect_interactive_input",
            lambda branches: None,  # User cancelled
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.console", mock_console)

        from aipass.ai_mail.apps.modules.email_send import handle_send

        result = handle_send([])
        assert result is False
        assert any("Cancelled" in p for p in printed)

    def test_send_dispatch_fires_trigger(self, monkeypatch):
        """With auto_execute, dispatch trigger is fired after successful send."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.parse_send_args",
            lambda args: {
                "mode": "direct",
                "recipients": ["@target"],
                "subject": "Dispatch Task",
                "message": "Do the thing",
                "auto_execute": True,
                "reply_to": None,
                "no_memory_save": False,
                "from_branch": None,
            },
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_dispatch_target",
            lambda branch, auto, fn: "@target",
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_sender_info",
            lambda fb, rr, amd, gbe, gcu: {
                "email_address": "@ai_mail",
                "display_name": "AI_MAIL",
                "mailbox_path": "/tmp/mailbox",
            },
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.prepend_dispatch_header",
            lambda msg, no_memory_save=False: f"[DISPATCH] {msg}",
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.send_to_single",
            lambda *a, **kw: (True, None),
        )

        trigger_calls: list[tuple] = []
        mock_trigger = MagicMock()
        mock_trigger.fire = lambda event, **kw: trigger_calls.append((event, kw))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.trigger", mock_trigger)

        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: None
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.console", mock_console)
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.error", lambda msg: None)

        from aipass.ai_mail.apps.modules.email_send import handle_send

        result = handle_send(["@target", "Dispatch Task", "Do the thing", "--dispatch"])
        assert result is True
        assert len(trigger_calls) == 1
        assert trigger_calls[0][0] == "email_dispatched"
        assert trigger_calls[0][1]["to"] == "@target"

    def test_send_group_multiple_recipients(self, monkeypatch):
        """Group send to multiple recipients calls _send_direct for each."""
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.parse_send_args",
            lambda args: {
                "mode": "direct",
                "recipients": ["@alpha", "@beta"],
                "subject": "Group msg",
                "message": "Hi all",
                "auto_execute": False,
                "reply_to": None,
                "no_memory_save": False,
                "from_branch": None,
            },
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_dispatch_target",
            lambda branch, auto, fn: None,
        )
        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.resolve_sender_info",
            lambda fb, rr, amd, gbe, gcu: {
                "email_address": "@ai_mail",
                "display_name": "AI_MAIL",
                "mailbox_path": "/tmp/mailbox",
            },
        )

        sent_to: list[str] = []

        def mock_send_single(*args, **kwargs):
            """Track which branches receive send_to_single calls."""
            sent_to.append(args[0])
            return (True, None)

        monkeypatch.setattr(
            "aipass.ai_mail.apps.modules.email_send.send_to_single",
            mock_send_single,
        )
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.console", mock_console)
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email_send.error", lambda msg: None)

        from aipass.ai_mail.apps.modules.email_send import handle_send

        result = handle_send(["@alpha", "@beta", "Group msg", "Hi all"])
        assert result is True
        # Both recipients should have been sent to
        assert "@alpha" in sent_to
        assert "@beta" in sent_to
        assert any("Group send complete" in p for p in printed)


# ===========================================================================
# handle_command dispatch table
# ===========================================================================


class TestHandleCommand:
    """Tests for the top-level handle_command router."""

    def test_unknown_command_returns_false(self):
        """Unknown command returns False."""
        from aipass.ai_mail.apps.modules.email import handle_command

        result = handle_command("nonexistent", [])
        assert result is False

    def test_help_flag_prints_help(self, monkeypatch):
        """--help prints help text and returns True."""
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_command

        result = handle_command("--help", [])
        assert result is True
        assert any("Email Module" in p for p in printed)

    def test_command_with_help_arg(self, monkeypatch):
        """Any valid command with 'help' as first arg prints help."""
        printed: list[str] = []
        mock_console = MagicMock()
        mock_console.print = lambda msg, **kw: printed.append(str(msg))
        monkeypatch.setattr("aipass.ai_mail.apps.modules.email.console", mock_console)

        from aipass.ai_mail.apps.modules.email import handle_command

        result = handle_command("inbox", ["help"])
        assert result is True
        assert any("Email Module" in p for p in printed)
