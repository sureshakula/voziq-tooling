# =================== AIPass ====================
# Name: test_edit_gate_trinity.py
# Version: 1.0.0
# Description: Tests for edit_gate .trinity char-limit check (FPLAN-0270 Phase 4)
# Branch: hooks
# Created: 2026-06-13
# Modified: 2026-06-13
# =============================================

"""Tests for edit_gate .trinity character-limit check (Write tool, Phase 4)."""

import importlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


_TEST_LIMITS_WARN = {
    "enabled": True,
    "enforce": False,
    "entry_types": {
        "key_learnings": {
            "file": "local.json",
            "container": "key_learnings",
            "kind": "dict",
            "field": "value",
            "max_chars": 200,
        },
        "sessions": {
            "file": "local.json",
            "container": "sessions",
            "kind": "list",
            "field": "summary",
            "max_chars": 300,
        },
        "todos": {
            "file": "local.json",
            "container": "todos",
            "kind": "list",
            "field": "task",
            "max_chars": 200,
        },
        "observations": {
            "file": "observations.json",
            "container": "observations",
            "kind": "list",
            "field": "note",
            "max_chars": 600,
        },
    },
}

_TEST_LIMITS_ENFORCE = {**_TEST_LIMITS_WARN, "enforce": True}

_TEST_LIMITS_DISABLED = {**_TEST_LIMITS_WARN, "enabled": False}


def _make_trinity_path(tmp_path, branch="hooks", filename="local.json"):
    """Build a .trinity file path with proper src/aipass/<branch>/.trinity/ structure."""
    trinity_dir = tmp_path / "src" / "aipass" / branch / ".trinity"
    trinity_dir.mkdir(parents=True, exist_ok=True)
    return str(trinity_dir / filename)


def _hook_data(file_path, content, tool_name="Write", cwd=None):
    """Build a hook_data dict for edit_gate.handle()."""
    data = {
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path, "content": content},
    }
    if cwd:
        data["cwd"] = cwd
    return data


def _mock_entry_limits(limits):
    """Create a mock module with controlled limits and real changed_entries."""
    el = importlib.import_module("aipass.memory.apps.handlers.json.entry_limits")
    mock_module = MagicMock()
    mock_module.load_entry_limits.return_value = limits
    mock_module.changed_entries = el.changed_entries
    return mock_module


class TestTrinityWriteClean:
    """Write to .trinity with entries under cap -> allowed."""

    def test_clean_write_local_json(self, tmp_path):
        """All entries under cap in local.json -> allowed."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps(
            {
                "key_learnings": {"learn_1": "short"},
                "sessions": [{"summary": "short session"}],
                "todos": [{"task": "short todo"}],
            }
        )

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_WARN)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_clean_write_observations_json(self, tmp_path):
        """All entries under cap in observations.json -> allowed."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "observations.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"observations": [{"note": "short observation"}]})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_WARN)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0
        assert result["stdout"] == ""


class TestTrinityWriteOverLimitEnforced:
    """Write with over-limit entry + enforce=True -> blocked."""

    def test_block_over_limit_key_learning(self, tmp_path):
        """key_learning value 201 chars vs 200 cap -> blocked."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"learn_1": "x" * 201}})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "key_learnings" in parsed["reason"]
        assert "201" in parsed["reason"]
        assert "200" in parsed["reason"]

    def test_block_over_limit_session_summary(self, tmp_path):
        """Session summary 301 chars vs 300 cap -> blocked."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"sessions": [{"summary": "x" * 301}]})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "sessions" in parsed["reason"]

    def test_block_over_limit_todo(self, tmp_path):
        """Todo task 201 chars vs 200 cap -> blocked."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"todos": [{"task": "x" * 201}]})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "todos" in parsed["reason"]

    def test_block_over_limit_observation(self, tmp_path):
        """Observation note 601 chars vs 600 cap -> blocked."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "observations.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"observations": [{"note": "x" * 601}]})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
        assert "observations" in parsed["reason"]

    def test_block_reason_includes_over_by(self, tmp_path):
        """Block reason includes the +over_by amount."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"k1": "x" * 210}})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        parsed = json.loads(result["stdout"])
        assert "+10" in parsed["reason"]


class TestTrinityWriteOverLimitWarnOnly:
    """Write with over-limit entry + enforce=False -> allowed + warning logged."""

    def test_allow_over_limit_warn_only(self, tmp_path):
        """Over-limit with enforce=False -> exit_code 0, empty stdout."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"learn_1": "x" * 250}})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_WARN)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_warn_logs_over_limit_entries(self, tmp_path, caplog):
        """Over-limit with enforce=False -> warning logged with warn-only message."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"k1": "x" * 250}})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_WARN)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0
        assert "warn only" in caplog.text


class TestTrinityWriteNonTrinity:
    """Write to non-.trinity file -> passes through unchanged."""

    def test_non_trinity_py_passthrough(self):
        """Write to a .py file -> no .trinity check, passes to diagnostics gate."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/apps/test.py",
                    "content": "print('hello')",
                },
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/hooks",
            }
        )
        assert result["exit_code"] == 0

    def test_non_trinity_json_passthrough(self):
        """Write to a non-.trinity .json file -> allowed."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        result = handle(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/home/patrick/Projects/AIPass/src/aipass/hooks/apps/config.json",
                    "content": '{"key": "value"}',
                },
                "cwd": "/home/patrick/Projects/AIPass/src/aipass/hooks",
            }
        )
        assert result["exit_code"] == 0

    def test_trinity_passport_passthrough(self, tmp_path):
        """passport.json is in .trinity but NOT in _TRINITY_MEMORY_FILES."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        trinity_dir = tmp_path / "src" / "aipass" / "hooks" / ".trinity"
        trinity_dir.mkdir(parents=True, exist_ok=True)
        file_path = str(trinity_dir / "passport.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")

        result = handle(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": file_path, "content": '{"identity": {}}'},
                "cwd": cwd,
            }
        )
        assert result["exit_code"] == 0


class TestTrinityWriteFailOpen:
    """Invalid or unparseable content -> fail-open (allowed)."""

    def test_invalid_json_content(self, tmp_path):
        """Non-JSON content -> JSONDecodeError caught, fail-open."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, "not valid json {{{", cwd=cwd))

        assert result["exit_code"] == 0
        assert result["stdout"] == ""

    def test_empty_content(self, tmp_path):
        """Empty content string -> JSONDecodeError caught, fail-open."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, "", cwd=cwd))

        assert result["exit_code"] == 0

    def test_import_failure_fail_open(self, tmp_path):
        """importlib.import_module raises ImportError -> caught, fail-open."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"k1": "x" * 500}})

        with patch("importlib.import_module", side_effect=ImportError("no module")):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0


class TestTrinityWriteCharNotByte:
    """Character vs byte boundary: em-dash is 3 bytes / 1 char."""

    def test_em_dash_at_cap_allowed(self, tmp_path):
        """200 em-dashes = 200 chars (600 bytes) = exactly at cap -> allowed."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"k1": "—" * 200}})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0

    def test_em_dash_over_cap_blocked(self, tmp_path):
        """201 em-dashes = 201 chars (603 bytes) = over cap -> blocked."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"k1": "—" * 201}})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"


class TestTrinityEditMultiEditPassthrough:
    """Edit/MultiEdit to .trinity file -> NOT blocked by Phase 4 check."""

    def test_edit_to_trinity_not_blocked(self, tmp_path):
        """Edit tool to .trinity/local.json -> passes through (Phase 5 scope)."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")

        result = handle(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": file_path,
                    "old_string": "old",
                    "new_string": "x" * 500,
                },
                "cwd": cwd,
            }
        )
        assert result["exit_code"] == 0

    def test_multiedit_to_trinity_not_blocked(self, tmp_path):
        """MultiEdit tool to .trinity/local.json -> passes through (Phase 5 scope)."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")

        result = handle(
            {
                "tool_name": "MultiEdit",
                "tool_input": {
                    "file_path": file_path,
                    "edits": [{"old_string": "a", "new_string": "x" * 500}],
                },
                "cwd": cwd,
            }
        )
        assert result["exit_code"] == 0


class TestTrinityWriteDisabled:
    """Feature disabled via enabled:false -> passthrough."""

    def test_disabled_allows_over_limit(self, tmp_path):
        """enabled=False -> size check skipped, over-limit entry allowed."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")
        content = json.dumps({"key_learnings": {"k1": "x" * 500}})

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_DISABLED)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0


class TestTrinityWriteUnchangedLegacy:
    """Unchanged legacy over-limit entry in Write -> not blocked (rollover-safe)."""

    def test_unchanged_legacy_allowed(self, tmp_path):
        """Legacy over-limit entry unchanged between before/after -> allowed."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")

        existing = {"key_learnings": {"old_fat": "x" * 500}}
        Path(file_path).write_text(json.dumps(existing), encoding="utf-8")

        after = {"key_learnings": {"old_fat": "x" * 500, "new_clean": "short"}}
        content = json.dumps(after)

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 0

    def test_changed_legacy_blocked(self, tmp_path):
        """Legacy entry modified (text changed, still over-limit) -> blocked."""
        from aipass.hooks.apps.handlers.security.edit_gate import handle

        file_path = _make_trinity_path(tmp_path, "hooks", "local.json")
        cwd = str(tmp_path / "src" / "aipass" / "hooks")

        existing = {"key_learnings": {"old_fat": "x" * 500}}
        Path(file_path).write_text(json.dumps(existing), encoding="utf-8")

        after = {"key_learnings": {"old_fat": "y" * 500}}
        content = json.dumps(after)

        with patch("importlib.import_module", return_value=_mock_entry_limits(_TEST_LIMITS_ENFORCE)):
            result = handle(_hook_data(file_path, content, cwd=cwd))

        assert result["exit_code"] == 2
        parsed = json.loads(result["stdout"])
        assert parsed["decision"] == "block"
