"""Tests for email formatting handler -- lookup, preview, header, list item."""

import json

import pytest
from unittest.mock import MagicMock
from pathlib import Path

import aipass.ai_mail.apps.handlers.email.format as mod


# --- Fixtures --------------------------------------------------------


@pytest.fixture(autouse=True)
def _suppress_log_operation(monkeypatch):
    """Prevent json_handler.log_operation from touching real files."""
    mock_jh = MagicMock()
    monkeypatch.setattr(mod, "json_handler", mock_jh)
    return mock_jh


@pytest.fixture()
def registry_file(tmp_path, monkeypatch):
    """Create a temporary AIPASS_REGISTRY.json and patch REGISTRY_PATH."""
    registry_data = {
        "branches": [
            {"name": "TEAM_1", "alias": "Team Alpha"},
            {"name": "VERA", "alias": "Vera"},
            {"name": "NO_ALIAS", "alias": ""},
            {"name": "NULL_ALIAS"},
        ]
    }
    reg_path = tmp_path / "AIPASS_REGISTRY.json"
    reg_path.write_text(json.dumps(registry_data), encoding="utf-8")
    monkeypatch.setattr(mod, "REGISTRY_PATH", reg_path)
    return reg_path


# --- lookup_branch_alias tests ---------------------------------------


def test_lookup_branch_alias_returns_alias(registry_file):
    """Returns alias when branch has a non-empty alias."""
    result = mod.lookup_branch_alias("TEAM_1")
    assert result == "Team Alpha"


def test_lookup_branch_alias_empty_alias_returns_none(registry_file):
    """Returns None when branch has an empty string alias."""
    result = mod.lookup_branch_alias("NO_ALIAS")
    assert result is None


def test_lookup_branch_alias_missing_alias_key_returns_none(registry_file):
    """Returns None when branch dict has no 'alias' key."""
    result = mod.lookup_branch_alias("NULL_ALIAS")
    assert result is None


def test_lookup_branch_alias_unknown_branch_returns_none(registry_file):
    """Returns None for a branch not in the registry."""
    result = mod.lookup_branch_alias("NONEXISTENT")
    assert result is None


def test_lookup_branch_alias_file_missing_returns_none(tmp_path, monkeypatch):
    """Returns None when REGISTRY_PATH points to a non-existent file."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", tmp_path / "missing.json")
    result = mod.lookup_branch_alias("TEAM_1")
    assert result is None


def test_lookup_branch_alias_invalid_json_returns_none(tmp_path, monkeypatch):
    """Returns None when REGISTRY_PATH contains invalid JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not valid json {{{", encoding="utf-8")
    monkeypatch.setattr(mod, "REGISTRY_PATH", bad_file)
    result = mod.lookup_branch_alias("TEAM_1")
    assert result is None


# --- format_sender_display tests -------------------------------------


def test_format_sender_display_with_alias(registry_file):
    """Uses alias when branch has one."""
    result = mod.format_sender_display("TEAM_1", "@team_1")
    assert result == "Team Alpha (@team_1)"


def test_format_sender_display_without_alias(registry_file):
    """Falls back to from_name when branch has no alias."""
    result = mod.format_sender_display("NO_ALIAS", "@no_alias")
    assert result == "NO_ALIAS (@no_alias)"


def test_format_sender_display_unknown_branch(registry_file):
    """Falls back to from_name for unknown branch."""
    result = mod.format_sender_display("UNKNOWN", "@unknown")
    assert result == "UNKNOWN (@unknown)"


# --- format_email_preview tests --------------------------------------


def test_format_email_preview_short_message():
    """Returns full message when under max_length."""
    msg = "Short message"
    result = mod.format_email_preview(msg, max_length=100)
    assert result == msg


def test_format_email_preview_exact_length():
    """Returns full message when exactly at max_length."""
    msg = "x" * 100
    result = mod.format_email_preview(msg, max_length=100)
    assert result == msg
    assert "..." not in result


def test_format_email_preview_truncates_long_message():
    """Truncates and adds ellipsis when over max_length."""
    msg = "a" * 150
    result = mod.format_email_preview(msg, max_length=100)
    assert len(result) == 103  # 100 chars + "..."
    assert result.endswith("...")


def test_format_email_preview_empty_message():
    """Returns empty string for empty message."""
    result = mod.format_email_preview("")
    assert result == ""


def test_format_email_preview_default_max_length():
    """Default max_length is 100."""
    msg = "b" * 101
    result = mod.format_email_preview(msg)
    assert result == "b" * 100 + "..."


# --- format_email_header tests ---------------------------------------


def test_format_email_header_contains_all_fields(monkeypatch):
    """Header includes From, Date, Subject, and separator lines."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    email_data = {
        "from_name": "TEAM_1",
        "from": "@team_1",
        "timestamp": "2026-04-25T10:00:00",
        "subject": "Test Subject",
    }
    result = mod.format_email_header(email_data)
    assert "From: TEAM_1 (@team_1)" in result
    assert "Date: 2026-04-25T10:00:00" in result
    assert "Subject: Test Subject" in result
    assert "=" * 70 in result


def test_format_email_header_missing_fields(monkeypatch):
    """Uses defaults for missing email_data fields."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    result = mod.format_email_header({})
    assert "From: Unknown (unknown)" in result
    assert "Date: Unknown" in result
    assert "Subject: No Subject" in result


def test_format_email_header_logs_operation(
    _suppress_log_operation: MagicMock,
    monkeypatch,
):
    """format_email_header calls json_handler.log_operation."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    email_data: dict[str, str] = {"subject": "Log Test"}
    mod.format_email_header(email_data)
    _suppress_log_operation.log_operation.assert_called_once_with("format_email_header", {"subject": "Log Test"})


def test_format_email_header_with_alias(registry_file):
    """Header uses alias when branch has one in the registry."""
    email_data = {
        "from_name": "VERA",
        "from": "@vera",
        "timestamp": "2026-04-25",
        "subject": "Alias Test",
    }
    result = mod.format_email_header(email_data)
    assert "From: Vera (@vera)" in result


# --- format_email_list_item tests ------------------------------------


def test_format_email_list_item_new_message(monkeypatch):
    """New/unread message shows the new-mail emoji marker."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    email_data = {
        "id": "abc123",
        "from_name": "SENDER",
        "from": "@sender",
        "timestamp": "2026-04-25",
        "subject": "New Mail",
        "message": "Hello world",
        "status": "new",
    }
    result = mod.format_email_list_item(1, email_data)
    assert "\U0001f4e8" in result  # new-mail emoji
    assert "[abc123]" in result
    assert "Subject: New Mail" in result


def test_format_email_list_item_opened_message(monkeypatch):
    """Opened message shows the opened-mailbox emoji marker."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    email_data = {
        "id": "def456",
        "from_name": "SENDER",
        "from": "@sender",
        "timestamp": "2026-04-25",
        "subject": "Read Mail",
        "message": "Already read",
        "status": "opened",
    }
    result = mod.format_email_list_item(1, email_data)
    assert "\U0001f4ec" in result  # opened-mailbox emoji


def test_format_email_list_item_read_fallback(monkeypatch):
    """Falls back to 'read' field when 'status' is absent."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    email_data = {
        "id": "ghi789",
        "from_name": "SENDER",
        "from": "@sender",
        "timestamp": "2026-04-25",
        "subject": "Legacy Mail",
        "message": "Old format",
        "read": True,
    }
    result = mod.format_email_list_item(1, email_data)
    assert "\U0001f4ec" in result  # opened-mailbox emoji (read=True)


def test_format_email_list_item_show_unread_false(monkeypatch):
    """When show_unread=False, shows 'To:' instead of sender with emoji."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    email_data = {
        "id": "jkl012",
        "to": "@recipient",
        "timestamp": "2026-04-25",
        "subject": "Sent Mail",
        "message": "Outgoing message",
    }
    result = mod.format_email_list_item(1, email_data, show_unread=False)
    assert "To: @recipient" in result
    assert "\U0001f4e8" not in result
    assert "\U0001f4ec" not in result


def test_format_email_list_item_missing_fields(monkeypatch):
    """Uses defaults for missing email_data fields."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    result = mod.format_email_list_item(1, {})
    assert "[????????]" in result
    assert "Subject: No Subject" in result


def test_format_email_list_item_truncates_long_message(monkeypatch):
    """Long message is truncated in the preview."""
    monkeypatch.setattr(mod, "REGISTRY_PATH", Path("/nonexistent"))
    email_data = {
        "id": "trunc1",
        "from_name": "SENDER",
        "from": "@sender",
        "timestamp": "2026-04-25",
        "subject": "Long Body",
        "message": "z" * 200,
        "status": "new",
    }
    result = mod.format_email_list_item(1, email_data)
    assert "..." in result
