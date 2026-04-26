# =================== AIPass ====================
# Name: test_startup_handler.py
# Description: Tests for startup event handler
# Version: 1.0.0
# Created: 2026-04-25
# Modified: 2026-04-25
# =============================================

"""Tests for startup event handler."""

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
        "aipass.trigger.apps.handlers.events.startup",
        raising=False,
    )


def _import_startup():
    """Import fresh after mocking."""
    import aipass.trigger.apps.handlers.events.startup as m

    return m


class TestHandleStartup:
    """Tests for handle_startup."""

    def test_calls_error_catchup_with_fire_event(self) -> None:
        """Passes fire_event kwarg to _run_error_catchup."""
        mod = _import_startup()
        mod._run_error_catchup = MagicMock()
        mod._run_memory_check = MagicMock()

        fire_event = MagicMock()
        mod.handle_startup(fire_event=fire_event)

        mod._run_error_catchup.assert_called_once_with(fire_event)  # type: ignore[union-attr]

    def test_calls_memory_check(self) -> None:
        """Invokes _run_memory_check on every startup."""
        mod = _import_startup()
        mod._run_error_catchup = MagicMock()
        mod._run_memory_check = MagicMock()

        mod.handle_startup()

        mod._run_memory_check.assert_called_once()  # type: ignore[union-attr]

    def test_passes_none_when_no_fire_event(self) -> None:
        """Without fire_event kwarg, passes None to error catchup."""
        mod = _import_startup()
        mod._run_error_catchup = MagicMock()
        mod._run_memory_check = MagicMock()

        mod.handle_startup()

        mod._run_error_catchup.assert_called_once_with(None)  # type: ignore[union-attr]

    def test_calls_both_helpers_in_order(self) -> None:
        """Error catchup runs before memory check."""
        mod = _import_startup()
        call_order: list[str] = []
        mod._run_error_catchup = MagicMock(side_effect=lambda *a, **kw: call_order.append("catchup"))
        mod._run_memory_check = MagicMock(side_effect=lambda *a, **kw: call_order.append("memory"))

        mod.handle_startup(fire_event=MagicMock())

        assert call_order == ["catchup", "memory"]

    def test_extra_kwargs_do_not_crash(self) -> None:
        """Arbitrary extra kwargs are silently ignored."""
        mod = _import_startup()
        mod._run_error_catchup = MagicMock()
        mod._run_memory_check = MagicMock()

        mod.handle_startup(fire_event=MagicMock(), extra_arg="ignored", count=42)

        mod._run_error_catchup.assert_called_once()  # type: ignore[union-attr]
        mod._run_memory_check.assert_called_once()  # type: ignore[union-attr]
