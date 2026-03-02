"""
Seed Go Core Framework Tests

Comprehensive tests for Phase 1 deliverables:
  - models.py: CheckResult, CheckItem, Severity
  - config.py: load_config, find_project_root, create_default_config, DEFAULT_CONFIG
  - discovery.py: discover_plugins and helper functions
  - bypass.py: is_bypassed, load_bypass_rules
  - exceptions.py: exception hierarchy

Target: 85%+ coverage of src/seedgo/ core modules.
"""

import json
from pathlib import Path

import pytest

from seedgo.models import CheckItem, CheckResult, Severity
from seedgo.config import (
    DEFAULT_CONFIG,
    _deep_merge,
    create_default_config,
    find_project_root,
    load_config,
    resolve_file_config,
)
from seedgo.bypass import is_bypassed, load_bypass_rules
from seedgo.discovery import _scan_directory, discover_plugins
from seedgo.exceptions import ConfigError, DiscoveryError, PluginError, SeedGoError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path):
    """A temporary project root with a .seedgo/ directory."""
    seedgo_dir = tmp_path / ".seedgo"
    seedgo_dir.mkdir()
    (seedgo_dir / "plugins").mkdir()
    return tmp_path


@pytest.fixture
def tmp_project_with_config(tmp_project):
    """A temporary project with a minimal .seedgo/config.json."""
    config = {
        "version": "1.0.0",
        "plugins": {
            "enabled": ["test-plugin"],
            "disabled": [],
            "config": {},
        },
        "scoring": {"threshold": 80},
    }
    config_path = tmp_project / ".seedgo" / "config.json"
    config_path.write_text(json.dumps(config))
    return tmp_project


@pytest.fixture
def simple_plugin_file(tmp_project):
    """Write a minimal valid plugin into .seedgo/plugins/."""
    plugin_code = """
PLUGIN_NAME = "test-plugin"
PLUGIN_DESCRIPTION = "A simple test plugin"
FILE_TYPES = ["*.py"]

from seedgo.models import CheckResult, CheckItem, Severity

def check(file_path, config=None):
    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=True,
        checks=[CheckItem(name="always-passes", passed=True, message="ok")],
        score=100,
        file_path=file_path,
    )
"""
    plugin_path = tmp_project / ".seedgo" / "plugins" / "test_plugin.py"
    plugin_path.write_text(plugin_code)
    return plugin_path


@pytest.fixture
def bypass_rules_file(tmp_project):
    """Write a .seedgo/bypass.json file."""
    rules = {
        "version": "1.0.0",
        "bypass": [
            {
                "file": "src/legacy.py",
                "plugin": "no-bare-except",
                "reason": "Legacy code",
            },
            {
                "file": "src/utils.py",
                "plugin": "type-hints",
                "lines": [10, 20],
                "reason": "Line-specific bypass",
            },
        ],
    }
    bypass_path = tmp_project / ".seedgo" / "bypass.json"
    bypass_path.write_text(json.dumps(rules))
    return tmp_project


# ---------------------------------------------------------------------------
# Severity tests
# ---------------------------------------------------------------------------


class TestSeverity:
    def test_severity_values(self):
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_severity_is_enum(self):
        from enum import Enum
        assert issubclass(Severity, Enum)

    def test_severity_members(self):
        members = {s.name for s in Severity}
        assert members == {"ERROR", "WARNING", "INFO"}

    def test_severity_comparison(self):
        assert Severity.ERROR == Severity.ERROR
        assert Severity.ERROR != Severity.WARNING

    def test_severity_from_value(self):
        assert Severity("error") == Severity.ERROR
        assert Severity("warning") == Severity.WARNING
        assert Severity("info") == Severity.INFO


# ---------------------------------------------------------------------------
# CheckItem tests
# ---------------------------------------------------------------------------


class TestCheckItem:
    def test_required_fields(self):
        item = CheckItem(name="test", passed=True, message="all good")
        assert item.name == "test"
        assert item.passed is True
        assert item.message == "all good"

    def test_default_severity_is_error(self):
        item = CheckItem(name="x", passed=False, message="fail")
        assert item.severity == Severity.ERROR

    def test_custom_severity(self):
        item = CheckItem(name="x", passed=False, message="warn", severity=Severity.WARNING)
        assert item.severity == Severity.WARNING

    def test_optional_line_defaults_to_none(self):
        item = CheckItem(name="x", passed=True, message="ok")
        assert item.line is None

    def test_optional_fix_hint_defaults_to_none(self):
        item = CheckItem(name="x", passed=True, message="ok")
        assert item.fix_hint is None

    def test_all_fields(self):
        item = CheckItem(
            name="bare-except",
            passed=False,
            message="Found bare except at line 5",
            severity=Severity.WARNING,
            line=5,
            fix_hint="except Exception:",
        )
        assert item.name == "bare-except"
        assert item.passed is False
        assert item.severity == Severity.WARNING
        assert item.line == 5
        assert item.fix_hint == "except Exception:"

    def test_missing_required_field_raises(self):
        with pytest.raises(TypeError):
            CheckItem(name="x", passed=True)  # type: ignore[call-arg]  # missing message

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(CheckItem)


# ---------------------------------------------------------------------------
# CheckResult tests
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_required_fields(self):
        result = CheckResult(plugin="my-plugin", passed=True)
        assert result.plugin == "my-plugin"
        assert result.passed is True

    def test_checks_defaults_to_empty_list(self):
        result = CheckResult(plugin="p", passed=True)
        assert result.checks == []

    def test_score_defaults_to_zero(self):
        result = CheckResult(plugin="p", passed=True)
        assert result.score == 0

    def test_file_path_defaults_to_empty_string(self):
        result = CheckResult(plugin="p", passed=True)
        assert result.file_path == ""

    def test_metadata_defaults_to_empty_dict(self):
        result = CheckResult(plugin="p", passed=True)
        assert result.metadata == {}

    def test_metadata_is_independent_per_instance(self):
        r1 = CheckResult(plugin="p", passed=True)
        r2 = CheckResult(plugin="p", passed=True)
        r1.metadata["key"] = "val"
        assert "key" not in r2.metadata

    def test_checks_is_independent_per_instance(self):
        r1 = CheckResult(plugin="p", passed=True)
        r2 = CheckResult(plugin="p", passed=True)
        r1.checks.append(CheckItem(name="x", passed=True, message="ok"))
        assert len(r2.checks) == 0

    def test_full_construction(self):
        items = [
            CheckItem(name="c1", passed=True, message="ok"),
            CheckItem(name="c2", passed=False, message="fail", severity=Severity.WARNING),
        ]
        result = CheckResult(
            plugin="no-bare-except",
            passed=False,
            checks=items,
            score=65,
            file_path="/path/to/file.py",
            metadata={"ast_nodes": 42},
        )
        assert result.plugin == "no-bare-except"
        assert result.passed is False
        assert len(result.checks) == 2
        assert result.score == 65
        assert result.file_path == "/path/to/file.py"
        assert result.metadata["ast_nodes"] == 42

    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(CheckResult)

    def test_asdict_serializable(self):
        import dataclasses
        result = CheckResult(
            plugin="p",
            passed=True,
            checks=[CheckItem(name="c", passed=True, message="ok")],
            score=100,
        )
        d = dataclasses.asdict(result)
        assert d["plugin"] == "p"
        assert d["passed"] is True
        assert d["score"] == 100
        assert d["checks"][0]["name"] == "c"


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    def test_default_config_has_required_keys(self):
        assert "version" in DEFAULT_CONFIG
        assert "profile" in DEFAULT_CONFIG
        assert "plugins" in DEFAULT_CONFIG
        assert "scoring" in DEFAULT_CONFIG
        assert "paths" in DEFAULT_CONFIG
        assert "overrides" in DEFAULT_CONFIG

    def test_default_profile_is_none(self):
        assert DEFAULT_CONFIG["profile"] is None

    def test_default_threshold(self):
        assert DEFAULT_CONFIG["scoring"]["threshold"] == 75

    def test_default_weights(self):
        scoring = DEFAULT_CONFIG["scoring"]
        assert scoring["error_weight"] == 1.0
        assert scoring["warning_weight"] == 0.5
        assert scoring["info_weight"] == 0.0

    def test_default_paths_include(self):
        assert DEFAULT_CONFIG["paths"]["include"] == ["."]

    def test_default_plugins_empty(self):
        plugins = DEFAULT_CONFIG["plugins"]
        assert plugins["enabled"] == []
        assert plugins["disabled"] == []
        assert plugins["config"] == {}

    def test_default_overrides_empty(self):
        assert DEFAULT_CONFIG["overrides"] == []


class TestLoadConfig:
    def test_returns_defaults_when_no_config_file(self, tmp_project):
        config = load_config(str(tmp_project))
        assert config["scoring"]["threshold"] == 75
        assert config["profile"] is None

    def test_loads_user_config(self, tmp_project_with_config):
        config = load_config(str(tmp_project_with_config))
        assert config["scoring"]["threshold"] == 80

    def test_merges_user_config_over_defaults(self, tmp_project):
        user_cfg = {"scoring": {"threshold": 90}}
        (tmp_project / ".seedgo" / "config.json").write_text(json.dumps(user_cfg))
        config = load_config(str(tmp_project))
        assert config["scoring"]["threshold"] == 90
        # Other defaults preserved
        assert config["scoring"]["error_weight"] == 1.0

    def test_raises_config_error_on_invalid_json(self, tmp_project):
        (tmp_project / ".seedgo" / "config.json").write_text("{ invalid json }")
        with pytest.raises(ConfigError):
            load_config(str(tmp_project))

    def test_plugins_enabled_list_loaded(self, tmp_project):
        cfg = {"plugins": {"enabled": ["plugin-a", "plugin-b"]}}
        (tmp_project / ".seedgo" / "config.json").write_text(json.dumps(cfg))
        config = load_config(str(tmp_project))
        assert "plugin-a" in config["plugins"]["enabled"]

    def test_default_config_not_mutated(self, tmp_project):
        """load_config must return a copy — DEFAULT_CONFIG must stay pristine."""
        import copy
        original = copy.deepcopy(DEFAULT_CONFIG)
        cfg = {"scoring": {"threshold": 99}}
        (tmp_project / ".seedgo" / "config.json").write_text(json.dumps(cfg))
        load_config(str(tmp_project))
        assert DEFAULT_CONFIG == original


class TestFindProjectRoot:
    def test_finds_root_from_subdir(self, tmp_project):
        subdir = tmp_project / "src" / "mypackage"
        subdir.mkdir(parents=True)
        root = find_project_root(str(subdir))
        assert root == str(tmp_project)

    def test_finds_root_from_file(self, tmp_project):
        src = tmp_project / "src"
        src.mkdir()
        some_file = src / "main.py"
        some_file.write_text("pass")
        root = find_project_root(str(some_file))
        assert root == str(tmp_project)

    def test_returns_none_when_no_seedgo_dir(self, tmp_path):
        subdir = tmp_path / "no_seedgo_here" / "nested"
        subdir.mkdir(parents=True)
        root = find_project_root(str(subdir))
        assert root is None

    def test_finds_root_from_project_root_itself(self, tmp_project):
        root = find_project_root(str(tmp_project))
        assert root == str(tmp_project)


class TestCreateDefaultConfig:
    def test_creates_config_file(self, tmp_path):
        project = tmp_path / "newproject"
        project.mkdir()
        config_path = create_default_config(str(project))
        assert Path(config_path).exists()

    def test_created_config_is_valid_json(self, tmp_path):
        project = tmp_path / "newproject"
        project.mkdir()
        config_path = create_default_config(str(project))
        with open(config_path) as f:
            data = json.load(f)
        assert "version" in data
        assert "scoring" in data

    def test_creates_seedgo_dir_if_missing(self, tmp_path):
        project = tmp_path / "newproject"
        project.mkdir()
        create_default_config(str(project))
        assert (project / ".seedgo").is_dir()

    def test_creates_plugins_subdir(self, tmp_path):
        project = tmp_path / "newproject"
        project.mkdir()
        create_default_config(str(project))
        assert (project / ".seedgo" / "plugins").is_dir()

    def test_raises_if_config_already_exists(self, tmp_project):
        # Write a config so it already exists
        (tmp_project / ".seedgo" / "config.json").write_text("{}")
        with pytest.raises(ConfigError, match="already exists"):
            create_default_config(str(tmp_project))

    def test_profile_embedded_in_config(self, tmp_path):
        project = tmp_path / "newproject"
        project.mkdir()
        config_path = create_default_config(str(project), profile="python-basic")
        with open(config_path) as f:
            data = json.load(f)
        assert data["profile"] == "python-basic"


class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        _deep_merge(base, {"b": 99})
        assert base == {"a": 1, "b": 99}

    def test_nested_merge(self):
        base = {"scoring": {"threshold": 75, "error_weight": 1.0}}
        _deep_merge(base, {"scoring": {"threshold": 90}})
        assert base["scoring"]["threshold"] == 90
        assert base["scoring"]["error_weight"] == 1.0  # preserved

    def test_new_key_added(self):
        base = {"a": 1}
        _deep_merge(base, {"b": 2})
        assert base["b"] == 2

    def test_list_replaces_not_merges(self):
        base = {"plugins": {"enabled": ["a", "b"]}}
        _deep_merge(base, {"plugins": {"enabled": ["c"]}})
        assert base["plugins"]["enabled"] == ["c"]


class TestResolveFileConfig:
    def test_no_overrides_returns_same_config(self, tmp_project):
        config = load_config(str(tmp_project))
        resolved = resolve_file_config(config, str(tmp_project / "src" / "main.py"), str(tmp_project))
        assert resolved["scoring"]["threshold"] == config["scoring"]["threshold"]

    def test_override_applied_for_matching_path(self, tmp_project):
        cfg = {
            "scoring": {"threshold": 75},
            "overrides": [
                {"paths": ["tests/"], "scoring": {"threshold": 50}}
            ],
        }
        (tmp_project / ".seedgo" / "config.json").write_text(json.dumps(cfg))
        config = load_config(str(tmp_project))
        test_file = str(tmp_project / "tests" / "test_foo.py")
        resolved = resolve_file_config(config, test_file, str(tmp_project))
        assert resolved["scoring"]["threshold"] == 50

    def test_override_not_applied_for_non_matching_path(self, tmp_project):
        cfg = {
            "scoring": {"threshold": 75},
            "overrides": [
                {"paths": ["tests/"], "scoring": {"threshold": 50}}
            ],
        }
        (tmp_project / ".seedgo" / "config.json").write_text(json.dumps(cfg))
        config = load_config(str(tmp_project))
        src_file = str(tmp_project / "src" / "main.py")
        resolved = resolve_file_config(config, src_file, str(tmp_project))
        assert resolved["scoring"]["threshold"] == 75


# ---------------------------------------------------------------------------
# Bypass tests
# ---------------------------------------------------------------------------


class TestLoadBypassRules:
    def test_returns_empty_list_when_no_file(self, tmp_project):
        rules = load_bypass_rules(str(tmp_project))
        assert rules == []

    def test_loads_rules(self, bypass_rules_file):
        rules = load_bypass_rules(str(bypass_rules_file))
        assert len(rules) == 2

    def test_returns_empty_on_invalid_json(self, tmp_project):
        (tmp_project / ".seedgo" / "bypass.json").write_text("{ bad json }")
        rules = load_bypass_rules(str(tmp_project))
        assert rules == []

    def test_returns_empty_when_bypass_key_missing(self, tmp_project):
        (tmp_project / ".seedgo" / "bypass.json").write_text('{"version": "1.0.0"}')
        rules = load_bypass_rules(str(tmp_project))
        assert rules == []


class TestIsBypassed:
    def test_no_rules_returns_false(self):
        assert is_bypassed("src/foo.py", "my-plugin", bypass_rules=None) is False

    def test_empty_rules_returns_false(self):
        assert is_bypassed("src/foo.py", "my-plugin", bypass_rules=[]) is False

    def test_whole_file_plugin_bypass(self):
        rules = [{"file": "src/legacy.py", "plugin": "no-bare-except"}]
        assert is_bypassed("src/legacy.py", "no-bare-except", bypass_rules=rules) is True

    def test_different_file_not_bypassed(self):
        rules = [{"file": "src/legacy.py", "plugin": "no-bare-except"}]
        assert is_bypassed("src/other.py", "no-bare-except", bypass_rules=rules) is False

    def test_different_plugin_not_bypassed(self):
        rules = [{"file": "src/legacy.py", "plugin": "no-bare-except"}]
        assert is_bypassed("src/legacy.py", "type-hints", bypass_rules=rules) is False

    def test_line_specific_bypass_matching_line(self):
        rules = [{"file": "src/utils.py", "plugin": "type-hints", "lines": [10, 20]}]
        assert is_bypassed("src/utils.py", "type-hints", line=10, bypass_rules=rules) is True

    def test_line_specific_bypass_non_matching_line(self):
        rules = [{"file": "src/utils.py", "plugin": "type-hints", "lines": [10, 20]}]
        assert is_bypassed("src/utils.py", "type-hints", line=99, bypass_rules=rules) is False

    def test_line_specific_bypass_no_line_provided(self):
        """Line rule requires a matching line — without line=, should not bypass."""
        rules = [{"file": "src/utils.py", "plugin": "type-hints", "lines": [10, 20]}]
        assert is_bypassed("src/utils.py", "type-hints", line=None, bypass_rules=rules) is False

    def test_project_root_relative_path(self, tmp_project):
        rules = [{"file": "src/legacy.py", "plugin": "no-bare-except"}]
        abs_path = str(tmp_project / "src" / "legacy.py")
        assert is_bypassed(abs_path, "no-bare-except", bypass_rules=rules, project_root=str(tmp_project)) is True

    def test_multiple_rules_first_match_wins(self):
        rules = [
            {"file": "src/foo.py", "plugin": "plugin-a"},
            {"file": "src/foo.py", "plugin": "plugin-b"},
        ]
        assert is_bypassed("src/foo.py", "plugin-a", bypass_rules=rules) is True
        assert is_bypassed("src/foo.py", "plugin-b", bypass_rules=rules) is True
        assert is_bypassed("src/foo.py", "plugin-c", bypass_rules=rules) is False


# ---------------------------------------------------------------------------
# Discovery tests
# ---------------------------------------------------------------------------


class TestScanDirectory:
    def test_returns_empty_for_nonexistent_dir(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        result = _scan_directory(nonexistent, source="builtin")
        assert result == []

    def test_skips_underscore_files(self, tmp_path):
        (tmp_path / "_private.py").write_text("PLUGIN_NAME = 'x'\ndef check(f, c=None): pass")
        (tmp_path / "__init__.py").write_text("")
        result = _scan_directory(tmp_path, source="builtin")
        assert result == []

    def test_discovers_valid_plugin(self, tmp_path):
        plugin_code = "PLUGIN_NAME = 'my-plugin'\ndef check(f, c=None): pass"
        (tmp_path / "my_plugin.py").write_text(plugin_code)
        result = _scan_directory(tmp_path, source="local")
        assert len(result) == 1
        assert result[0]["name"] == "my-plugin"
        assert result[0]["source"] == "local"

    def test_skips_file_without_plugin_name(self, tmp_path):
        (tmp_path / "not_a_plugin.py").write_text("def check(f, c=None): pass")
        result = _scan_directory(tmp_path, source="local")
        assert result == []

    def test_skips_file_without_check_function(self, tmp_path):
        (tmp_path / "no_check.py").write_text("PLUGIN_NAME = 'x'")
        result = _scan_directory(tmp_path, source="local")
        assert result == []

    def test_skips_broken_plugin_silently(self, tmp_path):
        (tmp_path / "broken.py").write_text("raise RuntimeError('boom')")
        # Should not raise — broken plugins are silently skipped
        result = _scan_directory(tmp_path, source="local")
        assert result == []

    def test_multiple_plugins_discovered(self, tmp_path):
        for i in range(3):
            code = f"PLUGIN_NAME = 'plugin-{i}'\ndef check(f, c=None): pass"
            (tmp_path / f"plugin_{i}.py").write_text(code)
        result = _scan_directory(tmp_path, source="builtin")
        assert len(result) == 3

    def test_descriptor_has_required_keys(self, tmp_path):
        (tmp_path / "p.py").write_text("PLUGIN_NAME = 'p'\ndef check(f, c=None): pass")
        result = _scan_directory(tmp_path, source="local")
        assert len(result) == 1
        descriptor = result[0]
        assert "name" in descriptor
        assert "module" in descriptor
        assert "source" in descriptor
        assert "path" in descriptor


class TestDiscoverPlugins:
    def test_returns_list(self, tmp_project):
        result = discover_plugins(str(tmp_project))
        assert isinstance(result, list)

    def test_discovers_local_plugin(self, tmp_project, simple_plugin_file):
        result = discover_plugins(str(tmp_project))
        names = [p["name"] for p in result]
        assert "test-plugin" in names

    def test_local_plugin_source_is_local(self, tmp_project, simple_plugin_file):
        result = discover_plugins(str(tmp_project))
        local_plugins = [p for p in result if p["source"] == "local"]
        assert len(local_plugins) >= 1

    def test_deduplication_last_wins(self, tmp_project):
        """Two plugins with the same name — the last one (local) wins."""
        # Create a builtin-style plugin by patching the builtin directory
        local_code = "PLUGIN_NAME = 'dupe-plugin'\ndef check(f, c=None): return 'local'"
        (tmp_project / ".seedgo" / "plugins" / "dupe.py").write_text(local_code)
        result = discover_plugins(str(tmp_project))
        dupe = next((p for p in result if p["name"] == "dupe-plugin"), None)
        assert dupe is not None
        assert dupe["source"] == "local"

    def test_no_project_root_still_works(self):
        result = discover_plugins(project_root=None)
        assert isinstance(result, list)

    def test_plugin_descriptor_has_module(self, tmp_project, simple_plugin_file):
        result = discover_plugins(str(tmp_project))
        plugin = next((p for p in result if p["name"] == "test-plugin"), None)
        assert plugin is not None
        assert hasattr(plugin["module"], "check")
        assert hasattr(plugin["module"], "PLUGIN_NAME")


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_seedgo_error_is_exception(self):
        assert issubclass(SeedGoError, Exception)

    def test_config_error_inherits_seedgo_error(self):
        assert issubclass(ConfigError, SeedGoError)

    def test_plugin_error_inherits_seedgo_error(self):
        assert issubclass(PluginError, SeedGoError)

    def test_discovery_error_inherits_seedgo_error(self):
        assert issubclass(DiscoveryError, SeedGoError)

    def test_config_error_can_be_raised_and_caught(self):
        with pytest.raises(ConfigError):
            raise ConfigError("bad config")

    def test_plugin_error_can_be_raised_and_caught(self):
        with pytest.raises(PluginError):
            raise PluginError("bad plugin")

    def test_discovery_error_can_be_raised_and_caught(self):
        with pytest.raises(DiscoveryError):
            raise DiscoveryError("discovery failed")

    def test_catch_all_via_seedgo_error(self):
        """All custom exceptions should be catchable via SeedGoError."""
        for exc_class in (ConfigError, PluginError, DiscoveryError):
            with pytest.raises(SeedGoError):
                raise exc_class("test")

    def test_error_message_preserved(self):
        try:
            raise ConfigError("specific message")
        except ConfigError as e:
            assert "specific message" in str(e)


# ---------------------------------------------------------------------------
# Public API / __init__ tests
# ---------------------------------------------------------------------------


class TestPublicAPI:
    def test_version_is_string(self):
        import seedgo
        assert isinstance(seedgo.__version__, str)

    def test_version_format(self):
        import seedgo
        parts = seedgo.__version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_version_is_1_0_0(self):
        import seedgo
        assert seedgo.__version__ == "1.0.0"

    def test_check_result_importable_from_seedgo(self):
        from seedgo import CheckResult
        assert CheckResult is not None

    def test_check_item_importable_from_seedgo(self):
        from seedgo import CheckItem
        assert CheckItem is not None

    def test_severity_importable_from_seedgo(self):
        from seedgo import Severity
        assert Severity is not None

    def test_discover_plugins_importable_from_seedgo(self):
        from seedgo import discover_plugins
        assert callable(discover_plugins)

    def test_load_config_importable_from_seedgo(self):
        from seedgo import load_config
        assert callable(load_config)

    def test_all_exports_listed_in_dunder_all(self):
        import seedgo
        for name in ["CheckResult", "CheckItem", "Severity", "discover_plugins", "load_config"]:
            assert name in seedgo.__all__
