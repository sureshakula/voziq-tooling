# =================== AIPass ====================
# Name: test_global_loader.py
# Version: 1.0.0
# Description: Tests for global_loader prompt handler
# Branch: hooks
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/prompt/global_loader.py."""

from unittest.mock import patch


class TestGlobalLoaderHandler:
    def test_loads_global_prompt(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.global_loader import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        prompt = aipass_dir / "aipass_global_prompt.md"
        prompt.write_text("# AIPass Global\nContext here", encoding="utf-8")

        with patch("aipass.hooks.apps.handlers.prompt.global_loader.speak"):
            with patch.dict("os.environ", {"AIPASS_HOME": str(tmp_path)}):
                result = handle({})

        assert result["exit_code"] == 0
        assert "AIPass Global" in result["stdout"]
        assert "Context here" in result["stdout"]

    def test_returns_empty_when_no_aipass_home(self):
        from aipass.hooks.apps.handlers.prompt.global_loader import handle

        with patch("aipass.hooks.apps.handlers.prompt.global_loader.speak"):
            with patch.dict("os.environ", {}, clear=True):
                result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_returns_empty_when_file_missing(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.global_loader import handle

        with patch("aipass.hooks.apps.handlers.prompt.global_loader.speak"):
            with patch.dict("os.environ", {"AIPASS_HOME": str(tmp_path)}):
                result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_empty_hook_data(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.global_loader import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        (aipass_dir / "aipass_global_prompt.md").write_text("content", encoding="utf-8")

        with patch("aipass.hooks.apps.handlers.prompt.global_loader.speak"):
            with patch.dict("os.environ", {"AIPASS_HOME": str(tmp_path)}):
                result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == "content"
