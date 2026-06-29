"""Tests for the presence gate handler."""

import json
import os
from unittest.mock import MagicMock, patch

from aipass.hooks.apps.handlers.security import presence_gate


def _make_presence_mock(claim_result, release_result=True):
    """Build a mock presence module with given claim/release return values."""
    mock = MagicMock()
    mock.claim.return_value = claim_result
    mock.release.return_value = release_result
    return mock


_ACQUIRED_MOCK = _make_presence_mock({"status": "ACQUIRED"})
_OCCUPIED_MOCK = _make_presence_mock(
    {
        "status": "OCCUPIED",
        "pid": 5000,
        "session_id": "existing",
        "work_dir": "/tmp/branch",
        "session_type": "interactive",
    }
)


class TestHandle:
    def test_first_prompt_acquired(self):
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "interactive"}, clear=True):
            with patch("importlib.import_module", return_value=_ACQUIRED_MOCK):
                result = presence_gate.handle({})
        assert result["exit_code"] == 0

    def test_occupied_blocks(self):
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "interactive"}, clear=True):
            with patch("importlib.import_module", return_value=_OCCUPIED_MOCK):
                result = presence_gate.handle({})
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "5000" in parsed["reason"]

    def test_subagent_skipped(self):
        result = presence_gate.handle({"agent_type": "sub"})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_main_agent_not_skipped(self):
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "interactive"}, clear=True):
            with patch("importlib.import_module", return_value=_ACQUIRED_MOCK):
                result = presence_gate.handle({"agent_type": "main"})
        assert result["exit_code"] == 0

    def test_dispatched_session_skipped(self):
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "dispatched"}, clear=True):
            result = presence_gate.handle({})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_daemon_session_skipped(self):
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "daemon"}, clear=True):
            result = presence_gate.handle({})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_resume_dead_holder_acquires(self):
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "interactive"}, clear=True):
            with patch("importlib.import_module", return_value=_ACQUIRED_MOCK):
                result = presence_gate.handle({})
        assert result["exit_code"] == 0

    def test_block_message_includes_branch(self):
        mock_cwd = MagicMock()
        mock_cwd.name = "devpulse"
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "interactive"}, clear=True):
            with patch("importlib.import_module", return_value=_OCCUPIED_MOCK):
                with patch.object(presence_gate.Path, "cwd", return_value=mock_cwd):
                    result = presence_gate.handle({})
        parsed = json.loads(result["stdout"])
        assert "devpulse" in parsed["reason"]
        assert "attach" in parsed["reason"].lower()


class TestHandleStop:
    def test_stop_releases(self):
        mock = _make_presence_mock({"status": "ACQUIRED"})
        with patch("importlib.import_module", return_value=mock):
            result = presence_gate.handle_stop({})
        assert result["exit_code"] == 0
        mock.release.assert_called_once()

    def test_stop_nothing_to_release(self):
        mock = _make_presence_mock({"status": "ACQUIRED"}, release_result=False)
        with patch("importlib.import_module", return_value=mock):
            result = presence_gate.handle_stop({})
        assert result["exit_code"] == 0

    def test_stop_exception_handled(self):
        with patch("importlib.import_module", side_effect=ImportError("no module")):
            result = presence_gate.handle_stop({})
        assert result["exit_code"] == 0
