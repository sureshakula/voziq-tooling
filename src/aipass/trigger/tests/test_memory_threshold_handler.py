# =================== AIPass ====================
# Name: test_memory_threshold_handler.py
# Description: Tests for memory_threshold_exceeded event handler
# Version: 1.0.0
# Created: 2026-04-25
# Modified: 2026-04-25
# =============================================

"""Tests for memory_threshold_exceeded event handler."""

import sys

import pytest
from unittest.mock import MagicMock
from pathlib import Path


@pytest.fixture(autouse=True)
def _mock_infrastructure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mock heavy infrastructure imports before importing the handler module."""
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

    # Mock ai_mail chain so the handler can import deliver_email_to_branch
    mock_email_send = MagicMock()
    mock_email_send.deliver_email_to_branch = MagicMock()
    monkeypatch.setitem(sys.modules, "aipass.ai_mail", MagicMock())
    monkeypatch.setitem(sys.modules, "aipass.ai_mail.apps", MagicMock())
    monkeypatch.setitem(sys.modules, "aipass.ai_mail.apps.modules", MagicMock())
    monkeypatch.setitem(sys.modules, "aipass.ai_mail.apps.modules.email_send", mock_email_send)

    monkeypatch.delitem(
        sys.modules,
        "aipass.trigger.apps.handlers.events.memory_threshold_exceeded",
        raising=False,
    )


def _import_memory_threshold():
    """Import fresh after mocking."""
    import aipass.trigger.apps.handlers.events.memory_threshold_exceeded as m

    return m


class TestHandleMemoryThresholdExceeded:
    """Tests for handle_memory_threshold_exceeded."""

    def test_returns_early_when_branch_missing(self) -> None:
        """None branch skips email delivery."""
        mod = _import_memory_threshold()

        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_threshold_exceeded(branch=None, file_name="local.json", line_count=700)

        deliver_email_to_branch.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_when_file_name_missing(self) -> None:
        """None file_name skips email delivery."""
        mod = _import_memory_threshold()

        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_threshold_exceeded(branch="flow", file_name=None, line_count=700)

        deliver_email_to_branch.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_when_line_count_is_none(self) -> None:
        """None line_count skips email delivery."""
        mod = _import_memory_threshold()

        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_threshold_exceeded(branch="flow", file_name="local.json", line_count=None)

        deliver_email_to_branch.assert_not_called()  # type: ignore[union-attr]

    def test_returns_early_when_ai_mail_import_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No operation is logged when ai_mail import fails."""
        # Setting the module to None causes ImportError on `from ... import`
        monkeypatch.setitem(sys.modules, "aipass.ai_mail.apps.modules.email_send", None)

        mod = _import_memory_threshold()
        mod.handle_memory_threshold_exceeded(branch="flow", file_name="local.json", line_count=700)

        from aipass.trigger.apps.handlers.json import json_handler

        json_handler.log_operation.assert_not_called()  # type: ignore[union-attr]

    def test_happy_path_sends_email(self) -> None:
        """Sends email with correct target and email data on valid input."""
        mod = _import_memory_threshold()

        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_threshold_exceeded(
            branch="flow",
            file_name="local.json",
            line_count=700,
            threshold=600,
            timestamp="2026-04-25 12:00:00",
        )

        deliver_email_to_branch.assert_called_once()  # type: ignore[union-attr]
        target, email_data = deliver_email_to_branch.call_args[0]  # type: ignore[union-attr]
        assert target == "@flow"
        assert email_data["to"] == "@flow"
        assert email_data["from"] == "@trigger"
        assert "local.json" in email_data["subject"]
        assert "600" in email_data["subject"]
        assert email_data["timestamp"] == "2026-04-25 12:00:00"

    def test_uses_default_threshold_when_not_provided(self) -> None:
        """Falls back to default threshold of 600 when not explicitly given."""
        mod = _import_memory_threshold()

        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_threshold_exceeded(branch="drone", file_name="observations.json", line_count=800)

        deliver_email_to_branch.assert_called_once()  # type: ignore[union-attr]
        _, email_data = deliver_email_to_branch.call_args[0]  # type: ignore[union-attr]
        assert "600" in email_data["subject"]

    def test_uses_default_timestamp_when_not_provided(self) -> None:
        """Generates a non-empty timestamp when none is supplied."""
        mod = _import_memory_threshold()

        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_threshold_exceeded(branch="api", file_name="local.json", line_count=650)

        deliver_email_to_branch.assert_called_once()  # type: ignore[union-attr]
        _, email_data = deliver_email_to_branch.call_args[0]  # type: ignore[union-attr]
        assert email_data["timestamp"] is not None
        assert len(email_data["timestamp"]) > 0

    def test_does_not_raise_on_deliver_exception(self) -> None:
        """Delivery failure is swallowed without propagating."""
        mod = _import_memory_threshold()

        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]
        deliver_email_to_branch.side_effect = RuntimeError(  # type: ignore[union-attr]
            "delivery failed"
        )

        mod.handle_memory_threshold_exceeded(
            branch="flow",
            file_name="local.json",
            line_count=700,
            threshold=600,
        )

        deliver_email_to_branch.side_effect = None  # type: ignore[union-attr]

    def test_logs_operation_on_success(self) -> None:
        """Logs memory_threshold_event via json_handler after successful send."""
        mod = _import_memory_threshold()

        from aipass.trigger.apps.handlers.json import json_handler
        from aipass.ai_mail.apps.modules.email_send import deliver_email_to_branch

        json_handler.log_operation.reset_mock()  # type: ignore[union-attr]
        deliver_email_to_branch.reset_mock()  # type: ignore[union-attr]

        mod.handle_memory_threshold_exceeded(
            branch="system",
            file_name="local.json",
            line_count=900,
            threshold=600,
        )

        json_handler.log_operation.assert_called_once_with(  # type: ignore[union-attr]
            "memory_threshold_event", {"success": True}
        )
