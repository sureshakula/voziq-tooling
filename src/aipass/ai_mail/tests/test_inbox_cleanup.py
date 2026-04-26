# =================== AIPass ====================
# Name: test_inbox_cleanup.py
# Description: Tests for inbox cleanup handler
# Version: 1.0.0
# Created: 2026-04-25
# Modified: 2026-04-25
# =============================================

"""Tests for inbox cleanup handler -- mark_all_read, mark_as_opened, mark_as_closed."""

import json
from contextlib import contextmanager

import pytest
from pathlib import Path
from unittest.mock import MagicMock

import aipass.ai_mail.apps.handlers.email.inbox_cleanup as mod


# ---- Fixtures ------------------------------------------------


@contextmanager
def _noop_lock(_path: Path):
    """Dummy context manager replacing the real inbox file lock."""
    yield


@pytest.fixture(autouse=True)
def _silence_json_handler(monkeypatch):
    """Prevent log_operation from writing real JSON files during tests."""
    mock_jh = MagicMock()
    mock_jh.log_operation.return_value = True
    monkeypatch.setattr(mod, "json_handler", mock_jh)
    return mock_jh


@pytest.fixture(autouse=True)
def _mock_inbox_lock(monkeypatch):
    """Replace _get_inbox_lock so it returns a no-op context manager."""
    monkeypatch.setattr(mod, "_get_inbox_lock", lambda: _noop_lock)


@pytest.fixture(autouse=True)
def _mock_dashboard(monkeypatch):
    """Replace _get_push_dashboard_update with a no-op."""
    monkeypatch.setattr(mod, "_get_push_dashboard_update", lambda: lambda _bp: None)


@pytest.fixture(autouse=True)
def _mock_central(monkeypatch):
    """Replace _get_update_central with a no-op."""
    monkeypatch.setattr(mod, "_get_update_central", lambda: lambda: None)


@pytest.fixture(autouse=True)
def _mock_deleted_purge(monkeypatch):
    """Replace _trigger_deleted_purge with a no-op."""
    monkeypatch.setattr(mod, "_trigger_deleted_purge", lambda _bp: None)


def _make_inbox(branch_path: Path, messages: list) -> Path:
    """Create a branch with .ai_mail.local/inbox.json containing messages."""
    mailbox = branch_path / ".ai_mail.local"
    mailbox.mkdir(parents=True, exist_ok=True)
    inbox_file = mailbox / "inbox.json"
    unread = sum(
        1 for m in messages if m.get("status") == "new" or (m.get("status") is None and not m.get("read", False))
    )
    data = {
        "mailbox": "inbox",
        "total_messages": len(messages),
        "unread_count": unread,
        "messages": messages,
    }
    inbox_file.write_text(json.dumps(data), encoding="utf-8")
    return inbox_file


# ---- mark_all_read_and_archive tests ---------------------------


def test_mark_all_read_and_archive_success(tmp_path: Path):
    """Archives all messages and clears inbox."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [
            {"id": "m1", "status": "new", "subject": "First", "read": False},
            {"id": "m2", "status": "opened", "subject": "Second", "read": True},
        ],
    )

    success, message, count = mod.mark_all_read_and_archive(branch_path)

    assert success is True
    assert count == 2
    assert "Archived 2" in message

    # Inbox should be empty
    inbox_file = branch_path / ".ai_mail.local" / "inbox.json"
    with open(inbox_file, "r", encoding="utf-8") as f:
        inbox_data = json.load(f)
    assert inbox_data["messages"] == []
    assert inbox_data["total_messages"] == 0
    assert inbox_data["unread_count"] == 0

    # Deleted folder should have files
    deleted_dir = branch_path / ".ai_mail.local" / "deleted"
    assert deleted_dir.is_dir()
    deleted_files = list(deleted_dir.glob("*.json"))
    assert len(deleted_files) == 2


def test_mark_all_read_and_archive_empty_inbox(tmp_path: Path):
    """Empty inbox returns success with count 0."""
    branch_path = tmp_path / "branch"
    _make_inbox(branch_path, [])

    success, message, count = mod.mark_all_read_and_archive(branch_path)

    assert success is True
    assert count == 0
    assert "empty" in message.lower()


def test_mark_all_read_and_archive_no_inbox(tmp_path: Path):
    """Missing inbox file returns failure."""
    branch_path = tmp_path / "branch"
    branch_path.mkdir(parents=True)

    success, message, count = mod.mark_all_read_and_archive(branch_path)

    assert success is False
    assert count == 0
    assert "not found" in message.lower()


# ---- mark_as_opened tests -------------------------------------


def test_mark_as_opened_success(tmp_path: Path):
    """Marks a message as opened and sets read=True."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [
            {"id": "m1", "status": "new", "subject": "Hello", "read": False},
        ],
    )

    success, message, email_data = mod.mark_as_opened(branch_path, "m1")

    assert success is True
    assert "opened" in message.lower()
    assert email_data is not None
    assert email_data["status"] == "opened"
    assert email_data["read"] is True

    # Verify inbox file updated
    inbox_file = branch_path / ".ai_mail.local" / "inbox.json"
    with open(inbox_file, "r", encoding="utf-8") as f:
        inbox_data = json.load(f)
    assert inbox_data["messages"][0]["status"] == "opened"
    assert inbox_data["unread_count"] == 0


def test_mark_as_opened_not_found(tmp_path: Path):
    """Nonexistent message ID returns failure."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [{"id": "m1", "status": "new", "subject": "Hello"}],
    )

    success, message, email_data = mod.mark_as_opened(branch_path, "nonexistent")

    assert success is False
    assert "not found" in message.lower()
    assert email_data is None


def test_mark_as_opened_no_inbox(tmp_path: Path):
    """Missing inbox file returns failure."""
    branch_path = tmp_path / "branch"
    branch_path.mkdir(parents=True)

    success, message, email_data = mod.mark_as_opened(branch_path, "m1")

    assert success is False
    assert "not found" in message.lower()
    assert email_data is None


def test_mark_as_opened_updates_unread_count(tmp_path: Path):
    """Opening one of two new messages reduces unread_count by 1."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [
            {"id": "m1", "status": "new", "subject": "A", "read": False},
            {"id": "m2", "status": "new", "subject": "B", "read": False},
        ],
    )

    mod.mark_as_opened(branch_path, "m1")

    inbox_file = branch_path / ".ai_mail.local" / "inbox.json"
    with open(inbox_file, "r", encoding="utf-8") as f:
        inbox_data = json.load(f)
    assert inbox_data["unread_count"] == 1


# ---- mark_as_closed_and_archive tests --------------------------


def test_mark_as_closed_and_archive_success(tmp_path: Path):
    """Closes message, removes from inbox, saves to deleted/."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [
            {"id": "m1", "status": "opened", "subject": "Task", "read": True},
            {"id": "m2", "status": "new", "subject": "Other", "read": False},
        ],
    )

    success, message = mod.mark_as_closed_and_archive(branch_path, "m1")

    assert success is True
    assert "closed" in message.lower()

    # Inbox should have only m2
    inbox_file = branch_path / ".ai_mail.local" / "inbox.json"
    with open(inbox_file, "r", encoding="utf-8") as f:
        inbox_data = json.load(f)
    assert len(inbox_data["messages"]) == 1
    assert inbox_data["messages"][0]["id"] == "m2"
    assert inbox_data["total_messages"] == 1

    # Deleted folder should have the archived message
    deleted_dir = branch_path / ".ai_mail.local" / "deleted"
    assert deleted_dir.is_dir()
    deleted_files = list(deleted_dir.glob("*.json"))
    assert len(deleted_files) == 1


def test_mark_as_closed_and_archive_not_found(tmp_path: Path):
    """Nonexistent message ID returns failure."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [{"id": "m1", "status": "new", "subject": "Hello"}],
    )

    success, message = mod.mark_as_closed_and_archive(branch_path, "nonexistent")

    assert success is False
    assert "not found" in message.lower()


def test_mark_as_closed_and_archive_no_inbox(tmp_path: Path):
    """Missing inbox file returns failure."""
    branch_path = tmp_path / "branch"
    branch_path.mkdir(parents=True)

    success, message = mod.mark_as_closed_and_archive(branch_path, "m1")

    assert success is False
    assert "not found" in message.lower()


def test_mark_as_closed_and_archive_skip_post_ops(tmp_path: Path):
    """With skip_post_ops=True, message is still archived but post-ops skipped."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [{"id": "m1", "status": "opened", "subject": "Task", "read": True}],
    )

    success, message = mod.mark_as_closed_and_archive(branch_path, "m1", skip_post_ops=True)

    assert success is True

    # Inbox should be empty
    inbox_file = branch_path / ".ai_mail.local" / "inbox.json"
    with open(inbox_file, "r", encoding="utf-8") as f:
        inbox_data = json.load(f)
    assert len(inbox_data["messages"]) == 0

    # Deleted folder should still have the archived file
    deleted_dir = branch_path / ".ai_mail.local" / "deleted"
    deleted_files = list(deleted_dir.glob("*.json"))
    assert len(deleted_files) == 1


def test_mark_as_closed_and_archive_updates_counts(tmp_path: Path):
    """Closing a message updates total_messages and unread_count."""
    branch_path = tmp_path / "branch"
    _make_inbox(
        branch_path,
        [
            {"id": "m1", "status": "new", "subject": "A", "read": False},
            {"id": "m2", "status": "new", "subject": "B", "read": False},
        ],
    )

    mod.mark_as_closed_and_archive(branch_path, "m1")

    inbox_file = branch_path / ".ai_mail.local" / "inbox.json"
    with open(inbox_file, "r", encoding="utf-8") as f:
        inbox_data = json.load(f)
    assert inbox_data["total_messages"] == 1
    assert inbox_data["unread_count"] == 1
