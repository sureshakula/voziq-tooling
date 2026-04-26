# =================== AIPass ====================
# Name: test_plan_file_handler.py
# Description: Tests for plan_file event handlers (created, deleted, moved)
# Version: 1.0.0
# Created: 2026-04-25
# Modified: 2026-04-25
# =============================================

"""Tests for plan_file event handlers."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path


@pytest.fixture(autouse=True)
def _mock_infrastructure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mock heavy infrastructure imports before importing the handler module."""
    import sys

    from aipass.trigger.apps.config import atomic_write_json

    mock_config = MagicMock()
    mock_config.TRIGGER_ROOT = tmp_path
    mock_config.AIPASS_PKG_ROOT = tmp_path / "aipass"
    mock_config.atomic_write_json = atomic_write_json
    monkeypatch.setitem(sys.modules, "aipass.trigger.apps.config", mock_config)

    mock_json_handler = MagicMock()
    mock_json_handler.log_operation = MagicMock(return_value=True)
    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler
    monkeypatch.setitem(sys.modules, "aipass.trigger.apps.handlers.json", json_pkg)
    monkeypatch.setitem(
        sys.modules,
        "aipass.trigger.apps.handlers.json.json_handler",
        mock_json_handler,
    )

    monkeypatch.delitem(
        sys.modules,
        "aipass.trigger.apps.handlers.events.plan_file",
        raising=False,
    )


def _import_plan_file():
    """Import fresh after mocking."""
    import aipass.trigger.apps.handlers.events.plan_file as m

    return m


class TestHandlePlanFileCreated:
    """Tests for handle_plan_file_created."""

    def test_new_plan_added_to_registry(self, tmp_path: Path) -> None:
        """New FPLAN file adds entry with status open."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(return_value={"plans": {}, "next_number": 1})
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_created(path=plan_path)

        mod._save_registry.assert_called_once()  # type: ignore[union-attr]
        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        assert "0042" in saved["plans"]
        plan = saved["plans"]["0042"]
        assert plan["status"] == "open"
        assert plan["file_path"] == plan_path
        assert plan["subject"] == "Auto-detected PLAN"

    def test_existing_open_plan_is_noop(self, tmp_path: Path) -> None:
        """Existing open plan causes early return without saving."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(
            return_value={
                "plans": {"0042": {"status": "open", "file_path": "/old/FPLAN-0042.md"}},
                "next_number": 43,
            }
        )
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_created(path=plan_path)

        mod._save_registry.assert_not_called()  # type: ignore[union-attr]

    def test_existing_closed_plan_updates_location(self, tmp_path: Path) -> None:
        """Closed plan gets location fields updated, status preserved."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(
            return_value={
                "plans": {
                    "0042": {
                        "status": "closed",
                        "file_path": "/old/FPLAN-0042.md",
                        "closed_reason": "completed",
                    }
                },
                "next_number": 43,
            }
        )
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_created(path=plan_path)

        mod._save_registry.assert_called_once()  # type: ignore[union-attr]
        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        plan = saved["plans"]["0042"]
        assert plan["status"] == "closed"
        assert plan["file_path"] == plan_path
        assert plan["closed_reason"] == "completed"
        assert "last_updated" in plan

    def test_updates_next_number_when_needed(self, tmp_path: Path) -> None:
        """Next number advances past the new plan number."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(return_value={"plans": {}, "next_number": 1})
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_created(path=plan_path)

        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        assert saved["next_number"] == 43

    def test_does_not_lower_next_number(self, tmp_path: Path) -> None:
        """Next number stays at 100 when plan 42 is added."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(return_value={"plans": {}, "next_number": 100})
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_created(path=plan_path)

        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        assert saved["next_number"] == 100

    def test_returns_early_for_non_plan_file(self, tmp_path: Path) -> None:
        """Non-FPLAN filenames cause immediate return."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock()
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        non_plan_path = str(tmp_path / "README.md")
        mod.handle_plan_file_created(path=non_plan_path)

        mod._load_registry.assert_not_called()  # type: ignore[union-attr]
        mod._save_registry.assert_not_called()  # type: ignore[union-attr]

    def test_logs_operation_on_success(self, tmp_path: Path) -> None:
        """Calls json_handler.log_operation after adding new plan."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(return_value={"plans": {}, "next_number": 1})
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        plan_path = str(tmp_path / "FPLAN-0001.md")
        mod.handle_plan_file_created(path=plan_path)

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "plan_event", {"success": True}
        )


class TestHandlePlanFileDeleted:
    """Tests for handle_plan_file_deleted."""

    def test_open_plan_removed_from_registry(self, tmp_path: Path) -> None:
        """Open plan is deleted entirely from the plans dict."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(
            return_value={
                "plans": {"0042": {"status": "open", "file_path": "/some/FPLAN-0042.md"}},
                "next_number": 43,
            }
        )
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_deleted(path=plan_path)

        mod._save_registry.assert_called_once()  # type: ignore[union-attr]
        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        assert "0042" not in saved["plans"]

    def test_closed_plan_marked_archived(self, tmp_path: Path) -> None:
        """Closed plan gets archived flag instead of being removed."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(
            return_value={
                "plans": {
                    "0042": {
                        "status": "closed",
                        "file_path": "/some/FPLAN-0042.md",
                    }
                },
                "next_number": 43,
            }
        )
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_deleted(path=plan_path)

        mod._save_registry.assert_called_once()  # type: ignore[union-attr]
        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        assert saved["plans"]["0042"]["archived"] is True
        assert "archived_date" in saved["plans"]["0042"]

    def test_processed_plan_marked_archived(self, tmp_path: Path) -> None:
        """Plan with processed=True gets archived flag."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(
            return_value={
                "plans": {
                    "0042": {
                        "status": "open",
                        "processed": True,
                        "file_path": "/some/FPLAN-0042.md",
                    }
                },
                "next_number": 43,
            }
        )
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_deleted(path=plan_path)

        mod._save_registry.assert_called_once()  # type: ignore[union-attr]
        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        assert saved["plans"]["0042"]["archived"] is True

    def test_unknown_plan_no_crash(self, tmp_path: Path) -> None:
        """Plan not in registry causes no error."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(return_value={"plans": {}, "next_number": 1})
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        plan_path = str(tmp_path / "FPLAN-9999.md")
        mod.handle_plan_file_deleted(path=plan_path)

        mod._save_registry.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_for_non_plan_file(self, tmp_path: Path) -> None:
        """Non-FPLAN filenames cause immediate return."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock()
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        mod.handle_plan_file_deleted(path=str(tmp_path / "random-notes.txt"))

        mod._load_registry.assert_not_called()  # type: ignore[union-attr]


class TestHandlePlanFileMoved:
    """Tests for handle_plan_file_moved."""

    def test_updates_location_fields(self, tmp_path: Path) -> None:
        """Move updates location, relative_path, and file_path."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(
            return_value={
                "plans": {
                    "0042": {
                        "status": "open",
                        "location": "/old/dir",
                        "relative_path": "old/dir",
                        "file_path": "/old/dir/FPLAN-0042.md",
                    }
                },
                "next_number": 43,
            }
        )
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        new_dir = tmp_path / "new" / "location"
        new_dir.mkdir(parents=True, exist_ok=True)
        dest_path = str(new_dir / "FPLAN-0042.md")

        mod.handle_plan_file_moved(
            src_path=str(tmp_path / "old" / "FPLAN-0042.md"),
            dest_path=dest_path,
        )

        mod._save_registry.assert_called_once()  # type: ignore[union-attr]
        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        plan = saved["plans"]["0042"]
        assert plan["file_path"] == dest_path
        assert plan["location"] == str(new_dir)
        assert "last_updated" in plan

    def test_preserves_existing_metadata(self, tmp_path: Path) -> None:
        """Move preserves status, closed_reason, memory_created, etc."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(
            return_value={
                "plans": {
                    "0042": {
                        "status": "closed",
                        "closed_reason": "completed",
                        "memory_created": True,
                        "memory_created_date": "2026-01-15",
                        "location": "/old",
                        "relative_path": "old",
                        "file_path": "/old/FPLAN-0042.md",
                    }
                },
                "next_number": 43,
            }
        )
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        dest_path = str(tmp_path / "FPLAN-0042.md")
        mod.handle_plan_file_moved(
            src_path="/old/FPLAN-0042.md",
            dest_path=dest_path,
        )

        saved = mod._save_registry.call_args[0][0]  # type: ignore[union-attr]
        plan = saved["plans"]["0042"]
        assert plan["status"] == "closed"
        assert plan["closed_reason"] == "completed"
        assert plan["memory_created"] is True
        assert plan["memory_created_date"] == "2026-01-15"

    def test_unknown_plan_no_crash(self, tmp_path: Path) -> None:
        """Plan not in registry causes no error on move."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock(return_value={"plans": {}, "next_number": 1})
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        mod.handle_plan_file_moved(
            src_path=str(tmp_path / "FPLAN-9999.md"),
            dest_path=str(tmp_path / "new" / "FPLAN-9999.md"),
        )

        mod._save_registry.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_for_non_plan_dest(self, tmp_path: Path) -> None:
        """Non-FPLAN destination filename causes immediate return."""
        mod = _import_plan_file()
        mod._load_registry = MagicMock()
        mod._save_registry = MagicMock()
        mod.REPO_ROOT = tmp_path

        mod.handle_plan_file_moved(
            src_path=str(tmp_path / "FPLAN-0001.md"),
            dest_path=str(tmp_path / "renamed-notes.txt"),
        )

        mod._load_registry.assert_not_called()  # type: ignore[union-attr]
