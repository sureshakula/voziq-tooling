# =================== AIPass ====================
# Name: test_event_handlers.py
# Description: Tests for simple event handler functions
# Version: 1.0.0
# Created: 2026-04-25
# Modified: 2026-04-25
# =============================================

"""Tests for cli, error_logged, memory, memory_template_updated, warning_logged, and bulletin_created event handlers."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_infrastructure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mock heavy infrastructure imports for all six handler modules."""
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

    for mod_name in (
        "aipass.trigger.apps.handlers.events.cli",
        "aipass.trigger.apps.handlers.events.error_logged",
        "aipass.trigger.apps.handlers.events.memory",
        "aipass.trigger.apps.handlers.events.memory_template_updated",
        "aipass.trigger.apps.handlers.events.warning_logged",
        "aipass.trigger.apps.handlers.events.bulletin_created",
    ):
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


def _import_cli():
    """Import cli handler module fresh after mocking."""
    import aipass.trigger.apps.handlers.events.cli as m

    return m


def _import_error_logged():
    """Import error_logged handler module fresh after mocking."""
    import aipass.trigger.apps.handlers.events.error_logged as m

    return m


def _import_memory():
    """Import memory handler module fresh after mocking."""
    import aipass.trigger.apps.handlers.events.memory as m

    return m


def _import_memory_template_updated():
    """Import memory_template_updated handler module fresh after mocking."""
    import aipass.trigger.apps.handlers.events.memory_template_updated as m

    return m


def _import_warning_logged():
    """Import warning_logged handler module fresh after mocking."""
    import aipass.trigger.apps.handlers.events.warning_logged as m

    return m


def _import_bulletin():
    """Import bulletin_created handler module fresh after mocking."""
    import aipass.trigger.apps.handlers.events.bulletin_created as m

    return m


# ---------------------------------------------------------------------------
# cli.py -- handle_cli_header_displayed
# ---------------------------------------------------------------------------


class TestHandleCliHeaderDisplayed:
    """Tests for handle_cli_header_displayed from cli.py."""

    def test_calls_log_operation(self) -> None:
        """Logs cli_event via json_handler."""
        mod = _import_cli()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_cli_header_displayed()

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "cli_event", {"success": True}
        )

    def test_accepts_arbitrary_kwargs(self) -> None:
        """Does not crash when extra kwargs are passed."""
        mod = _import_cli()
        mod.handle_cli_header_displayed(foo="bar", baz=42)

    def test_returns_none(self) -> None:
        """Handler returns None (handlers must not return values)."""
        mod = _import_cli()
        result = mod.handle_cli_header_displayed()
        assert result is None


# ---------------------------------------------------------------------------
# error_logged.py -- handle_error_logged
# ---------------------------------------------------------------------------


class TestHandleErrorLogged:
    """Tests for handle_error_logged from error_logged.py."""

    def test_happy_path_logs_operation(self) -> None:
        """Logs error_logged_event with branch, module, and error_hash."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(branch="flow", message="kaboom", error_hash="abc123")

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "error_logged_event",
            {"branch": "flow", "module": "unknown", "error_hash": "abc123"},
        )

    def test_returns_early_missing_branch(self) -> None:
        """Does not log when branch is None."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(branch=None, message="msg", error_hash="h")

        json_handler.log_operation.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_missing_message(self) -> None:
        """Does not log when message is None."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(branch="flow", message=None, error_hash="h")

        json_handler.log_operation.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_missing_error_hash(self) -> None:
        """Does not log when error_hash is None."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(branch="flow", message="msg", error_hash=None)

        json_handler.log_operation.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_empty_branch(self) -> None:
        """Does not log when branch is empty string (falsy)."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(branch="", message="msg", error_hash="h")

        json_handler.log_operation.assert_not_called()  # type: ignore[union-attr]

    def test_prefers_source_module_over_module_name(self) -> None:
        """Uses source_module when both source_module and module_name are given."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(
            branch="api",
            message="err",
            error_hash="xyz",
            source_module="config.py",
            module_name="old_name.py",
        )

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "error_logged_event",
            {"branch": "api", "module": "config.py", "error_hash": "xyz"},
        )

    def test_falls_back_to_module_name(self) -> None:
        """Uses module_name when source_module is not provided."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(
            branch="spawn",
            message="err",
            error_hash="h1",
            module_name="fallback.py",
        )

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "error_logged_event",
            {"branch": "spawn", "module": "fallback.py", "error_hash": "h1"},
        )

    def test_falls_back_to_unknown(self) -> None:
        """Uses 'unknown' when neither source_module nor module_name given."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_error_logged(branch="drone", message="oops", error_hash="h2")

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "error_logged_event",
            {"branch": "drone", "module": "unknown", "error_hash": "h2"},
        )

    def test_exception_does_not_raise(self) -> None:
        """Catches exception from log_operation without propagating."""
        mod = _import_error_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.side_effect = RuntimeError("boom")  # type: ignore[union-attr]

        mod.handle_error_logged(branch="flow", message="msg", error_hash="h3")

        json_handler.log_operation.side_effect = None  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# memory.py -- handle_memory_saved
# ---------------------------------------------------------------------------


class TestHandleMemorySaved:
    """Tests for handle_memory_saved from memory.py."""

    def test_calls_log_operation(self) -> None:
        """Logs memory_event via json_handler."""
        mod = _import_memory()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_saved()

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "memory_event", {"success": True}
        )

    def test_accepts_kwargs(self) -> None:
        """Does not crash when event data kwargs are passed."""
        mod = _import_memory()
        mod.handle_memory_saved(branch="flow", lines=150)

    def test_returns_none(self) -> None:
        """Handler returns None."""
        mod = _import_memory()
        result = mod.handle_memory_saved()
        assert result is None


# ---------------------------------------------------------------------------
# memory_template_updated.py -- handle_memory_template_updated
# ---------------------------------------------------------------------------


class TestHandleMemoryTemplateUpdated:
    """Tests for handle_memory_template_updated from memory_template_updated.py."""

    def test_calls_log_operation(self) -> None:
        """Logs memory_template_event via json_handler."""
        mod = _import_memory_template_updated()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_template_updated()

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "memory_template_event", {"success": True}
        )

    def test_accepts_kwargs(self) -> None:
        """Does not crash when event data kwargs are passed."""
        mod = _import_memory_template_updated()
        mod.handle_memory_template_updated(template_name="local", updated_by="drone")

    def test_returns_none(self) -> None:
        """Handler returns None."""
        mod = _import_memory_template_updated()
        result = mod.handle_memory_template_updated()
        assert result is None


# ---------------------------------------------------------------------------
# warning_logged.py -- handle_warning_logged
# ---------------------------------------------------------------------------


class TestHandleWarningLogged:
    """Tests for handle_warning_logged from warning_logged.py."""

    def test_calls_log_operation(self) -> None:
        """Logs warning_logged_event via json_handler."""
        mod = _import_warning_logged()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_warning_logged()

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "warning_logged_event", {"success": True}
        )

    def test_accepts_all_named_params(self) -> None:
        """Accepts all documented event parameters without error."""
        mod = _import_warning_logged()
        mod.handle_warning_logged(
            branch="flow",
            message="disk almost full",
            error_hash="w1",
            timestamp="2026-04-25T12:00:00",
            log_file="flow.log",
            module_name="watcher",
            level="warning",
        )

    def test_does_not_crash_with_none_params(self) -> None:
        """Handles None for every named parameter gracefully."""
        mod = _import_warning_logged()
        mod.handle_warning_logged(
            branch=None,
            message=None,
            error_hash=None,
            timestamp=None,
            log_file=None,
            module_name=None,
            level=None,
        )

    def test_accepts_extra_kwargs(self) -> None:
        """Accepts unexpected kwargs via **kwargs."""
        mod = _import_warning_logged()
        mod.handle_warning_logged(extra_field="unexpected")

    def test_returns_none(self) -> None:
        """Handler returns None."""
        mod = _import_warning_logged()
        result = mod.handle_warning_logged()
        assert result is None


# ---------------------------------------------------------------------------
# bulletin_created.py -- handle_bulletin_created
# ---------------------------------------------------------------------------


class TestHandleBulletinCreated:
    """Tests for handle_bulletin_created from bulletin_created.py."""

    def test_does_not_raise_when_files_missing(self) -> None:
        """Silently handles missing registry and bulletins files."""
        mod = _import_bulletin()
        mod.handle_bulletin_created()

    def test_logs_operation_on_success(self) -> None:
        """Logs bulletin_event after successful propagation."""
        mod = _import_bulletin()
        mod._propagate_bulletins_to_branches = MagicMock()
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_bulletin_created()

        mod._propagate_bulletins_to_branches.assert_called_once()
        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "bulletin_event", {"success": True}
        )

    def test_catches_propagation_exception(self) -> None:
        """Does not log operation when propagation raises."""
        mod = _import_bulletin()
        mod._propagate_bulletins_to_branches = MagicMock(side_effect=RuntimeError("propagation failed"))
        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]

        mod.handle_bulletin_created()

        json_handler.log_operation.assert_not_called()  # type: ignore[union-attr]

    def test_accepts_all_params(self) -> None:
        """Accepts all documented event parameters without error."""
        mod = _import_bulletin()
        mod._propagate_bulletins_to_branches = MagicMock()

        mod.handle_bulletin_created(
            _bulletin_id="b1",
            _title="System update",
            _message="Scheduled maintenance",
            _priority="high",
            _created_by="devpulse",
            _timestamp="2026-04-25T10:00:00",
        )

    def test_returns_none(self) -> None:
        """Handler returns None."""
        mod = _import_bulletin()
        mod._propagate_bulletins_to_branches = MagicMock()
        result = mod.handle_bulletin_created()
        assert result is None
