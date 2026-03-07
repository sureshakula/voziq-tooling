# ===================AIPASS====================
# META DATA HEADER
# Name: test_validator.py - Unit tests for skills validator
# Date: 2026-03-07
# Version: 1.0.0
# Category: skills/tests
# =============================================

"""Tests for the skills validator handler."""

import sys
from pathlib import Path

import pytest

skills_root = Path(__file__).resolve().parent.parent.parent
if str(skills_root) not in sys.path:
    sys.path.insert(0, str(skills_root))

from skills.apps.handlers.validator import validate_skill


class TestValidateSkill:
    def test_no_requirements(self):
        result = validate_skill({})
        assert result["valid"] is True
        assert result["missing_pip"] == []
        assert result["missing_bins"] == []
        assert result["missing_config"] == []

    def test_empty_requirements(self):
        result = validate_skill({"requires": {"pip": [], "bins": [], "config": []}})
        assert result["valid"] is True

    def test_installed_pip_package(self):
        # sys is always available
        result = validate_skill({"requires": {"pip": ["sys"]}})
        assert result["valid"] is True
        assert result["missing_pip"] == []

    def test_missing_pip_package(self):
        result = validate_skill({"requires": {"pip": ["nonexistent_pkg_xyz_123"]}})
        assert result["valid"] is False
        assert "nonexistent_pkg_xyz_123" in result["missing_pip"]

    def test_available_binary(self):
        # python3 should be on PATH
        result = validate_skill({"requires": {"bins": ["python3"]}})
        assert result["valid"] is True
        assert result["missing_bins"] == []

    def test_missing_binary(self):
        result = validate_skill({"requires": {"bins": ["nonexistent_bin_xyz"]}})
        assert result["valid"] is False
        assert "nonexistent_bin_xyz" in result["missing_bins"]

    def test_missing_config(self):
        result = validate_skill({"requires": {"config": ["NONEXISTENT_VAR_XYZ"]}})
        assert result["valid"] is False
        assert "NONEXISTENT_VAR_XYZ" in result["missing_config"]

    def test_set_config(self):
        import os
        os.environ["_TEST_SKILLS_VAR"] = "value"
        try:
            result = validate_skill({"requires": {"config": ["_TEST_SKILLS_VAR"]}})
            assert result["valid"] is True
            assert result["missing_config"] == []
        finally:
            del os.environ["_TEST_SKILLS_VAR"]

    def test_mixed_pass_fail(self):
        result = validate_skill({
            "requires": {
                "pip": ["sys"],
                "bins": ["nonexistent_bin_xyz"],
                "config": [],
            }
        })
        assert result["valid"] is False
        assert result["missing_pip"] == []
        assert "nonexistent_bin_xyz" in result["missing_bins"]

    def test_return_structure(self):
        result = validate_skill({})
        assert "valid" in result
        assert "missing_pip" in result
        assert "missing_bins" in result
        assert "missing_config" in result
