# =================== AIPass ====================
# Name: test_compact.py
# Version: 1.0.0
# Description: Tests for compact lifecycle handler
# Branch: hooks
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/lifecycle/compact.py."""

import json
from unittest.mock import patch, MagicMock


class TestCompactHandler:
    def test_injects_recovery_context(self, tmp_path):
        from aipass.hooks.apps.handlers.lifecycle.compact import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        local = trinity / "local.json"
        local.write_text(
            json.dumps(
                {
                    "sessions": [{"id": "S10", "d": "2026-05-22", "sum": "did stuff"}],
                    "key_learnings": {"learn1": "value1"},
                }
            ),
            encoding="utf-8",
        )
        status = tmp_path / "STATUS.local.md"
        status.write_text("# Status\nCurrent work here", encoding="utf-8")

        with patch("aipass.hooks.apps.handlers.lifecycle.compact.speak"):
            with patch("aipass.hooks.apps.handlers.lifecycle.compact._get_git_info", return_value="Git branch: dev"):
                result = handle({"cwd": str(tmp_path)})

        assert result["exit_code"] == 0
        assert "POST-COMPACT RECOVERY" in result["stdout"]
        assert "Git branch: dev" in result["stdout"]
        assert "did stuff" in result["stdout"]
        assert "Current work here" in result["stdout"]

    def test_returns_recovery_when_no_branch_dir(self):
        from aipass.hooks.apps.handlers.lifecycle.compact import handle

        with patch("aipass.hooks.apps.handlers.lifecycle.compact.speak"):
            with patch("aipass.hooks.apps.handlers.lifecycle.compact._get_git_info", return_value=None):
                result = handle({"cwd": "/tmp/nonexistent"})

        assert result["exit_code"] == 0
        assert "POST-COMPACT RECOVERY" in result["stdout"]

    def test_dispatched_agent_gets_save_warning(self, tmp_path):
        from aipass.hooks.apps.handlers.lifecycle.compact import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()

        with patch("aipass.hooks.apps.handlers.lifecycle.compact.speak"):
            with patch("aipass.hooks.apps.handlers.lifecycle.compact._get_git_info", return_value=None):
                with patch.dict("os.environ", {"AIPASS_SESSION_TYPE": "dispatched"}):
                    result = handle({"cwd": str(tmp_path)})

        assert "SAVE STATE NOW" in result["stdout"]

    def test_interactive_gets_recovery_protocol(self, tmp_path):
        from aipass.hooks.apps.handlers.lifecycle.compact import handle

        trinity = tmp_path / ".trinity"
        trinity.mkdir()

        with patch("aipass.hooks.apps.handlers.lifecycle.compact.speak"):
            with patch("aipass.hooks.apps.handlers.lifecycle.compact._get_git_info", return_value=None):
                with patch.dict("os.environ", {"AIPASS_SESSION_TYPE": ""}):
                    result = handle({"cwd": str(tmp_path)})

        assert "Recovery Protocol" in result["stdout"]

    def test_empty_hook_data(self):
        from aipass.hooks.apps.handlers.lifecycle.compact import handle

        with patch("aipass.hooks.apps.handlers.lifecycle.compact.speak"):
            with patch("aipass.hooks.apps.handlers.lifecycle.compact._get_git_info", return_value=None):
                with patch("pathlib.Path.cwd", return_value=MagicMock(parts=("/", "tmp"))):
                    result = handle({})

        assert result["exit_code"] == 0
