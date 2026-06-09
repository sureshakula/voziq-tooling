# =================== AIPass ====================
# Name: test_rollover.py
# Version: 1.0.0
# Description: Tests for rollover lifecycle handler
# Branch: hooks
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/lifecycle/rollover.py."""

import json
from unittest.mock import patch, MagicMock


class TestRolloverHandler:
    def test_no_repo_root_returns_empty(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import handle

        with patch("aipass.hooks.apps.handlers.lifecycle.rollover._find_repo_root", return_value=None):
            result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""
        assert "sound" not in result

    def test_no_overdue_returns_empty(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import handle

        with patch("aipass.hooks.apps.handlers.lifecycle.rollover._find_repo_root", return_value=MagicMock()):
            with patch("aipass.hooks.apps.handlers.lifecycle.rollover._find_overdue", return_value=[]):
                result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""
        assert "sound" not in result

    def test_overdue_triggers_rollover(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import handle

        with patch("aipass.hooks.apps.handlers.lifecycle.rollover._find_repo_root", return_value=MagicMock()):
            with patch(
                "aipass.hooks.apps.handlers.lifecycle.rollover._find_overdue",
                return_value=[("devpulse", "local", "21/20 sessions")],
            ):
                with patch("aipass.hooks.apps.handlers.lifecycle.rollover._run_rollover", return_value=(True, "ok")):
                    result = handle({})

        assert result["exit_code"] == 0
        assert result["sound"] == "pre compact rollover"

    def test_check_file_v2_sessions_overdue(self, tmp_path):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _check_file

        f = tmp_path / "local.json"
        f.write_text(
            json.dumps(
                {
                    "document_metadata": {"limits": {"max_sessions": 5}},
                    "sessions": [{"id": i} for i in range(6)],
                }
            ),
            encoding="utf-8",
        )

        overdue, reason = _check_file(f)
        assert overdue
        assert "6/5" in reason

    def test_check_file_v2_not_overdue(self, tmp_path):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _check_file

        f = tmp_path / "local.json"
        f.write_text(
            json.dumps(
                {
                    "document_metadata": {"limits": {"max_sessions": 20}},
                    "sessions": [{"id": i} for i in range(5)],
                }
            ),
            encoding="utf-8",
        )

        overdue, _ = _check_file(f)
        assert not overdue

    def test_check_file_v1_line_count(self, tmp_path):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _check_file

        f = tmp_path / "obs.json"
        content = {"document_metadata": {"limits": {"max_lines": 10}}}
        text = json.dumps(content, indent=2)
        lines_needed = 10 - text.count("\n")
        text += "\n" * lines_needed
        f.write_text(text, encoding="utf-8")

        overdue, reason = _check_file(f)
        assert overdue
        assert "lines" in reason

    def test_check_file_missing(self, tmp_path):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _check_file

        overdue, _ = _check_file(tmp_path / "nonexistent.json")
        assert not overdue
