# =================== META ====================
# Name: test_spawn.py
# Description: Test suite for spawn module
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-03-07
# =============================================

"""Tests for the aipass.spawn module."""

import json
import shutil
import pytest
from pathlib import Path

from aipass.spawn import spawn_agent
from aipass.spawn.apps.handlers.metadata import get_branch_name, normalize_branch_name, detect_profile
from aipass.spawn.apps.handlers.placeholders import (
    build_replacements_dict,
    replace_placeholders,
    validate_no_placeholders,
)
from aipass.spawn.apps.handlers.registry import load_registry, add_to_registry, save_registry, get_next_citizen_number


@pytest.fixture
def tmp_agent(tmp_path):
    """Provide a temp path for agent creation and clean up after."""
    agent_path = tmp_path / "test_agent"
    yield agent_path
    if agent_path.exists():
        shutil.rmtree(agent_path)


@pytest.fixture
def tmp_registry(tmp_path):
    """Provide a temp registry path."""
    return tmp_path / "AIPASS_REGISTRY.json"


class TestMetadata:
    def test_get_branch_name(self):
        assert get_branch_name("/some/path/my_agent") == "my_agent"

    def test_normalize_upper(self):
        assert normalize_branch_name("my-agent", "upper") == "MY_AGENT"

    def test_normalize_lower(self):
        assert normalize_branch_name("My-Agent", "lower") == "my_agent"

    def test_detect_profile_default(self):
        assert detect_profile("/tmp/test") == "AIPass Workshop"


class TestPlaceholders:
    def test_build_replacements(self):
        r = build_replacements_dict(Path("/tmp/x"), "my_agent", role="Tester")
        assert r["BRANCHNAME"] == "MY_AGENT"
        assert r["branchname"] == "my_agent"
        assert r["ROLE"] == "Tester"
        assert r["CWD"] == "/tmp/x"

    def test_validate_clean_dir(self, tmp_path):
        (tmp_path / "clean.txt").write_text("no placeholders here")
        issues = validate_no_placeholders(tmp_path)
        assert issues == []

    def test_validate_catches_placeholders(self, tmp_path):
        (tmp_path / "dirty.txt").write_text("Hello {{NAME}}")
        issues = validate_no_placeholders(tmp_path)
        assert len(issues) == 1
        assert "NAME" in issues[0][1]


class TestRegistry:
    def test_load_missing(self, tmp_registry):
        data = load_registry(tmp_registry)
        assert data["metadata"]["total_branches"] == 0
        assert data["branches"] == []

    def test_add_and_load(self, tmp_registry):
        result = add_to_registry(tmp_registry, "TEST", "/tmp/test", "Workshop", "@test", "A test")
        assert result is True
        data = load_registry(tmp_registry)
        assert len(data["branches"]) == 1
        assert data["branches"][0]["name"] == "TEST"

    def test_no_duplicates(self, tmp_registry):
        add_to_registry(tmp_registry, "X", "/tmp/x", "W", "@x")
        result = add_to_registry(tmp_registry, "X", "/tmp/x", "W", "@x")
        assert result is False


class TestSpawnAgent:
    def test_full_spawn(self, tmp_agent, tmp_registry):
        result = spawn_agent(
            str(tmp_agent),
            role="Test Role",
            purpose="Test Purpose",
            registry_path=str(tmp_registry),
        )
        assert result["success"] is True
        assert result["branch_name"] == "TEST_AGENT"
        assert result["files_copied"] > 0
        assert result["registry_updated"] is True
        assert result["validation_issues"] == []

        # Verify key files exist
        assert (tmp_agent / ".trinity" / "passport.json").exists()
        assert (tmp_agent / "DASHBOARD.local.json").exists()
        assert (tmp_agent / "apps" / "test_agent.py").exists()

        # Verify passport content
        passport = json.loads((tmp_agent / ".trinity" / "passport.json").read_text())
        assert passport["branch_info"]["branch_name"] == "TEST_AGENT"
        assert passport["identity"]["role"] == "Test Role"

        # Verify registry
        reg = load_registry(tmp_registry)
        assert len(reg["branches"]) == 1

    def test_target_already_exists(self, tmp_path, tmp_registry):
        existing = tmp_path / "existing"
        existing.mkdir()
        result = spawn_agent(str(existing), registry_path=str(tmp_registry))
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_template_registry_regenerated(self, tmp_agent, tmp_registry):
        spawn_agent(str(tmp_agent), registry_path=str(tmp_registry))
        reg_file = tmp_agent / ".spawn" / ".template_registry.json"
        assert reg_file.exists()
        data = json.loads(reg_file.read_text())
        assert data["metadata"]["generated"] is True
        assert len(data["files"]) > 0


class TestReplacePlaceholders:
    """Tests for replace_placeholders()."""

    def test_basic_replacement(self):
        content = "Hello {{NAME}}, welcome to {{PROJECT}}."
        result = replace_placeholders(content, {"NAME": "Alice", "PROJECT": "AIPass"})
        assert result == "Hello Alice, welcome to AIPass."

    def test_no_placeholders(self):
        content = "No placeholders here."
        result = replace_placeholders(content, {"FOO": "bar"})
        assert result == "No placeholders here."

    def test_multiple_occurrences(self):
        content = "{{X}} and {{X}} again"
        result = replace_placeholders(content, {"X": "val"})
        assert result == "val and val again"

    def test_empty_replacements(self):
        content = "{{STAYS}} intact"
        result = replace_placeholders(content, {})
        assert result == "{{STAYS}} intact"

    def test_value_coercion_to_string(self):
        result = replace_placeholders("number={{N}}", {"N": 42})
        assert result == "number=42"


class TestSaveRegistry:
    """Tests for save_registry()."""

    def test_saves_and_sorts_branches(self, tmp_path):
        reg_path = tmp_path / "TEST_REGISTRY.json"
        data = {
            "metadata": {"version": "1.0.0", "total_branches": 2},
            "branches": [
                {"name": "ZEBRA", "path": "zebra"},
                {"name": "ALPHA", "path": "alpha"},
            ],
        }
        save_registry(reg_path, data)
        saved = json.loads(reg_path.read_text())
        assert saved["branches"][0]["name"] == "ALPHA"
        assert saved["branches"][1]["name"] == "ZEBRA"

    def test_updates_timestamp(self, tmp_path):
        reg_path = tmp_path / "TEST_REGISTRY.json"
        data = {
            "metadata": {"version": "1.0.0", "last_updated": "2020-01-01", "total_branches": 0},
            "branches": [],
        }
        save_registry(reg_path, data)
        saved = json.loads(reg_path.read_text())
        assert saved["metadata"]["last_updated"] != "2020-01-01"

    def test_handles_dict_branches(self, tmp_path):
        reg_path = tmp_path / "TEST_REGISTRY.json"
        data = {
            "metadata": {"version": "1.0.0", "total_branches": 1},
            "branches": {"MY_AGENT": {"name": "MY_AGENT", "path": "my_agent"}},
        }
        save_registry(reg_path, data)
        saved = json.loads(reg_path.read_text())
        assert isinstance(saved["branches"], list)
        assert saved["branches"][0]["name"] == "MY_AGENT"


class TestGetNextCitizenNumber:
    """Tests for get_next_citizen_number()."""

    def test_empty_registry(self, tmp_path):
        reg_path = tmp_path / "TEST_REGISTRY.json"
        reg_path.write_text('{"metadata":{"version":"1.0.0","total_branches":0},"branches":[]}')
        assert get_next_citizen_number(reg_path) == 1

    def test_with_existing_branches(self, tmp_path):
        reg_path = tmp_path / "TEST_REGISTRY.json"
        reg_path.write_text(
            '{"metadata":{"version":"1.0.0","total_branches":2},"branches":[{"name":"A"},{"name":"B"}]}'
        )
        assert get_next_citizen_number(reg_path) == 3

    def test_missing_registry(self, tmp_path):
        reg_path = tmp_path / "NONEXISTENT_REGISTRY.json"
        assert get_next_citizen_number(reg_path) == 1
