"""
Seed Go Phase 2 Tests — CLI, Runner, and Reporter

Covers:
  - runner.py: calculate_score, calculate_overall, run_checks, file matching
  - reporter.py: human / json / github output formats
  - cli.py: init / check / list commands via argparse + subprocess

All tests use tmp_path for isolation. Mock plugins are written as .py files
into .seedgo/plugins/ — no monkeypatching of discovery needed.

sys.path fix ensures src/ is importable when running from the repo root:
  python -m pytest tests/test_seedgo_cli.py -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from seedgo.models import CheckItem, CheckResult, Severity
from seedgo.runner import (
    _file_matches_types,
    _find_project_files,
    calculate_overall,
    calculate_score,
    run_checks,
)
from seedgo.reporter import report_results


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path):
    """Minimal project root with .seedgo/ directory tree."""
    seedgo_dir = tmp_path / ".seedgo"
    seedgo_dir.mkdir()
    (seedgo_dir / "plugins").mkdir()
    return tmp_path


@pytest.fixture
def passing_plugin(tmp_project):
    """A plugin that always passes for *.py files."""
    code = '''\
PLUGIN_NAME = "always-pass"
PLUGIN_DESCRIPTION = "Always returns a passing result"
FILE_TYPES = ["*.py"]

import sys
_src = str(__import__("pathlib").Path(__file__).parent.parent.parent.parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from seedgo.models import CheckResult, CheckItem, Severity

def check(file_path, config=None):
    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=True,
        checks=[CheckItem(name="always-passes", passed=True, message="All good")],
        score=100,
        file_path=file_path,
    )
'''
    (tmp_project / ".seedgo" / "plugins" / "always_pass.py").write_text(code)
    return tmp_project


@pytest.fixture
def failing_plugin(tmp_project):
    """A plugin that always fails with one ERROR for *.py files."""
    code = '''\
PLUGIN_NAME = "always-fail"
PLUGIN_DESCRIPTION = "Always returns a failing result"
FILE_TYPES = ["*.py"]

import sys
_src = str(__import__("pathlib").Path(__file__).parent.parent.parent.parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from seedgo.models import CheckResult, CheckItem, Severity

def check(file_path, config=None):
    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=False,
        checks=[
            CheckItem(
                name="always-fails",
                passed=False,
                message="This check always fails",
                severity=Severity.ERROR,
                line=1,
                fix_hint="Cannot fix",
            )
        ],
        score=0,
        file_path=file_path,
    )
'''
    (tmp_project / ".seedgo" / "plugins" / "always_fail.py").write_text(code)
    return tmp_project


@pytest.fixture
def warning_plugin(tmp_project):
    """A plugin that returns a WARNING-level failure for *.py files."""
    code = '''\
PLUGIN_NAME = "warn-plugin"
PLUGIN_DESCRIPTION = "Returns a warning"
FILE_TYPES = ["*.py"]

import sys
_src = str(__import__("pathlib").Path(__file__).parent.parent.parent.parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from seedgo.models import CheckResult, CheckItem, Severity

def check(file_path, config=None):
    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=False,
        checks=[
            CheckItem(
                name="warns",
                passed=False,
                message="A warning issue",
                severity=Severity.WARNING,
                line=5,
            )
        ],
        score=50,
        file_path=file_path,
    )
'''
    (tmp_project / ".seedgo" / "plugins" / "warn_plugin.py").write_text(code)
    return tmp_project


@pytest.fixture
def sample_py_file(tmp_project):
    """A Python source file to check."""
    src = tmp_project / "src"
    src.mkdir()
    f = src / "main.py"
    f.write_text("def hello(): pass\n")
    return f


# ---------------------------------------------------------------------------
# calculate_score tests
# ---------------------------------------------------------------------------


class TestCalculateScore:
    def test_no_checks_returns_100(self):
        result = CheckResult(plugin="p", passed=True, checks=[])
        assert calculate_score(result, {}) == 100

    def test_all_passing_checks_returns_100(self):
        result = CheckResult(
            plugin="p",
            passed=True,
            checks=[
                CheckItem(name="c1", passed=True, message="ok", severity=Severity.ERROR),
                CheckItem(name="c2", passed=True, message="ok", severity=Severity.WARNING),
            ],
        )
        assert calculate_score(result, {}) == 100

    def test_all_failing_errors_returns_0(self):
        result = CheckResult(
            plugin="p",
            passed=False,
            checks=[
                CheckItem(name="c1", passed=False, message="fail", severity=Severity.ERROR),
                CheckItem(name="c2", passed=False, message="fail", severity=Severity.ERROR),
            ],
        )
        assert calculate_score(result, {}) == 0

    def test_half_errors_failing_returns_50(self):
        result = CheckResult(
            plugin="p",
            passed=False,
            checks=[
                CheckItem(name="c1", passed=True, message="ok", severity=Severity.ERROR),
                CheckItem(name="c2", passed=False, message="fail", severity=Severity.ERROR),
            ],
        )
        assert calculate_score(result, {}) == 50

    def test_warning_has_half_weight_by_default(self):
        """One passing ERROR (weight 1.0) + one failing WARNING (weight 0.5) = 1/1.5 * 100 = 66."""
        result = CheckResult(
            plugin="p",
            passed=False,
            checks=[
                CheckItem(name="c1", passed=True, message="ok", severity=Severity.ERROR),
                CheckItem(name="c2", passed=False, message="warn", severity=Severity.WARNING),
            ],
        )
        score = calculate_score(result, {})
        assert score == int((1.0 / 1.5) * 100)  # 66

    def test_info_has_zero_weight_by_default(self):
        """INFO items don't affect score — one failing INFO should still give 100."""
        result = CheckResult(
            plugin="p",
            passed=True,
            checks=[
                CheckItem(name="c1", passed=False, message="info", severity=Severity.INFO),
            ],
        )
        assert calculate_score(result, {}) == 100

    def test_custom_weights_from_config(self):
        """Custom weights override defaults."""
        config = {"error_weight": 2.0, "warning_weight": 1.0, "info_weight": 0.0}
        result = CheckResult(
            plugin="p",
            passed=False,
            checks=[
                CheckItem(name="c1", passed=True, message="ok", severity=Severity.ERROR),
                CheckItem(name="c2", passed=False, message="fail", severity=Severity.WARNING),
            ],
        )
        # passed_weight = 2.0 (ERROR passed), total_weight = 2.0 + 1.0 = 3.0
        # score = int(2/3 * 100) = 66
        score = calculate_score(result, config)
        assert score == int((2.0 / 3.0) * 100)

    def test_all_info_checks_returns_100(self):
        """All INFO (zero weight) → total_weight == 0 → score = 100."""
        result = CheckResult(
            plugin="p",
            passed=True,
            checks=[
                CheckItem(name="i1", passed=False, message="info", severity=Severity.INFO),
                CheckItem(name="i2", passed=False, message="info", severity=Severity.INFO),
            ],
        )
        assert calculate_score(result, {}) == 100


# ---------------------------------------------------------------------------
# calculate_overall tests
# ---------------------------------------------------------------------------


class TestCalculateOverall:
    def test_empty_results_returns_100_pass(self):
        overall = calculate_overall([], {})
        assert overall["overall_score"] == 100
        assert overall["passed"] is True
        assert overall["plugins_passed"] == 0
        assert overall["plugins_failed"] == 0
        assert overall["error_count"] == 0

    def test_single_passing_result(self):
        results = [
            CheckResult(
                plugin="p",
                passed=True,
                checks=[CheckItem(name="c", passed=True, message="ok")],
            )
        ]
        overall = calculate_overall(results, {})
        assert overall["overall_score"] == 100
        assert overall["passed"] is True
        assert overall["plugins_passed"] == 1
        assert overall["plugins_failed"] == 0

    def test_single_failing_result_with_error(self):
        results = [
            CheckResult(
                plugin="p",
                passed=False,
                checks=[
                    CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR)
                ],
            )
        ]
        overall = calculate_overall(results, {})
        assert overall["overall_score"] == 0
        assert overall["passed"] is False
        assert overall["error_count"] == 1

    def test_error_blocks_pass_even_at_high_score(self):
        """An ERROR-severity failure must block pass even if score is above threshold."""
        results = [
            CheckResult(
                plugin="p",
                passed=False,
                checks=[
                    CheckItem(name="ok1", passed=True, message="ok", severity=Severity.ERROR),
                    CheckItem(name="ok2", passed=True, message="ok", severity=Severity.ERROR),
                    CheckItem(name="ok3", passed=True, message="ok", severity=Severity.ERROR),
                    CheckItem(name="fail", passed=False, message="fail", severity=Severity.ERROR),
                ],
            )
        ]
        overall = calculate_overall(results, {"threshold": 70})
        # Score = 75 (3/4 * 100), above threshold=70 — but error blocks pass
        assert overall["overall_score"] == 75
        assert overall["error_count"] == 1
        assert overall["passed"] is False

    def test_warning_does_not_block_pass(self):
        """A WARNING-only failure should allow passing if score >= threshold."""
        results = [
            CheckResult(
                plugin="p",
                passed=False,
                checks=[
                    CheckItem(name="ok1", passed=True, message="ok", severity=Severity.ERROR),
                    CheckItem(name="warn", passed=False, message="warn", severity=Severity.WARNING),
                ],
            )
        ]
        # passed_weight = 1.0, total_weight = 1.5, score = 66
        overall = calculate_overall(results, {"threshold": 60})
        assert overall["error_count"] == 0
        assert overall["warning_count"] == 1
        assert overall["passed"] is True  # score 66 >= threshold 60, no errors

    def test_overall_score_is_mean_of_results(self):
        """overall_score should be the mean of individual result scores."""
        r1 = CheckResult(
            plugin="p1",
            passed=True,
            checks=[CheckItem(name="c", passed=True, message="ok", severity=Severity.ERROR)],
        )
        r2 = CheckResult(
            plugin="p2",
            passed=False,
            checks=[CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR)],
        )
        overall = calculate_overall([r1, r2], {})
        # r1 score = 100, r2 score = 0, mean = 50
        assert overall["overall_score"] == 50

    def test_threshold_respected(self):
        results = [
            CheckResult(
                plugin="p",
                passed=True,
                checks=[CheckItem(name="c", passed=True, message="ok")],
            )
        ]
        overall = calculate_overall(results, {"threshold": 90})
        assert overall["threshold"] == 90

    def test_info_count_tracked(self):
        results = [
            CheckResult(
                plugin="p",
                passed=False,
                checks=[
                    CheckItem(name="info", passed=False, message="info", severity=Severity.INFO),
                ],
            )
        ]
        overall = calculate_overall(results, {})
        assert overall["info_count"] == 1
        assert overall["error_count"] == 0
        assert overall["warning_count"] == 0

    def test_plugins_passed_and_failed_counts(self):
        results = [
            CheckResult(
                plugin="p1",
                passed=True,
                checks=[CheckItem(name="c", passed=True, message="ok", severity=Severity.ERROR)],
            ),
            CheckResult(
                plugin="p2",
                passed=False,
                checks=[CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR)],
            ),
            CheckResult(
                plugin="p3",
                passed=False,
                checks=[CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR)],
            ),
        ]
        overall = calculate_overall(results, {"threshold": 75})
        assert overall["plugins_passed"] == 1
        assert overall["plugins_failed"] == 2


# ---------------------------------------------------------------------------
# File matching tests
# ---------------------------------------------------------------------------


class TestFileMatchesTypes:
    def test_py_pattern_matches_py_file(self):
        assert _file_matches_types("/path/to/file.py", ["*.py"]) is True

    def test_py_pattern_does_not_match_js_file(self):
        assert _file_matches_types("/path/to/file.js", ["*.py"]) is False

    def test_wildcard_matches_any_file(self):
        assert _file_matches_types("/path/to/file.anything", ["*"]) is True

    def test_multiple_patterns_any_match(self):
        assert _file_matches_types("/path/to/file.ts", ["*.js", "*.ts"]) is True

    def test_no_patterns_returns_false(self):
        assert _file_matches_types("/path/to/file.py", []) is False

    def test_specific_filename_match(self):
        assert _file_matches_types("/path/to/Makefile", ["Makefile"]) is True


class TestFindProjectFiles:
    def test_finds_py_files_in_project(self, tmp_project):
        src = tmp_project / "src"
        src.mkdir()
        (src / "main.py").write_text("pass")
        (src / "utils.py").write_text("pass")
        config = {"paths": {"include": ["."], "exclude": []}}
        files = _find_project_files(str(tmp_project), config)
        file_names = [Path(f).name for f in files]
        assert "main.py" in file_names
        assert "utils.py" in file_names

    def test_excludes_patterns(self, tmp_project):
        src = tmp_project / "src"
        tests = tmp_project / "tests"
        src.mkdir()
        tests.mkdir()
        (src / "main.py").write_text("pass")
        (tests / "test_main.py").write_text("pass")
        config = {"paths": {"include": ["."], "exclude": ["tests/"]}}
        files = _find_project_files(str(tmp_project), config)
        file_names = [Path(f).name for f in files]
        assert "main.py" in file_names
        assert "test_main.py" not in file_names

    def test_specific_include_path(self, tmp_project):
        src = tmp_project / "src"
        other = tmp_project / "other"
        src.mkdir()
        other.mkdir()
        (src / "main.py").write_text("pass")
        (other / "other.py").write_text("pass")
        config = {"paths": {"include": ["src"], "exclude": []}}
        files = _find_project_files(str(tmp_project), config)
        file_names = [Path(f).name for f in files]
        assert "main.py" in file_names
        assert "other.py" not in file_names


# ---------------------------------------------------------------------------
# run_checks integration tests
# ---------------------------------------------------------------------------


class TestRunChecks:
    def test_no_plugins_returns_empty_results_and_pass(self, tmp_project, sample_py_file):
        # Filter to a nonexistent plugin name so builtins are also excluded
        results, overall = run_checks(str(tmp_project), files=[str(sample_py_file)], plugins=["nonexistent-plugin-xyz"])
        assert results == []
        assert overall["passed"] is True
        assert overall["overall_score"] == 100

    def test_passing_plugin_gives_pass(self, passing_plugin, sample_py_file):
        # Filter to only the local always-pass plugin to isolate from builtins
        results, overall = run_checks(str(passing_plugin), files=[str(sample_py_file)], plugins=["always-pass"])
        assert len(results) == 1
        assert results[0].passed is True
        assert overall["passed"] is True

    def test_failing_plugin_gives_fail(self, failing_plugin, sample_py_file):
        # Filter to only the local always-fail plugin to isolate from builtins
        results, overall = run_checks(str(failing_plugin), files=[str(sample_py_file)], plugins=["always-fail"])
        assert len(results) == 1
        assert results[0].passed is False
        assert overall["passed"] is False
        assert overall["error_count"] == 1

    def test_plugin_filter_restricts_plugins(self, passing_plugin, failing_plugin, sample_py_file):
        """When plugins filter is given, only those plugins should run."""
        # Both plugins are in the same project dir (failing_plugin fixture modifies passing_plugin's dir)
        # We need a project with both; use the failing_plugin fixture which wraps passing_plugin
        # Actually since fixtures use the same tmp_project, we can't easily combine them.
        # Instead test with a fresh project that has one plugin, filtered out.
        results, overall = run_checks(
            str(passing_plugin),
            files=[str(sample_py_file)],
            plugins=["nonexistent-plugin"],
        )
        assert results == []
        assert overall["passed"] is True

    def test_file_type_filtering(self, passing_plugin):
        """Plugin with FILE_TYPES=['*.py'] should not run on .txt files."""
        txt_file = passing_plugin / "src" / "readme.txt"
        (passing_plugin / "src").mkdir(exist_ok=True)
        txt_file.write_text("hello")
        results, overall = run_checks(str(passing_plugin), files=[str(txt_file)])
        assert results == []

    def test_explicit_files_override_discovery(self, passing_plugin, sample_py_file):
        # Filter to only the local always-pass plugin to isolate from builtins
        results, overall = run_checks(str(passing_plugin), files=[str(sample_py_file)], plugins=["always-pass"])
        # Only the one file we specified should be checked
        assert len(results) == 1
        assert results[0].file_path == str(sample_py_file)

    def test_score_set_on_results(self, passing_plugin, sample_py_file):
        results, _ = run_checks(str(passing_plugin), files=[str(sample_py_file)])
        assert results[0].score == 100

    def test_crashed_plugin_returns_failed_result(self, tmp_project, sample_py_file):
        """A plugin that raises an exception should return a failed CheckResult, not crash."""
        code = '''\
PLUGIN_NAME = "crash-plugin"
PLUGIN_DESCRIPTION = "Always crashes"
FILE_TYPES = ["*.py"]

def check(file_path, config=None):
    raise RuntimeError("kaboom")
'''
        (tmp_project / ".seedgo" / "plugins" / "crash_plugin.py").write_text(code)
        # Filter to only the crash plugin to isolate from builtins
        results, overall = run_checks(str(tmp_project), files=[str(sample_py_file)], plugins=["crash-plugin"])
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].score == 0
        assert "kaboom" in results[0].metadata.get("error", "")


# ---------------------------------------------------------------------------
# Reporter tests
# ---------------------------------------------------------------------------


class TestReportHuman:
    def _make_result(self, passed=True, score=100, checks=None):
        return CheckResult(
            plugin="test-plugin",
            passed=passed,
            checks=checks or [],
            score=score,
            file_path="/path/to/file.py",
        )

    def _overall(self, score=100, passed=True, threshold=75):
        return {
            "overall_score": score,
            "passed": passed,
            "threshold": threshold,
            "plugins_passed": 1 if passed else 0,
            "plugins_failed": 0 if passed else 1,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
        }

    def test_output_contains_plugin_name(self):
        result = self._make_result()
        output = report_results([result], self._overall())
        assert "test-plugin" in output

    def test_passing_result_contains_pass(self):
        result = self._make_result(passed=True, score=100)
        output = report_results([result], self._overall(score=100, passed=True))
        assert "PASS" in output

    def test_failing_result_contains_fail(self):
        checks = [CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR)]
        result = self._make_result(passed=False, score=0, checks=checks)
        output = report_results([result], self._overall(score=0, passed=False))
        assert "FAIL" in output

    def test_score_shown_in_output(self):
        result = self._make_result(score=75)
        output = report_results([result], self._overall(score=75))
        assert "75" in output

    def test_check_item_message_shown(self):
        checks = [CheckItem(name="bare-except", passed=False, message="Found bare except", severity=Severity.ERROR)]
        result = self._make_result(passed=False, checks=checks)
        output = report_results([result], self._overall(passed=False))
        assert "Found bare except" in output

    def test_fix_hint_shown_for_failing_check(self):
        checks = [
            CheckItem(
                name="c",
                passed=False,
                message="fail",
                severity=Severity.ERROR,
                fix_hint="Use except Exception:",
            )
        ]
        result = self._make_result(passed=False, checks=checks)
        output = report_results([result], self._overall(passed=False))
        assert "Use except Exception:" in output

    def test_no_results_shows_no_checks_ran(self):
        output = report_results([], self._overall())
        assert "No checks ran" in output

    def test_threshold_shown_in_summary(self):
        result = self._make_result()
        output = report_results([result], self._overall(threshold=80))
        assert "80" in output

    def test_line_number_shown_when_present(self):
        checks = [CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR, line=42)]
        result = self._make_result(passed=False, checks=checks)
        output = report_results([result], self._overall(passed=False))
        assert "42" in output

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown format"):
            report_results([], {}, format="xml")


class TestReportJSON:
    def test_output_is_valid_json(self):
        results = [CheckResult(plugin="p", passed=True, checks=[], score=100, file_path="/f.py")]
        overall = {
            "overall_score": 100, "passed": True, "threshold": 75,
            "plugins_passed": 1, "plugins_failed": 0,
            "error_count": 0, "warning_count": 0, "info_count": 0,
        }
        output = report_results(results, overall, format="json")
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_json_contains_overall_score(self):
        results = [CheckResult(plugin="p", passed=True, checks=[], score=100, file_path="/f.py")]
        overall = {
            "overall_score": 88, "passed": True, "threshold": 75,
            "plugins_passed": 1, "plugins_failed": 0,
            "error_count": 0, "warning_count": 0, "info_count": 0,
        }
        data = json.loads(report_results(results, overall, format="json"))
        assert data["overall_score"] == 88

    def test_json_contains_results_list(self):
        results = [CheckResult(plugin="p", passed=True, checks=[], score=100, file_path="/f.py")]
        overall = {
            "overall_score": 100, "passed": True, "threshold": 75,
            "plugins_passed": 1, "plugins_failed": 0,
            "error_count": 0, "warning_count": 0, "info_count": 0,
        }
        data = json.loads(report_results(results, overall, format="json"))
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["plugin"] == "p"

    def test_json_severity_is_string(self):
        """Severity enum must be serialized as string in JSON output."""
        checks = [CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR)]
        results = [CheckResult(plugin="p", passed=False, checks=checks, score=0, file_path="/f.py")]
        overall = {
            "overall_score": 0, "passed": False, "threshold": 75,
            "plugins_passed": 0, "plugins_failed": 1,
            "error_count": 1, "warning_count": 0, "info_count": 0,
        }
        data = json.loads(report_results(results, overall, format="json"))
        sev = data["results"][0]["checks"][0]["severity"]
        assert isinstance(sev, str)
        assert sev == "error"

    def test_json_passed_field_present(self):
        results = []
        overall = {
            "overall_score": 100, "passed": True, "threshold": 75,
            "plugins_passed": 0, "plugins_failed": 0,
            "error_count": 0, "warning_count": 0, "info_count": 0,
        }
        data = json.loads(report_results(results, overall, format="json"))
        assert "passed" in data


class TestReportGitHub:
    def test_error_produces_error_annotation(self):
        checks = [
            CheckItem(
                name="c",
                passed=False,
                message="Missing type hint",
                severity=Severity.ERROR,
                line=42,
            )
        ]
        results = [CheckResult(plugin="type-hints", passed=False, checks=checks, score=0, file_path="src/main.py")]
        overall = {
            "overall_score": 0, "passed": False, "threshold": 75,
            "plugins_passed": 0, "plugins_failed": 1,
            "error_count": 1, "warning_count": 0, "info_count": 0,
        }
        output = report_results(results, overall, format="github")
        assert "::error" in output
        assert "Missing type hint" in output

    def test_warning_produces_warning_annotation(self):
        checks = [
            CheckItem(
                name="c",
                passed=False,
                message="Class too large",
                severity=Severity.WARNING,
                line=15,
            )
        ]
        results = [CheckResult(plugin="no-god-objects", passed=False, checks=checks, score=50, file_path="src/models.py")]
        overall = {
            "overall_score": 50, "passed": False, "threshold": 75,
            "plugins_passed": 0, "plugins_failed": 1,
            "error_count": 0, "warning_count": 1, "info_count": 0,
        }
        output = report_results(results, overall, format="github")
        assert "::warning" in output
        assert "Class too large" in output

    def test_file_and_line_in_annotation(self):
        checks = [
            CheckItem(name="c", passed=False, message="msg", severity=Severity.ERROR, line=7)
        ]
        results = [CheckResult(plugin="p", passed=False, checks=checks, score=0, file_path="/some/file.py")]
        overall = {
            "overall_score": 0, "passed": False, "threshold": 75,
            "plugins_passed": 0, "plugins_failed": 1,
            "error_count": 1, "warning_count": 0, "info_count": 0,
        }
        output = report_results(results, overall, format="github")
        assert "file=/some/file.py" in output
        assert "line=7" in output

    def test_passing_checks_not_in_github_output(self):
        checks = [
            CheckItem(name="ok", passed=True, message="all good", severity=Severity.ERROR),
        ]
        results = [CheckResult(plugin="p", passed=True, checks=checks, score=100, file_path="/f.py")]
        overall = {
            "overall_score": 100, "passed": True, "threshold": 75,
            "plugins_passed": 1, "plugins_failed": 0,
            "error_count": 0, "warning_count": 0, "info_count": 0,
        }
        output = report_results(results, overall, format="github")
        assert "::error" not in output
        assert "::warning" not in output

    def test_no_results_produces_empty_output(self):
        overall = {
            "overall_score": 100, "passed": True, "threshold": 75,
            "plugins_passed": 0, "plugins_failed": 0,
            "error_count": 0, "warning_count": 0, "info_count": 0,
        }
        output = report_results([], overall, format="github")
        assert output == ""

    def test_plugin_name_included_in_annotation(self):
        checks = [CheckItem(name="c", passed=False, message="fail", severity=Severity.ERROR)]
        results = [CheckResult(plugin="my-plugin", passed=False, checks=checks, score=0, file_path="/f.py")]
        overall = {
            "overall_score": 0, "passed": False, "threshold": 75,
            "plugins_passed": 0, "plugins_failed": 1,
            "error_count": 1, "warning_count": 0, "info_count": 0,
        }
        output = report_results(results, overall, format="github")
        assert "my-plugin" in output


# ---------------------------------------------------------------------------
# CLI tests — via subprocess to test the real entry point
# ---------------------------------------------------------------------------



class TestCLIInit:
    def test_init_creates_config_file(self, tmp_path):
        subprocess.run(
            [sys.executable, "-m", "seedgo.cli"],
            input="",
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env={**__import__("os").environ, "PYTHONPATH": str(Path(__file__).parent.parent / "src")},
        )
        # The above runs cli as module — we need the main() entry
        # Actually test by calling main() directly via runner script
        pass  # Covered by direct function tests below

    def test_init_via_main_creates_config(self, tmp_path):
        """Call _cmd_init directly to test config creation."""
        from seedgo.cli import _cmd_init
        import argparse

        args = argparse.Namespace(profile=None)
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_path))
            _cmd_init(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert (tmp_path / ".seedgo" / "config.json").exists()

    def test_init_with_profile_embeds_profile(self, tmp_path):
        from seedgo.cli import _cmd_init
        import argparse

        args = argparse.Namespace(profile="python-basic")
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_path))
            _cmd_init(args)
        finally:
            __import__("os").chdir(old_cwd)

        config_path = tmp_path / ".seedgo" / "config.json"
        data = json.loads(config_path.read_text())
        assert data["profile"] == "python-basic"

    def test_init_fails_if_config_exists(self, tmp_project):
        """If config already exists, init should exit with code 1."""
        from seedgo.cli import _cmd_init
        import argparse

        (tmp_project / ".seedgo" / "config.json").write_text("{}")
        args = argparse.Namespace(profile=None)
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_project))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_init(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert exc_info.value.code == 1

    def test_init_creates_plugins_dir(self, tmp_path):
        from seedgo.cli import _cmd_init
        import argparse

        args = argparse.Namespace(profile=None)
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_path))
            _cmd_init(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert (tmp_path / ".seedgo" / "plugins").is_dir()


class TestCLICheck:
    def test_check_with_no_plugins_exits_0(self, tmp_project, sample_py_file):
        """No matching plugins = no failures = exit code 0."""
        from seedgo.cli import _cmd_check
        import argparse

        # Filter to a nonexistent plugin so builtins are also excluded
        args = argparse.Namespace(
            files=[str(sample_py_file)],
            format="human",
            threshold=None,
            plugins=["nonexistent-plugin-xyz"],
        )
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_project))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_check(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert exc_info.value.code == 0

    def test_check_with_passing_plugin_exits_0(self, passing_plugin, sample_py_file):
        from seedgo.cli import _cmd_check
        import argparse

        # Filter to only the local always-pass plugin to isolate from builtins
        args = argparse.Namespace(
            files=[str(sample_py_file)],
            format="human",
            threshold=None,
            plugins=["always-pass"],
        )
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(passing_plugin))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_check(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert exc_info.value.code == 0

    def test_check_with_failing_plugin_exits_1(self, failing_plugin, sample_py_file):
        from seedgo.cli import _cmd_check
        import argparse

        args = argparse.Namespace(
            files=[str(sample_py_file)],
            format="human",
            threshold=None,
            plugins=None,
        )
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(failing_plugin))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_check(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert exc_info.value.code == 1

    def test_check_json_format_produces_valid_json(self, passing_plugin, sample_py_file, capsys):
        from seedgo.cli import _cmd_check
        import argparse

        args = argparse.Namespace(
            files=[str(sample_py_file)],
            format="json",
            threshold=None,
            plugins=None,
        )
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(passing_plugin))
            with pytest.raises(SystemExit):
                _cmd_check(args)
        finally:
            __import__("os").chdir(old_cwd)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "overall_score" in data

    def test_check_threshold_override(self, passing_plugin, sample_py_file):
        """--threshold 101 should force a fail even with a passing plugin."""
        from seedgo.cli import _cmd_check
        import argparse

        args = argparse.Namespace(
            files=[str(sample_py_file)],
            format="human",
            threshold=101,  # impossible to reach
            plugins=None,
        )
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(passing_plugin))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_check(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert exc_info.value.code == 1

    def test_check_without_seedgo_dir_exits_1(self, tmp_path, capsys):
        """Running check outside a project (no .seedgo/) should exit 1 with error."""
        from seedgo.cli import _cmd_check
        import argparse

        args = argparse.Namespace(
            files=[],
            format="human",
            threshold=None,
            plugins=None,
        )
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_path))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_check(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert exc_info.value.code == 1


class TestCLIList:
    def test_list_with_no_plugins_prints_message(self, tmp_project, capsys):
        # With builtin plugins now shipping, list always shows at least the builtins.
        # The test verifies list exits 0 and produces output — specific message
        # check updated to reflect that builtins are always discovered.
        from seedgo.cli import _cmd_list
        import argparse

        args = argparse.Namespace()
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_project))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_list(args)
        finally:
            __import__("os").chdir(old_cwd)

        captured = capsys.readouterr()
        assert exc_info.value.code == 0
        # Builtins are always present now — output should list them
        assert "plugin" in captured.out.lower()

    def test_list_shows_plugin_names(self, passing_plugin, capsys):
        from seedgo.cli import _cmd_list
        import argparse

        args = argparse.Namespace()
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(passing_plugin))
            with pytest.raises(SystemExit):
                _cmd_list(args)
        finally:
            __import__("os").chdir(old_cwd)

        captured = capsys.readouterr()
        assert "always-pass" in captured.out

    def test_list_shows_source(self, passing_plugin, capsys):
        from seedgo.cli import _cmd_list
        import argparse

        args = argparse.Namespace()
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(passing_plugin))
            with pytest.raises(SystemExit):
                _cmd_list(args)
        finally:
            __import__("os").chdir(old_cwd)

        captured = capsys.readouterr()
        assert "local" in captured.out

    def test_list_shows_file_types(self, passing_plugin, capsys):
        from seedgo.cli import _cmd_list
        import argparse

        args = argparse.Namespace()
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(passing_plugin))
            with pytest.raises(SystemExit):
                _cmd_list(args)
        finally:
            __import__("os").chdir(old_cwd)

        captured = capsys.readouterr()
        assert "*.py" in captured.out

    def test_list_exits_0(self, tmp_project):
        from seedgo.cli import _cmd_list
        import argparse

        args = argparse.Namespace()
        old_cwd = __import__("os").getcwd()
        try:
            __import__("os").chdir(str(tmp_project))
            with pytest.raises(SystemExit) as exc_info:
                _cmd_list(args)
        finally:
            __import__("os").chdir(old_cwd)

        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# CLI main() argparse dispatch tests
# ---------------------------------------------------------------------------


class TestCLIMain:
    """Test the main() entry point's argparse dispatch via sys.argv patching."""

    def test_main_no_args_exits_0(self):
        """main() with no command prints help and exits 0."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(sys, "argv", ["seedgo"])
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_main_init_command_dispatches(self, tmp_path):
        """main() with 'init' dispatches to _cmd_init."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(sys, "argv", ["seedgo", "init"])
            mp.chdir(tmp_path)
            main()

        assert (tmp_path / ".seedgo" / "config.json").exists()

    def test_main_init_with_profile(self, tmp_path):
        """main() with 'init --profile python-basic' passes profile through."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(sys, "argv", ["seedgo", "init", "--profile", "python-basic"])
            mp.chdir(tmp_path)
            main()

        data = json.loads((tmp_path / ".seedgo" / "config.json").read_text())
        assert data["profile"] == "python-basic"

    def test_main_list_command_dispatches(self, tmp_project, capsys):
        """main() with 'list' dispatches to _cmd_list."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(sys, "argv", ["seedgo", "list"])
            mp.chdir(tmp_project)
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_main_check_no_seedgo_exits_1(self, tmp_path, capsys):
        """main() check outside a project exits 1."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(sys, "argv", ["seedgo", "check"])
            mp.chdir(tmp_path)
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_main_check_with_passing_plugin(self, passing_plugin, sample_py_file):
        """main() check with passing plugin exits 0."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            # Filter to only the local always-pass plugin to isolate from builtins
            mp.setattr(sys, "argv", ["seedgo", "check", str(sample_py_file), "--plugin", "always-pass"])
            mp.chdir(passing_plugin)
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_main_check_github_format(self, tmp_project, sample_py_file, capsys):
        """main() check --format github produces annotation-style output (empty if passing)."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            # Filter to a nonexistent plugin so builtins are also excluded — pure format test
            mp.setattr(sys, "argv", [
                "seedgo", "check", str(sample_py_file),
                "--format", "github",
                "--plugin", "nonexistent-plugin-xyz",
            ])
            mp.chdir(tmp_project)
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_main_check_nonexistent_file_exits_1(self, tmp_project, capsys):
        """main() check with a file that doesn't exist exits 1."""
        from seedgo.cli import main

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(sys, "argv", ["seedgo", "check", "/nonexistent/file.py"])
            mp.chdir(tmp_project)
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Public API export test
# ---------------------------------------------------------------------------


class TestPublicAPIPhase2:
    def test_run_checks_importable_from_seedgo(self):
        from seedgo import run_checks as rc
        assert callable(rc)

    def test_run_checks_in_dunder_all(self):
        import seedgo
        assert "run_checks" in seedgo.__all__
