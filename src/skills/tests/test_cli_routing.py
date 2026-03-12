# ===================AIPASS====================
# META DATA HEADER
# Name: test_cli_routing.py - Unit tests for skills.py CLI routing
# Date: 2026-03-10
# Version: 1.0.0
# Category: skills/tests
# =============================================

"""Tests for the skills entry point CLI routing."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

skills_root = Path(__file__).resolve().parent.parent.parent
if str(skills_root) not in sys.path:
    sys.path.insert(0, str(skills_root))

from skills.apps.skills import handle_command, _parse_extra_args


class TestParseExtraArgs:
    def test_key_value_pairs(self):
        result = _parse_extra_args(["host=localhost", "port=8080"])
        assert result == {"host": "localhost", "port": "8080"}

    def test_positional_args(self):
        result = _parse_extra_args(["foo", "bar"])
        assert result == {"arg0": "foo", "arg1": "bar"}

    def test_mixed_args(self):
        result = _parse_extra_args(["foo", "key=val", "bar"])
        assert result == {"arg0": "foo", "key": "val", "arg1": "bar"}

    def test_empty_args(self):
        result = _parse_extra_args([])
        assert result == {}

    def test_value_with_equals_sign(self):
        """key=value where value itself contains '='."""
        result = _parse_extra_args(["query=a=b"])
        assert result == {"query": "a=b"}


class TestHandleCommand:
    def test_none_command_shows_introspection(self):
        result = handle_command(None)
        assert result is True

    def test_help_command(self):
        result = handle_command("--help")
        assert result is True

    def test_help_alias(self):
        result = handle_command("help")
        assert result is True

    def test_h_flag(self):
        result = handle_command("-h")
        assert result is True

    def test_version_command(self):
        result = handle_command("--version")
        assert result is True

    def test_version_short_flag(self):
        result = handle_command("-V")
        assert result is True

    def test_unknown_command_returns_false(self):
        result = handle_command("bogus_command_xyz")
        assert result is False

    def test_list_command(self):
        result = handle_command("list")
        assert result is True

    def test_info_missing_args_returns_false(self):
        result = handle_command("info")
        assert result is False

    def test_info_with_valid_skill(self):
        result = handle_command("info", ["github"])
        assert result is True

    def test_run_missing_args_returns_false(self):
        result = handle_command("run")
        assert result is False

    def test_run_with_valid_skill(self):
        result = handle_command("run", ["system_status", "disk"])
        assert result is True

    def test_validate_missing_args_returns_false(self):
        result = handle_command("validate")
        assert result is False

    def test_validate_with_valid_skill(self):
        result = handle_command("validate", ["github"])
        assert result is True

    def test_create_missing_args_returns_false(self):
        result = handle_command("create")
        assert result is False
