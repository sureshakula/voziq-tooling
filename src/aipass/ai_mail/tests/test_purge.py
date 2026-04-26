"""Tests for sent/deleted auto-purge handler -- purge_sent_folder, purge_deleted_folder, run_purge."""

import json
import os
import pytest
from unittest.mock import patch

import aipass.ai_mail.apps.handlers.email.purge as purge_mod
from aipass.ai_mail.apps.handlers.email.purge import (
    purge_sent_folder,
    purge_deleted_folder,
    run_purge,
)


# ---- Fixtures ------------------------------------------------


@pytest.fixture(autouse=True)
def _silence_json_handler():
    """Prevent log_operation from writing real JSON files during tests."""
    with patch("aipass.ai_mail.apps.handlers.email.purge.json_handler") as mock_jh:
        mock_jh.log_operation.return_value = True
        yield mock_jh


# ---- Helper --------------------------------------------------


def _populate_folder(folder_path, count):
    """Create count JSON files in folder_path with staggered mtimes.

    Files are named email_000.json through email_{count-1}.json.
    Each file gets a slightly different mtime so sorting by mtime is deterministic.
    """
    folder_path.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        email_file = folder_path / f"email_{i:03d}.json"
        email_data = {
            "id": f"msg-{i:03d}",
            "from": "@sender",
            "to": "@recipient",
            "subject": f"Email {i}",
            "message": f"Body {i}",
            "timestamp": f"2026-01-01 12:{i:02d}:00",
        }
        email_file.write_text(json.dumps(email_data), encoding="utf-8")
        # Stagger mtimes so sorting is deterministic (newer files have later mtime)
        base_time = 1700000000.0 + i
        os.utime(str(email_file), (base_time, base_time))


# ---- purge_sent_folder tests ---------------------------------


def test_purge_sent_folder_no_folder(tmp_path):
    """Returns success with 0 purged when sent folder does not exist."""
    result = purge_sent_folder(tmp_path)

    assert result["success"] is True
    assert result["purged_count"] == 0


def test_purge_sent_folder_below_threshold(tmp_path):
    """Returns success with 0 purged when file count is at or below threshold."""
    _populate_folder(tmp_path / "sent", 10)

    result = purge_sent_folder(tmp_path)

    assert result["success"] is True
    assert result["purged_count"] == 0
    assert "Below threshold" in result["message"]


def test_purge_sent_folder_above_threshold_vectorize_success(tmp_path, monkeypatch):
    """Purges oldest files when count exceeds threshold and vectorization succeeds."""
    _populate_folder(tmp_path / "sent", 13)

    monkeypatch.setattr(
        purge_mod, "_vectorize_emails", lambda emails, folder_type: {"success": True, "count": len(emails)}
    )

    result = purge_sent_folder(tmp_path)

    assert result["success"] is True
    assert result["purged_count"] == 3  # 13 - 10 = 3 files purged
    assert result["vectorized"] is True

    # Verify 10 files remain
    remaining = list((tmp_path / "sent").glob("*.json"))
    assert len(remaining) == 10


def test_purge_sent_folder_above_threshold_vectorize_fails(tmp_path, monkeypatch):
    """Preserves all files when vectorization fails."""
    _populate_folder(tmp_path / "sent", 13)

    monkeypatch.setattr(
        purge_mod, "_vectorize_emails", lambda emails, folder_type: {"success": False, "error": "timeout"}
    )

    result = purge_sent_folder(tmp_path)

    assert result["success"] is False
    assert result["purged_count"] == 0
    assert result["vectorized"] is False

    # All 13 files should still exist
    remaining = list((tmp_path / "sent").glob("*.json"))
    assert len(remaining) == 13


# ---- purge_deleted_folder tests ------------------------------


def test_purge_deleted_folder_no_folder(tmp_path):
    """Returns success with 0 purged when deleted folder does not exist."""
    result = purge_deleted_folder(tmp_path)

    assert result["success"] is True
    assert result["purged_count"] == 0


def test_purge_deleted_folder_below_threshold(tmp_path):
    """Returns success with 0 purged when file count is at or below threshold."""
    _populate_folder(tmp_path / "deleted", 5)

    result = purge_deleted_folder(tmp_path)

    assert result["success"] is True
    assert result["purged_count"] == 0


def test_purge_deleted_folder_above_threshold(tmp_path, monkeypatch):
    """Purges oldest files from deleted folder when count exceeds threshold."""
    _populate_folder(tmp_path / "deleted", 15)

    monkeypatch.setattr(
        purge_mod, "_vectorize_emails", lambda emails, folder_type: {"success": True, "count": len(emails)}
    )

    result = purge_deleted_folder(tmp_path)

    assert result["success"] is True
    assert result["purged_count"] == 5  # 15 - 10 = 5 files purged

    remaining = list((tmp_path / "deleted").glob("*.json"))
    assert len(remaining) == 10


# ---- run_purge tests -----------------------------------------


def test_run_purge_both_below_threshold(tmp_path):
    """Both folders below threshold returns success with 0 purged."""
    _populate_folder(tmp_path / "sent", 3)
    _populate_folder(tmp_path / "deleted", 2)

    result = run_purge(tmp_path)

    assert result["success"] is True
    assert result["sent"]["purged_count"] == 0
    assert result["deleted"]["purged_count"] == 0


def test_run_purge_no_folders(tmp_path):
    """No folders at all returns success."""
    result = run_purge(tmp_path)

    assert result["success"] is True
    assert result["sent"]["purged_count"] == 0
    assert result["deleted"]["purged_count"] == 0


def test_run_purge_mixed_results(tmp_path, monkeypatch):
    """Sent over threshold and deleted below returns combined result."""
    _populate_folder(tmp_path / "sent", 12)
    _populate_folder(tmp_path / "deleted", 5)

    monkeypatch.setattr(
        purge_mod, "_vectorize_emails", lambda emails, folder_type: {"success": True, "count": len(emails)}
    )

    result = run_purge(tmp_path)

    assert result["success"] is True
    assert result["sent"]["purged_count"] == 2  # 12 - 10
    assert result["deleted"]["purged_count"] == 0


def test_run_purge_failure_propagates(tmp_path, monkeypatch):
    """Overall success is False when either folder purge fails."""
    _populate_folder(tmp_path / "sent", 15)

    monkeypatch.setattr(
        purge_mod, "_vectorize_emails", lambda emails, folder_type: {"success": False, "error": "broken"}
    )

    result = run_purge(tmp_path)

    assert result["success"] is False
    assert result["sent"]["success"] is False
