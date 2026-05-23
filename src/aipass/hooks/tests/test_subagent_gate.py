# =================== AIPass ====================
# Name: test_subagent_gate.py
# Version: 1.0.0
# Description: Tests for subagent_gate security handler
# Branch: hooks
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/security/subagent_gate.py."""

import json
from unittest.mock import patch, MagicMock

from aipass.hooks.apps.handlers.security.subagent_gate import handle


class TestSubagentGateHandler:
    def test_no_repo_root_allows(self):
        with patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root", return_value=None):
            with patch("aipass.hooks.apps.handlers.security.subagent_gate.speak"):
                result = handle({"cwd": "/tmp/nowhere"})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_no_modified_files_allows(self):
        with patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root", return_value=None):
            with patch("aipass.hooks.apps.handlers.security.subagent_gate.speak"):
                result = handle({"cwd": "/tmp/somewhere"})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    @patch("aipass.hooks.apps.handlers.security.subagent_gate._check_hook_readme_accountability", return_value=None)
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._run_seedgo_checklist", return_value=[])
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._get_modified_py_files")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate.speak")
    def test_modified_files_no_violations_allows(self, mock_speak, mock_root, mock_modified, mock_seedgo, mock_readme):
        from pathlib import Path

        mock_root.return_value = Path("/fake/repo")
        mock_modified.return_value = ["/fake/repo/src/aipass/hooks/apps/test.py"]
        result = handle({"cwd": "/fake/repo/src/aipass/hooks"})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    @patch("aipass.hooks.apps.handlers.security.subagent_gate._check_hook_readme_accountability", return_value=None)
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._run_seedgo_checklist")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._get_modified_py_files")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate.speak")
    def test_violations_blocks(self, mock_speak, mock_root, mock_modified, mock_seedgo, mock_readme):
        from pathlib import Path

        mock_root.return_value = Path("/fake/repo")
        mock_modified.return_value = ["/fake/repo/src/aipass/hooks/apps/bad.py"]
        mock_seedgo.return_value = ["Missing docstring", "No tests"]
        result = handle({"cwd": "/fake/repo/src/aipass/hooks"})
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "Missing docstring" in parsed["reason"]
        assert "No tests" in parsed["reason"]
        assert "bad.py" in parsed["reason"]

    @patch("subprocess.run")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate.speak")
    def test_skip_claude_hooks_from_modified_files(self, mock_speak, mock_run, tmp_path):

        src = tmp_path / "src" / "aipass" / "hooks"
        src.mkdir(parents=True)
        (tmp_path / ".git").mkdir()
        mock_run.return_value = MagicMock(stdout=" M .claude/hooks/something.py\n", returncode=0)
        with patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root", return_value=tmp_path):
            with patch("aipass.hooks.apps.handlers.security.subagent_gate._get_cwd_branch", return_value="hooks"):
                from aipass.hooks.apps.handlers.security.subagent_gate import _get_modified_py_files

                files = _get_modified_py_files(str(src), tmp_path)
        assert files == []

    @patch("subprocess.run")
    def test_skip_claude_hooks_from_seedgo_checks(self, mock_run):
        from pathlib import Path
        from aipass.hooks.apps.handlers.security.subagent_gate import _run_seedgo_checklist

        result = _run_seedgo_checklist("/repo/.claude/hooks/gate.py", Path("/repo"))
        assert result == []
        mock_run.assert_not_called()

    @patch("aipass.hooks.apps.handlers.security.subagent_gate._check_hook_readme_accountability")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._run_seedgo_checklist", return_value=[])
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._get_modified_py_files")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate.speak")
    def test_readme_accountability_advisory(self, mock_speak, mock_root, mock_modified, mock_seedgo, mock_readme):
        from pathlib import Path

        mock_root.return_value = Path("/fake/repo")
        mock_modified.return_value = ["/fake/repo/src/aipass/hooks/apps/clean.py"]
        mock_readme.return_value = (
            "Hook files were modified but .claude/hooks/README.md was not updated. "
            "Consider updating the README to reflect your changes."
        )
        result = handle({"cwd": "/fake/repo/src/aipass/hooks"})
        assert result["exit_code"] == 0
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "allow"
        assert "README" in parsed["reason"]

    def test_empty_hook_data_allows(self):
        with patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root", return_value=None):
            with patch("aipass.hooks.apps.handlers.security.subagent_gate.speak"):
                result = handle({})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    @patch("aipass.hooks.apps.handlers.security.subagent_gate._get_modified_py_files")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate._find_repo_root")
    @patch("aipass.hooks.apps.handlers.security.subagent_gate.speak")
    def test_exception_in_get_modified_allows(self, mock_speak, mock_root, mock_modified):
        from pathlib import Path

        mock_root.return_value = Path("/fake/repo")
        mock_modified.side_effect = RuntimeError("subprocess died")
        result = handle({"cwd": "/fake/repo/src/aipass/hooks"})
        assert result["exit_code"] == 0
        assert result["stdout"] == ""
