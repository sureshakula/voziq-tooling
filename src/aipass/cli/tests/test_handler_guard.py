"""Tests for handlers/__init__.py cross-branch import guard."""

import os
from unittest.mock import patch

from aipass.cli.apps.handlers import _find_real_caller, _extract_branch_name


class TestExtractBranchName:
    def test_extracts_branch_from_aipass_path(self):
        path = "/home/user/Projects/AIPass/src/aipass/drone/apps/modules/core.py"
        assert _extract_branch_name(path) == "drone"

    def test_extracts_cli_branch(self):
        path = "/home/user/Projects/AIPass/src/aipass/cli/apps/modules/display.py"
        assert _extract_branch_name(path) == "cli"

    def test_returns_unknown_for_no_aipass(self):
        path = "/usr/lib/python3/site-packages/something.py"
        assert _extract_branch_name(path) == "unknown"

    def test_returns_unknown_when_aipass_is_last(self):
        path = "/home/user/aipass"
        assert _extract_branch_name(path) == "unknown"


class TestFindRealCaller:
    def test_returns_tuple(self):
        result = _find_real_caller()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_finds_this_test_file(self):
        filepath, import_line = _find_real_caller()
        assert filepath is not None
        assert "test_handler_guard" in filepath


class TestGuardBranchAccess:
    def test_allows_cli_branch_imports(self):
        """Importing from within cli branch should not raise."""
        from aipass.cli.apps.handlers.json import json_handler

        assert json_handler is not None

    def test_debug_guard_env_var(self):
        """AIPASS_DEBUG_GUARD env var enables debug output."""
        with patch.dict(os.environ, {"AIPASS_DEBUG_GUARD": "1"}):
            filepath, _ = _find_real_caller()
            assert filepath is not None
