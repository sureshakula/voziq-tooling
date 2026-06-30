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


class TestResolveBranch:
    def test_uses_hook_data_cwd(self, tmp_path):
        branch_dir = tmp_path / "devpulse"
        branch_dir.mkdir()
        (branch_dir / ".trinity").mkdir()
        assert presence_gate._resolve_branch({"cwd": str(branch_dir)}) == "devpulse"

    def test_walks_up_to_branch_root(self, tmp_path):
        branch_dir = tmp_path / "hooks"
        (branch_dir / "apps" / "modules").mkdir(parents=True)
        sub = branch_dir / "apps" / "modules"
        assert presence_gate._resolve_branch({"cwd": str(sub)}) == "hooks"

    def test_stops_at_repo_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert presence_gate._resolve_branch({"cwd": str(tmp_path)}) == tmp_path.name

    def test_fallback_to_path_cwd_when_no_cwd_in_hook_data(self):
        result = presence_gate._resolve_branch({})
        assert isinstance(result, str)
        assert len(result) > 0


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

    def test_block_message_includes_branch(self, tmp_path):
        branch_dir = tmp_path / "devpulse"
        branch_dir.mkdir()
        (branch_dir / ".trinity").mkdir()
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "interactive"}, clear=True):
            with patch("importlib.import_module", return_value=_OCCUPIED_MOCK):
                result = presence_gate.handle({"cwd": str(branch_dir)})
        parsed = json.loads(result["stdout"])
        assert "devpulse" in parsed["reason"]
        assert "attach" in parsed["reason"].lower()

    def test_branch_resolved_from_hook_data_cwd(self, tmp_path):
        branch_dir = tmp_path / "api"
        branch_dir.mkdir()
        (branch_dir / ".trinity").mkdir()
        mock = _make_presence_mock({"status": "ACQUIRED"})
        with patch.dict(os.environ, {"AIPASS_SESSION_TYPE": "interactive"}, clear=True):
            with patch("importlib.import_module", return_value=mock):
                presence_gate.handle({"cwd": str(branch_dir)})
        mock.claim.assert_called_once()
        assert mock.claim.call_args[1]["branch"] == "api"


class TestHandleStop:
    def test_stop_is_noop(self):
        result = presence_gate.handle_stop({})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_stop_does_not_call_presence(self):
        mock = _make_presence_mock({"status": "ACQUIRED"})
        with patch("importlib.import_module", return_value=mock):
            presence_gate.handle_stop({})
        mock.release.assert_not_called()
        mock.claim.assert_not_called()
