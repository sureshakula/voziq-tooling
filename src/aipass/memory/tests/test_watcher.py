# ===================AIPASS====================
# META DATA HEADER
# Name: tests/test_watcher.py
# Date: 2026-04-25
# Version: 1.0.0
# Category: memory/tests
# =============================================

"""Tests for the memory watcher handler.

Covers:
    from aipass.memory.apps.handlers.monitor.memory_watcher import start_memory_watcher
    from aipass.memory.apps.handlers.monitor.memory_watcher import stop_memory_watcher
    from aipass.memory.apps.handlers.monitor.memory_watcher import is_memory_watcher_active
    from aipass.memory.apps.handlers.monitor.memory_watcher import get_watcher_status
    from aipass.memory.apps.handlers.monitor.memory_watcher import MemoryFileWatcher

Tests watcher lifecycle (start/stop/status), the MemoryFileWatcher.on_modified
callback, and edge cases like missing watchdog or already-running observers.
All tests use mocks -- no live filesystem watchers or infrastructure access.
"""

import sys
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers: prepare the mock graph needed to import memory_watcher
# ---------------------------------------------------------------------------


def _prepare_watcher_mocks(monkeypatch):
    """Insert mocks for every module-level import memory_watcher.py touches.

    Returns a dict of key mock objects so tests can assert against them.
    """
    # Mock line_counter
    mock_update_line_count = MagicMock(return_value={"success": True, "lines": 150})
    mock_line_counter = MagicMock()
    mock_line_counter.update_line_count = mock_update_line_count
    monkeypatch.setitem(
        sys.modules,
        "aipass.memory.apps.handlers.tracking.line_counter",
        mock_line_counter,
    )

    # Mock detector
    mock_check_single_file = MagicMock(return_value={"success": True, "should_rollover": False})
    mock_detector = MagicMock()
    mock_detector.check_single_file = mock_check_single_file
    monkeypatch.setitem(
        sys.modules,
        "aipass.memory.apps.handlers.monitor.detector",
        mock_detector,
    )

    # Mock watchdog
    mock_observer_instance = MagicMock()
    mock_observer_instance.is_alive.return_value = True
    mock_observer_cls = MagicMock(return_value=mock_observer_instance)

    mock_watchdog_observers = MagicMock()
    mock_watchdog_observers.Observer = mock_observer_cls

    mock_fse_handler = type("FileSystemEventHandler", (), {"__init__": lambda self: None})

    mock_watchdog_events = MagicMock()
    mock_watchdog_events.FileSystemEventHandler = mock_fse_handler

    monkeypatch.setitem(sys.modules, "watchdog", MagicMock())
    monkeypatch.setitem(sys.modules, "watchdog.observers", mock_watchdog_observers)
    monkeypatch.setitem(sys.modules, "watchdog.events", mock_watchdog_events)

    # Mock rollover orchestrator (lazy import inside on_modified)
    mock_execute_rollover = MagicMock(return_value={"success": True})
    mock_orchestrator = MagicMock()
    mock_orchestrator.execute_rollover = mock_execute_rollover
    monkeypatch.setitem(
        sys.modules,
        "aipass.memory.apps.handlers.rollover",
        MagicMock(),
    )
    monkeypatch.setitem(
        sys.modules,
        "aipass.memory.apps.handlers.rollover.orchestrator",
        mock_orchestrator,
    )

    return {
        "update_line_count": mock_update_line_count,
        "check_single_file": mock_check_single_file,
        "observer_instance": mock_observer_instance,
        "observer_cls": mock_observer_cls,
        "execute_rollover": mock_execute_rollover,
    }


def _import_watcher(monkeypatch):
    """Prepare mocks and import (or reimport) memory_watcher.

    Returns (module, mocks_dict).
    """
    mocks = _prepare_watcher_mocks(monkeypatch)

    # Remove cached module so it gets re-imported with our mocks
    sys.modules.pop("aipass.memory.apps.handlers.monitor.memory_watcher", None)

    # Also clear parent package's cached attribute so Python re-executes
    # the module code with fresh mocks instead of returning a stale ref.
    parent = sys.modules.get("aipass.memory.apps.handlers.monitor")
    if parent is not None and hasattr(parent, "memory_watcher"):
        delattr(parent, "memory_watcher")

    from aipass.memory.apps.handlers.monitor import memory_watcher  # noqa: E402

    # Reset the global _observer to None for a clean slate each test
    setattr(memory_watcher, "_observer", None)

    return memory_watcher, mocks


# ===========================================================================
# Tests: start_memory_watcher
# ===========================================================================


class TestStartMemoryWatcher:
    """Verify start_memory_watcher lifecycle."""

    def test_start_returns_success_with_paths(self, monkeypatch, tmp_path):
        """Starting watcher with valid branch paths returns success."""
        mod, mocks = _import_watcher(monkeypatch)

        branch_path = tmp_path / "src" / "aipass" / "test_branch"
        branch_path.mkdir(parents=True)
        monkeypatch.setattr(mod, "_get_branch_paths", lambda: [branch_path])

        result = mod.start_memory_watcher()

        assert result["success"] is True
        assert result["count"] == 1
        assert str(branch_path) in result["watched_paths"]
        mocks["observer_cls"].assert_called_once()
        mocks["observer_instance"].start.assert_called_once()

    def test_start_fails_when_already_running(self, monkeypatch, tmp_path):
        """Starting when observer is already alive returns error."""
        mod, mocks = _import_watcher(monkeypatch)

        # Simulate already running observer
        mock_existing = MagicMock()
        mock_existing.is_alive.return_value = True
        setattr(mod, "_observer", mock_existing)

        result = mod.start_memory_watcher()

        assert result["success"] is False
        assert "already running" in result["error"].lower()

    def test_start_fails_when_no_branches(self, monkeypatch):
        """Starting with no branch paths returns error."""
        mod, mocks = _import_watcher(monkeypatch)
        monkeypatch.setattr(mod, "_get_branch_paths", lambda: [])

        result = mod.start_memory_watcher()

        assert result["success"] is False
        assert "no branch" in result["error"].lower()

    def test_start_handles_schedule_error_gracefully(self, monkeypatch, tmp_path):
        """If scheduling a path raises an exception, other paths still work."""
        mod, mocks = _import_watcher(monkeypatch)

        good_path = tmp_path / "good_branch"
        good_path.mkdir(parents=True)
        bad_path = tmp_path / "bad_branch"
        bad_path.mkdir(parents=True)

        call_count = 0

        def _mock_schedule(handler, path, recursive=False):
            """Mock observer.schedule that fails on the first call."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("Permission denied")

        mocks["observer_instance"].schedule = _mock_schedule
        monkeypatch.setattr(mod, "_get_branch_paths", lambda: [bad_path, good_path])

        result = mod.start_memory_watcher()

        assert result["success"] is True
        # Only the second path should succeed
        assert result["count"] == 1


# ===========================================================================
# Tests: stop_memory_watcher
# ===========================================================================


class TestStopMemoryWatcher:
    """Verify stop_memory_watcher lifecycle."""

    def test_stop_returns_success(self, monkeypatch):
        """Stopping a running watcher returns success."""
        mod, mocks = _import_watcher(monkeypatch)

        # Set up a running observer
        mock_obs = MagicMock()
        mock_obs.is_alive.return_value = True
        setattr(mod, "_observer", mock_obs)

        result = mod.stop_memory_watcher()

        assert result["success"] is True
        mock_obs.stop.assert_called_once()
        mock_obs.join.assert_called_once()
        assert mod._observer is None  # type: ignore[union-attr]

    def test_stop_fails_when_not_running(self, monkeypatch):
        """Stopping when no watcher is running returns error."""
        mod, mocks = _import_watcher(monkeypatch)

        result = mod.stop_memory_watcher()

        assert result["success"] is False
        assert "not running" in result["error"].lower()

    def test_stop_fails_when_observer_not_alive(self, monkeypatch):
        """Stopping when observer exists but is not alive returns error."""
        mod, mocks = _import_watcher(monkeypatch)

        mock_obs = MagicMock()
        mock_obs.is_alive.return_value = False
        setattr(mod, "_observer", mock_obs)

        result = mod.stop_memory_watcher()

        assert result["success"] is False


# ===========================================================================
# Tests: is_memory_watcher_active
# ===========================================================================


class TestIsMemoryWatcherActive:
    """Verify is_memory_watcher_active boolean checks."""

    def test_active_when_observer_alive(self, monkeypatch):
        """Returns True when observer is alive."""
        mod, mocks = _import_watcher(monkeypatch)

        mock_obs = MagicMock()
        mock_obs.is_alive.return_value = True
        setattr(mod, "_observer", mock_obs)

        assert mod.is_memory_watcher_active() is True

    def test_inactive_when_no_observer(self, monkeypatch):
        """Returns False when _observer is None."""
        mod, mocks = _import_watcher(monkeypatch)

        assert mod.is_memory_watcher_active() is False

    def test_inactive_when_observer_not_alive(self, monkeypatch):
        """Returns False when observer exists but is_alive returns False."""
        mod, mocks = _import_watcher(monkeypatch)

        mock_obs = MagicMock()
        mock_obs.is_alive.return_value = False
        setattr(mod, "_observer", mock_obs)

        assert mod.is_memory_watcher_active() is False


# ===========================================================================
# Tests: get_watcher_status
# ===========================================================================


class TestGetWatcherStatus:
    """Verify get_watcher_status returns correct status info."""

    def test_status_when_inactive(self, monkeypatch):
        """Returns inactive status when watcher is not running."""
        mod, mocks = _import_watcher(monkeypatch)

        result = mod.get_watcher_status()

        assert result["active"] is False
        assert "not running" in result["message"].lower()

    def test_status_when_active(self, monkeypatch, tmp_path):
        """Returns active status with directory count when watcher is running."""
        mod, mocks = _import_watcher(monkeypatch)

        mock_obs = MagicMock()
        mock_obs.is_alive.return_value = True
        setattr(mod, "_observer", mock_obs)

        branch_path = tmp_path / "branch1"
        branch_path.mkdir()
        monkeypatch.setattr(mod, "_get_branch_paths", lambda: [branch_path])

        result = mod.get_watcher_status()

        assert result["active"] is True
        assert result["watched_directories"] == 1
        assert str(branch_path) in result["paths"]

    def test_status_returns_multiple_paths(self, monkeypatch, tmp_path):
        """Returns all watched directory paths."""
        mod, mocks = _import_watcher(monkeypatch)

        mock_obs = MagicMock()
        mock_obs.is_alive.return_value = True
        setattr(mod, "_observer", mock_obs)

        paths = []
        for name in ["branch_a", "branch_b", "branch_c"]:
            p = tmp_path / name
            p.mkdir()
            paths.append(p)

        monkeypatch.setattr(mod, "_get_branch_paths", lambda: paths)

        result = mod.get_watcher_status()

        assert result["watched_directories"] == 3
        assert len(result["paths"]) == 3


# ===========================================================================
# Tests: MemoryFileWatcher.on_modified
# ===========================================================================


class TestMemoryFileWatcherOnModified:
    """Verify MemoryFileWatcher.on_modified callback behavior."""

    def test_ignores_directory_events(self, monkeypatch):
        """Directory modification events are ignored."""
        mod, mocks = _import_watcher(monkeypatch)

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = True
        event.src_path = "/some/.trinity/local.json"

        watcher.on_modified(event)

        mocks["update_line_count"].assert_not_called()

    def test_ignores_non_memory_files(self, monkeypatch):
        """Non-memory files (not in .trinity/) are ignored."""
        mod, mocks = _import_watcher(monkeypatch)

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/dir/config.json"

        watcher.on_modified(event)

        mocks["update_line_count"].assert_not_called()

    def test_processes_memory_file_modification(self, monkeypatch):
        """Valid memory file modification triggers line count update and check."""
        mod, mocks = _import_watcher(monkeypatch)

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/branch/.trinity/local.json"

        watcher.on_modified(event)

        mocks["update_line_count"].assert_called_once()
        mocks["check_single_file"].assert_called_once()

    def test_rollover_triggered_when_threshold_exceeded(self, monkeypatch):
        """When check_single_file says should_rollover, execute_rollover is called."""
        mod, mocks = _import_watcher(monkeypatch)

        mocks["check_single_file"].return_value = {
            "success": True,
            "should_rollover": True,
            "trigger": "lines exceeded 600",
        }

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/branch/.trinity/local.json"

        watcher.on_modified(event)

        mocks["execute_rollover"].assert_called_once()

    def test_skips_recently_modified_file(self, monkeypatch):
        """Files already in the recent modifications set are skipped."""
        mod, mocks = _import_watcher(monkeypatch)

        watcher = mod.MemoryFileWatcher()
        file_path = "/some/branch/.trinity/local.json"
        watcher._recent_modifications.add(file_path)

        event = MagicMock()
        event.is_directory = False
        event.src_path = file_path

        watcher.on_modified(event)

        # Should skip and not call update_line_count
        mocks["update_line_count"].assert_not_called()
        # The file key should be removed from recent modifications after skip
        assert file_path not in watcher._recent_modifications

    def test_handles_line_count_update_failure(self, monkeypatch):
        """When update_line_count fails, check_single_file is not called."""
        mod, mocks = _import_watcher(monkeypatch)

        mocks["update_line_count"].return_value = {
            "success": False,
            "error": "File not found",
        }

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/branch/.trinity/local.json"

        watcher.on_modified(event)

        mocks["update_line_count"].assert_called_once()
        mocks["check_single_file"].assert_not_called()

    def test_handles_check_failure(self, monkeypatch):
        """When check_single_file fails, rollover is not triggered."""
        mod, mocks = _import_watcher(monkeypatch)

        mocks["check_single_file"].return_value = {
            "success": False,
            "error": "Read error",
        }

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/branch/.trinity/local.json"

        watcher.on_modified(event)

        mocks["check_single_file"].assert_called_once()
        mocks["execute_rollover"].assert_not_called()

    def test_processes_observations_json(self, monkeypatch):
        """observations.json files in .trinity/ are also processed."""
        mod, mocks = _import_watcher(monkeypatch)

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/branch/.trinity/observations.json"

        watcher.on_modified(event)

        mocks["update_line_count"].assert_called_once()

    def test_rollover_exception_does_not_propagate(self, monkeypatch):
        """If execute_rollover raises, the exception is caught."""
        mod, mocks = _import_watcher(monkeypatch)

        mocks["check_single_file"].return_value = {
            "success": True,
            "should_rollover": True,
            "trigger": "lines exceeded",
        }
        mocks["execute_rollover"].side_effect = RuntimeError("Rollover crashed")

        watcher = mod.MemoryFileWatcher()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/some/branch/.trinity/local.json"

        # Should not raise
        watcher.on_modified(event)

        mocks["execute_rollover"].assert_called_once()
