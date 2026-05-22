# =================== AIPass ====================
# Name: test_identity.py
# Version: 1.0.0
# Description: Tests for identity prompt handler
# Branch: hooks
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/prompt/identity.py."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock


SAMPLE_PASSPORT = {
    "branch_info": {
        "branch_name": "devpulse",
        "path": "src/aipass/devpulse",
        "email": "unknown",
    },
    "identity": {
        "role": "orchestration_hub",
        "purpose": "The user's primary AI collaborator",
        "traits": ["Pragmatic", "Direct"],
        "what_i_do": ["Plan", "Design", "Debug"],
        "what_i_dont_do": ["Full rebuilds"],
    },
    "principles": ["Fail honestly", "Memory is everything"],
}


class TestIdentityHandler:
    def test_returns_identity_when_passport_found(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        passport = trinity / "passport.json"
        passport.write_text(json.dumps(SAMPLE_PASSPORT), encoding="utf-8")

        with patch("aipass.hooks.apps.handlers.prompt.identity._speak"):
            result = handle({"cwd": str(tmp_path)})

        assert result["exit_code"] == 0
        assert "devpulse Identity" in result["stdout"]
        assert "orchestration_hub" in result["stdout"]
        assert "Pragmatic" in result["stdout"]

    def test_returns_empty_when_no_passport(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        with patch("aipass.hooks.apps.handlers.prompt.identity._speak"):
            result = handle({"cwd": str(tmp_path)})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_walks_up_to_find_passport(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        passport = trinity / "passport.json"
        passport.write_text(json.dumps(SAMPLE_PASSPORT), encoding="utf-8")
        nested = tmp_path / "apps" / "handlers"
        nested.mkdir(parents=True)

        with patch("aipass.hooks.apps.handlers.prompt.identity._speak"):
            result = handle({"cwd": str(nested)})

        assert "devpulse Identity" in result["stdout"]

    def test_formats_all_fields(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        passport = trinity / "passport.json"
        passport.write_text(json.dumps(SAMPLE_PASSPORT), encoding="utf-8")

        with patch("aipass.hooks.apps.handlers.prompt.identity._speak"):
            result = handle({"cwd": str(tmp_path)})

        out = result["stdout"]
        assert "Path: src/aipass/devpulse" in out
        assert "Email: unknown" in out
        assert "Role: orchestration_hub" in out
        assert "Purpose: The user's primary AI collaborator" in out
        assert "Do: Plan | Design | Debug" in out
        assert "Don't: Full rebuilds" in out
        assert "Principles: Fail honestly * Memory is everything" in out

    def test_handles_minimal_passport(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        passport = trinity / "passport.json"
        passport.write_text(json.dumps({"branch_info": {"branch_name": "test"}, "identity": {}}), encoding="utf-8")

        with patch("aipass.hooks.apps.handlers.prompt.identity._speak"):
            result = handle({"cwd": str(tmp_path)})

        assert result["exit_code"] == 0
        assert "test Identity" in result["stdout"]

    def test_empty_hook_data(self):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        with patch("aipass.hooks.apps.handlers.prompt.identity._speak"):
            with patch("pathlib.Path.cwd", return_value=Path("/tmp/nonexistent")):
                result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_corrupt_passport_json(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        passport = trinity / "passport.json"
        passport.write_text("{broken json", encoding="utf-8")

        with patch("aipass.hooks.apps.handlers.prompt.identity._speak"):
            result = handle({"cwd": str(tmp_path)})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_piper_fires(self, mock_run, mock_popen):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(Path, "exists", return_value=True):
            handle({"cwd": "/tmp/nonexistent"})

        assert mock_run.called or mock_popen.called

    def test_piper_skips_when_not_available(self):
        from aipass.hooks.apps.handlers.prompt.identity import handle

        with patch("aipass.hooks.apps.handlers.prompt.identity.PIPER_BIN", Path("/nonexistent/piper")):
            result = handle({"cwd": "/tmp/nonexistent"})

        assert result["exit_code"] == 0
