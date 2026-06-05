# =================== AIPass ====================
# Name: test_rm_gate.py
# Version: 1.0.0
# Description: Tests for rm_gate security handler
# Branch: hooks
# Created: 2026-06-02
# Modified: 2026-06-02
# =============================================

"""Tests for handlers/security/rm_gate.py."""

import json
from unittest.mock import patch

from aipass.hooks.apps.handlers.security.rm_gate import (
    _clause_has_raw_recursive_rm,
    _has_recursive_flag,
    _split_clauses,
    _strip_quotes,
    handle,
)


class TestStripQuotes:
    def test_double_quotes(self):
        assert _strip_quotes('rm -rf "/tmp/foo bar"') == 'rm -rf ""'

    def test_single_quotes(self):
        assert _strip_quotes("rm -rf '/tmp/foo bar'") == "rm -rf ''"

    def test_escaped_quote_in_double(self):
        assert _strip_quotes(r'echo "he said \"hi\""') == 'echo ""'

    def test_no_quotes(self):
        assert _strip_quotes("rm -rf /tmp/foo") == "rm -rf /tmp/foo"

    def test_mixed_quotes(self):
        result = _strip_quotes("""echo "hello" && rm -rf '/tmp/x'""")
        assert "rm" in result
        assert "/tmp/x" not in result


class TestSplitClauses:
    def test_and_operator(self):
        clauses = _split_clauses("cd /tmp && rm -rf foo")
        assert any("rm" in c for c in clauses)

    def test_semicolon(self):
        clauses = _split_clauses("echo hi; rm -rf /tmp/x")
        assert any("rm" in c for c in clauses)

    def test_pipe(self):
        clauses = _split_clauses("ls | rm -rf /tmp/x")
        assert any("rm" in c for c in clauses)

    def test_or_operator(self):
        clauses = _split_clauses("true || rm -rf /tmp/x")
        assert any("rm" in c for c in clauses)

    def test_subshell(self):
        clauses = _split_clauses("echo $(rm -rf /tmp/x)")
        assert any("rm" in c for c in clauses)

    def test_backtick_subshell(self):
        clauses = _split_clauses("echo `rm -rf /tmp/x`")
        assert any("rm" in c for c in clauses)


class TestHasRecursiveFlag:
    def test_rf(self):
        assert _has_recursive_flag(["-rf", "/tmp/x"]) is True

    def test_fr(self):
        assert _has_recursive_flag(["-fr", "/tmp/x"]) is True

    def test_r_alone(self):
        assert _has_recursive_flag(["-r", "/tmp/x"]) is True

    def test_uppercase_r(self):
        assert _has_recursive_flag(["-R", "/tmp/x"]) is True

    def test_rfv(self):
        assert _has_recursive_flag(["-rfv", "/tmp/x"]) is True

    def test_recursive_long(self):
        assert _has_recursive_flag(["--recursive", "/tmp/x"]) is True

    def test_no_recursive(self):
        assert _has_recursive_flag(["-f", "/tmp/x"]) is False

    def test_after_double_dash(self):
        assert _has_recursive_flag(["--", "-rf", "/tmp/x"]) is False

    def test_empty(self):
        assert _has_recursive_flag([]) is False


class TestClauseHasRawRecursiveRm:
    def test_basic_rm_rf(self):
        assert _clause_has_raw_recursive_rm("rm -rf /tmp/x") is True

    def test_rm_fr(self):
        assert _clause_has_raw_recursive_rm("rm -fr /tmp/x") is True

    def test_rm_rfv(self):
        assert _clause_has_raw_recursive_rm("rm -rfv /tmp/x") is True

    def test_rm_recursive_long(self):
        assert _clause_has_raw_recursive_rm("rm --recursive /tmp/x") is True

    def test_rm_uppercase_r(self):
        assert _clause_has_raw_recursive_rm("rm -R /tmp/x") is True

    def test_drone_rm_not_blocked(self):
        assert _clause_has_raw_recursive_rm("drone rm /tmp/x") is False

    def test_non_recursive_rm(self):
        assert _clause_has_raw_recursive_rm("rm file.txt") is False

    def test_rm_force_only(self):
        assert _clause_has_raw_recursive_rm("rm -f file.txt") is False

    def test_sudo_rm_rf(self):
        assert _clause_has_raw_recursive_rm("sudo rm -rf /tmp/x") is True

    def test_env_prefix_rm_rf(self):
        assert _clause_has_raw_recursive_rm("env VAR=val rm -rf /tmp/x") is True

    def test_absolute_path_rm(self):
        assert _clause_has_raw_recursive_rm("/usr/bin/rm -rf /tmp/x") is True

    def test_empty_clause(self):
        assert _clause_has_raw_recursive_rm("") is False

    def test_whitespace_clause(self):
        assert _clause_has_raw_recursive_rm("   ") is False


class TestHandle:
    CWD = "/home/patrick/Projects/AIPass/src/aipass/hooks"

    def _bash(self, command: str) -> dict:
        return handle({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": self.CWD})

    def _assert_blocked(self, result: dict):
        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "drone rm" in parsed["reason"]

    def _assert_allowed(self, result: dict):
        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_block_rm_rf(self):
        self._assert_blocked(self._bash("rm -rf /tmp/x"))

    def test_block_rm_fr(self):
        self._assert_blocked(self._bash("rm -fr /tmp/x"))

    def test_block_rm_rfv(self):
        self._assert_blocked(self._bash("rm -rfv /tmp/x"))

    def test_block_rm_recursive_long(self):
        self._assert_blocked(self._bash("rm --recursive /tmp/x"))

    def test_block_rm_uppercase_r(self):
        self._assert_blocked(self._bash("rm -R /tmp/x"))

    def test_block_rm_r(self):
        self._assert_blocked(self._bash("rm -r /tmp/x"))

    def test_allow_drone_rm(self):
        self._assert_allowed(self._bash("drone rm /tmp/x"))

    def test_allow_non_recursive_rm(self):
        self._assert_allowed(self._bash("rm file.txt"))

    def test_allow_rm_force_only(self):
        self._assert_allowed(self._bash("rm -f file.txt"))

    def test_block_compound_cd_and_rm(self):
        self._assert_blocked(self._bash("cd /etc && rm -rf ."))

    def test_block_compound_semicolon(self):
        self._assert_blocked(self._bash("echo hi; rm -rf /tmp/x"))

    def test_block_subshell_rm(self):
        self._assert_blocked(self._bash("echo $(rm -rf /tmp/x)"))

    def test_block_sudo_rm_rf(self):
        self._assert_blocked(self._bash("sudo rm -rf /tmp/x"))

    def test_block_absolute_path_rm(self):
        self._assert_blocked(self._bash("/usr/bin/rm -rf /tmp/x"))

    def test_rm_in_quoted_string_allowed(self):
        self._assert_allowed(self._bash('echo "rm -rf /tmp/x"'))

    def test_rm_in_single_quoted_string_allowed(self):
        self._assert_allowed(self._bash("echo 'rm -rf /tmp/x'"))

    def test_non_bash_tool_allowed(self):
        result = handle({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x"}, "cwd": self.CWD})
        self._assert_allowed(result)

    def test_empty_command_allowed(self):
        self._assert_allowed(self._bash(""))

    def test_empty_hook_data(self):
        result = handle({})
        assert result["exit_code"] == 0

    def test_no_tool_input(self):
        result = handle({"tool_name": "Bash"})
        assert result["exit_code"] == 0

    @patch("aipass.hooks.apps.handlers.security.rm_gate.logger")
    def test_exception_allows(self, mock_logger):
        result = handle({"tool_name": "Bash", "tool_input": None, "cwd": self.CWD})
        assert result["exit_code"] == 0
        mock_logger.info.assert_called()

    def test_block_variable_target(self):
        self._assert_blocked(self._bash("rm -rf $DIR"))

    def test_block_multiple_targets(self):
        self._assert_blocked(self._bash("rm -rf /tmp/a /tmp/b"))
