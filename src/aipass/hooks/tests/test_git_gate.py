# =================== AIPass ====================
# Name: test_git_gate.py
# Version: 1.0.0
# Description: Tests for git_gate security handler
# Branch: hooks
# Created: 2026-05-21
# Modified: 2026-05-21
# =============================================

"""Tests for handlers/security/git_gate.py."""

import json


class TestGitGateHandler:
    def test_block_raw_git(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "drone" in parsed["reason"]

    def test_block_raw_gh(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr list"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 2

    def test_allow_drone_git(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "drone @git status"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_allow_gh_api(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh api repos/owner/repo/pulls"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 0

    def test_block_edit_settings(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/home/patrick/.claude/settings.json"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"

    def test_allow_edit_settings_from_devpulse(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/home/patrick/.claude/settings.json"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/devpulse",
            }
        )
        assert result["exit_code"] == 0

    def test_block_edit_hooks_dir(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/home/patrick/Projects/AIPass/.claude/hooks/some_hook.py"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 2

    def test_allow_normal_bash(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_git_in_quoted_string(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle(
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'echo "git status"'},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 0

    def test_empty_hook_data(self):
        from aipass.hooks.apps.handlers.security.git_gate import handle

        result = handle({})
        assert result["exit_code"] == 0
