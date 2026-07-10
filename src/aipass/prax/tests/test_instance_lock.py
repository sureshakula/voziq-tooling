# =================== AIPass ====================
# Name: test_instance_lock.py
# Description: Tests for the monitor single-instance lock
# Version: 1.0.0
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""Tests for apps/handlers/monitoring/instance_lock.py

Covers:
- _is_pid_alive() cross-platform liveness check
- acquire() creates lock, refuses live duplicate, reclaims stale
- release() removes lock file on clean shutdown
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

_HANDLER_MOCKS = {
    "aipass.prax.apps.handlers.json": MagicMock(),
    "aipass.prax.apps.handlers.json.json_handler": MagicMock(),
}


def _import_lock():
    """Import (or reload) instance_lock with handler mocks."""
    fresh = {k: MagicMock() for k in _HANDLER_MOCKS}
    with patch.dict(sys.modules, fresh):
        import importlib

        if "aipass.prax.apps.handlers.monitoring.instance_lock" in sys.modules:
            mod = importlib.reload(sys.modules["aipass.prax.apps.handlers.monitoring.instance_lock"])
        else:
            mod = importlib.import_module("aipass.prax.apps.handlers.monitoring.instance_lock")
        return mod


class TestIsPidAlive:
    """Test cross-platform PID liveness check."""

    def test_live_pid_returns_true_posix(self):
        """os.kill(pid, 0) success means alive on POSIX."""
        mod = _import_lock()
        with patch("sys.platform", "linux"), patch("os.kill"):
            assert mod._is_pid_alive(os.getpid()) is True

    def test_dead_pid_returns_false(self):
        """Non-existent PID returns False on POSIX."""
        mod = _import_lock()
        with patch("sys.platform", "linux"), patch("os.kill", side_effect=ProcessLookupError):
            assert mod._is_pid_alive(99999999) is False

    def test_permission_error_means_alive(self):
        """PermissionError means the process exists but is owned by another user."""
        mod = _import_lock()
        with patch("sys.platform", "linux"), patch("os.kill", side_effect=PermissionError):
            assert mod._is_pid_alive(1) is True

    def test_generic_oserror_returns_false(self):
        """Other OSError returns False."""
        mod = _import_lock()
        with patch("sys.platform", "linux"), patch("os.kill", side_effect=OSError(99, "Unknown")):
            assert mod._is_pid_alive(12345) is False

    def test_windows_delegates_to_pid_alive_windows(self):
        """On win32, _is_pid_alive delegates to _pid_alive_windows."""
        mod = _import_lock()
        with (
            patch("sys.platform", "win32"),
            patch.object(mod, "_pid_alive_windows", return_value=True) as mock_win,
        ):
            assert mod._is_pid_alive(1234) is True
            mock_win.assert_called_once_with(1234)

    def test_windows_dead_pid(self):
        """On win32, dead PID returns False via _pid_alive_windows."""
        mod = _import_lock()
        with (
            patch("sys.platform", "win32"),
            patch.object(mod, "_pid_alive_windows", return_value=False),
        ):
            assert mod._is_pid_alive(99999999) is False

    def test_windows_ctypes_failure_assumes_alive(self):
        """On win32, if ctypes fails, assume the process is alive (safe default)."""
        mod = _import_lock()
        with (
            patch("sys.platform", "win32"),
            patch.object(mod, "_pid_alive_windows", side_effect=OSError("ctypes failed")),
        ):
            assert mod._is_pid_alive(1234) is True


class TestAcquire:
    """Test single-instance lock acquisition."""

    def test_creates_lock_file(self, tmp_path):
        """acquire() creates a lock file with the current PID."""
        mod = _import_lock()
        lock_path = tmp_path / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        mod.acquire()

        assert lock_path.exists()
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()

    def test_refuses_when_live_instance_holds_lock(self, tmp_path):
        """acquire() exits with SystemExit(1) when another live process holds the lock."""
        mod = _import_lock()
        lock_path = tmp_path / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        lock_path.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")

        import pytest

        mock_error = MagicMock()
        with pytest.raises(SystemExit) as exc_info:
            mod.acquire(error_fn=mock_error)
        assert exc_info.value.code == 1
        mock_error.assert_called_once()
        assert str(os.getpid()) in mock_error.call_args[0][0]

    def test_reclaims_stale_lock(self, tmp_path):
        """acquire() reclaims the lock when the recorded PID is dead."""
        mod = _import_lock()
        lock_path = tmp_path / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        lock_path.write_text(json.dumps({"pid": 99999999}), encoding="utf-8")

        with patch.object(mod, "_is_pid_alive", return_value=False):
            mod.acquire()

        data = json.loads(lock_path.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()

    def test_reclaims_corrupt_lock_file(self, tmp_path):
        """acquire() overwrites a corrupt lock file."""
        mod = _import_lock()
        lock_path = tmp_path / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        lock_path.write_text("{corrupt json", encoding="utf-8")

        mod.acquire()

        data = json.loads(lock_path.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()

    def test_creates_parent_directories(self, tmp_path):
        """acquire() creates parent directories if they don't exist."""
        mod = _import_lock()
        lock_path = tmp_path / "nested" / "dir" / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        mod.acquire()

        assert lock_path.exists()


class TestRelease:
    """Test single-instance lock release."""

    def test_removes_lock_file(self, tmp_path):
        """release() removes the lock file."""
        mod = _import_lock()
        lock_path = tmp_path / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        mod.acquire()
        assert lock_path.exists()

        mod.release()
        assert not lock_path.exists()

    def test_clears_held_lock_state(self, tmp_path):
        """release() clears the _held_lock global."""
        mod = _import_lock()
        lock_path = tmp_path / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        mod.acquire()
        mod.release()
        assert mod._held_lock is None

    def test_release_without_acquire_is_safe(self):
        """release() is a no-op when no lock is held."""
        mod = _import_lock()
        setattr(mod, "_held_lock", None)
        mod.release()

    def test_release_handles_already_deleted_file(self, tmp_path):
        """release() handles the case where the lock file was already deleted."""
        mod = _import_lock()
        lock_path = tmp_path / "monitor.pid"
        setattr(mod, "_lock_path_override", lock_path)

        mod.acquire()
        lock_path.unlink()
        mod.release()
        assert mod._held_lock is None
