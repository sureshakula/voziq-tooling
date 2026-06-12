# ===================AIPASS====================
# META DATA HEADER
# Name: test_runner.py - Unit tests for skills runner
# Date: 2026-03-07
# Version: 1.0.0
# Category: skills/tests
# =============================================

"""Tests for the skills runner module."""

from aipass.skills.apps.modules.runner import run_skill


class TestRunSkillHandler:
    def test_run_system_status_disk(self):
        result = run_skill("system_status", action="disk")
        assert result["success"] is True
        assert "Disk Usage" in result["output"]
        assert result["error"] is None

    def test_run_system_status_memory(self):
        result = run_skill("system_status", action="memory")
        assert result["success"] is True
        assert "Memory" in result["output"]

    def test_run_system_status_uptime(self):
        result = run_skill("system_status", action="uptime")
        assert result["success"] is True
        assert "Uptime" in result["output"]

    def test_run_system_status_processes(self):
        result = run_skill("system_status", action="processes")
        assert result["success"] is True
        assert "processes" in result["output"].lower()

    def test_run_system_status_summary(self):
        result = run_skill("system_status", action="summary")
        assert result["success"] is True
        assert "Disk Usage" in result["output"]
        assert "Memory" in result["output"]

    def test_invalid_action(self):
        result = run_skill("system_status", action="nonexistent")
        assert result["success"] is False
        assert result["error"] is not None

    def test_no_action_lists_actions(self):
        result = run_skill("system_status")
        assert result["success"] is True
        assert "Available actions" in result["output"]

    def test_nonexistent_skill(self):
        result = run_skill("nonexistent_skill_xyz")
        assert result["success"] is False
        assert result["error"] is not None


class TestRunSkillMarkdown:
    def test_run_github_returns_body(self):
        result = run_skill("github")
        assert result["success"] is True
        assert result["output"] is not None
        assert len(result["output"]) > 100
        assert "github" in result["output"].lower()
        assert result["error"] is None

    def test_output_format(self):
        result = run_skill("github")
        assert result["output"].startswith("=== Skill: github ===")


class TestRunSkillReturnContract:
    def test_return_has_required_keys(self):
        result = run_skill("system_status", action="disk")
        assert "success" in result
        assert "output" in result
        assert "error" in result
        # Verify values are correct, not just keys
        assert result["success"] is True
        assert "Disk Usage" in result["output"]
        assert result["error"] is None

    def test_success_result_types(self):
        result = run_skill("system_status", action="disk")
        assert isinstance(result["success"], bool)
        assert isinstance(result["output"], str)
        assert result["error"] is None
        # Content assertions — not just types
        assert result["success"] is True
        assert len(result["output"]) > 0
        assert "Disk Usage" in result["output"]

    def test_failure_result_types(self):
        result = run_skill("nonexistent_skill_xyz")
        assert isinstance(result["success"], bool)
        assert isinstance(result["output"], str)
        assert isinstance(result["error"], str)
        # Content assertions — not just types
        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["output"] == ""
