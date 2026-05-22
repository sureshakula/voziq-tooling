# =================== AIPass ====================
# Name: test_edit_gate.py
# Version: 1.0.0
# Description: Tests for edit_gate security handler
# Branch: hooks
# Created: 2026-05-21
# Modified: 2026-05-21
# =============================================

"""Tests for handlers/security/edit_gate.py."""

import json
from unittest.mock import patch


class TestEditGateHandler:
    def test_allow_normal_edit(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/apps/test.py"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/hooks",
            }
        )
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_block_inbox_write(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/.ai_mail.local/inbox.json"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/hooks",
            }
        )
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "inbox.json" in parsed["reason"]

    def test_block_cross_branch(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/apps/test.py"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
            }
        )
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "Cross-branch" in parsed["reason"]

    def test_allow_trusted_cross_branch(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/apps/test.py"},
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/devpulse",
            }
        )
        assert result["exit_code"] == 0

    def test_block_daemon_cross_branch(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        with patch.dict("os.environ", {"AIPASS_SESSION_TYPE": "daemon"}):
            result = handle(
                {
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/apps/test.py"},
                    "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
                }
            )
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert "daemon" in parsed["reason"]

    def test_allow_daemon_own_branch(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        with patch.dict("os.environ", {"AIPASS_SESSION_TYPE": "daemon"}):
            result = handle(
                {
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "/home/patrick/Projects/AIPass/src/aipass/api/apps/test.py"},
                    "cwd": "/home/patrick/Projects/AIPass/src/aipass/api",
                }
            )
        assert result["exit_code"] == 0

    def test_skip_non_edit_tool(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle(
            {
                "tool_name": "Bash",
                "tool_input": {"file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/.ai_mail.local/inbox.json"},
            }
        )
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_empty_file_path(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle({"tool_name": "Edit", "tool_input": {"file_path": ""}})
        assert result["exit_code"] == 0

    def test_empty_hook_data(self):
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle({})
        assert result["exit_code"] == 0
