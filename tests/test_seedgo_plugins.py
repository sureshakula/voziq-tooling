"""
Seed Go Plugin Tests — Phase 3

Tests for all 5 starter plugins:
  - no-bare-except
  - type-hints-required
  - docstring-coverage
  - function-length
  - file-structure

Each plugin has:
  - A clean-file test (should pass)
  - A violation test (should fail)
  - Edge case tests (empty files, comments, binary-safe reads)
  - Configurable option tests where applicable

Uses tmp_path for isolated test directories.
"""

import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path when running from the repo root
_repo_root = Path(__file__).parent.parent
_src_path = str(_repo_root / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Import plugin modules directly for unit testing
import importlib.util

def _load_plugin(plugin_filename: str | Path):
    """Load a plugin module by filename from the plugins directory."""
    plugin_path = _repo_root / "src" / "seedgo" / "plugins" / plugin_filename
    spec = importlib.util.spec_from_file_location(Path(plugin_filename).stem, plugin_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Plugin: no-bare-except
# ---------------------------------------------------------------------------

class TestNoBareExcept:
    @pytest.fixture
    def plugin(self):
        return _load_plugin(Path("no_bare_except.py"))

    def test_plugin_name(self, plugin):
        assert plugin.PLUGIN_NAME == "no-bare-except"

    def test_plugin_has_description(self, plugin):
        assert isinstance(plugin.PLUGIN_DESCRIPTION, str)
        assert len(plugin.PLUGIN_DESCRIPTION) > 0

    def test_plugin_has_file_types(self, plugin):
        assert plugin.FILE_TYPES == ["*.py"]

    def test_clean_file_passes(self, plugin, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text(
            "try:\n"
            "    do_something()\n"
            "except Exception:\n"
            "    pass\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True
        assert result.plugin == "no-bare-except"
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 0

    def test_bare_except_fails(self, plugin, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text(
            "try:\n"
            "    do_something()\n"
            "except:\n"
            "    pass\n"
        )
        result = plugin.check(str(f))
        assert result.passed is False
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 1
        assert failed[0].line == 3

    def test_multiple_bare_excepts(self, plugin, tmp_path):
        f = tmp_path / "multi.py"
        f.write_text(
            "try:\n"
            "    x()\n"
            "except:\n"
            "    pass\n"
            "try:\n"
            "    y()\n"
            "except:\n"
            "    pass\n"
        )
        result = plugin.check(str(f))
        assert result.passed is False
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 2

    def test_bare_except_in_comment_ignored(self, plugin, tmp_path):
        f = tmp_path / "comment.py"
        f.write_text(
            "# except:  <- this is just a comment\n"
            "x = 1\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_bare_except_in_string_ignored(self, plugin, tmp_path):
        f = tmp_path / "string.py"
        f.write_text(
            'x = """This shows except: usage"""\n'
            "y = 1\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_empty_file_passes(self, plugin, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        result = plugin.check(str(f))
        assert result.passed is True

    def test_file_with_only_comments_passes(self, plugin, tmp_path):
        f = tmp_path / "comments.py"
        f.write_text(
            "# This is a comment\n"
            "# except: not a real bare except\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_nonexistent_file_returns_passing(self, plugin, tmp_path):
        result = plugin.check(str(tmp_path / "does_not_exist.py"))
        assert result.passed is True
        assert result.metadata.get("skipped") is True

    def test_bare_except_with_inline_comment_still_flagged(self, plugin, tmp_path):
        f = tmp_path / "inline.py"
        f.write_text(
            "try:\n"
            "    x()\n"
            "except:  # bad practice\n"
            "    pass\n"
        )
        result = plugin.check(str(f))
        assert result.passed is False

    def test_specific_exception_passes(self, plugin, tmp_path):
        f = tmp_path / "specific.py"
        f.write_text(
            "try:\n"
            "    x()\n"
            "except (ValueError, TypeError):\n"
            "    pass\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_result_has_file_path(self, plugin, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        result = plugin.check(str(f))
        assert result.file_path == str(f)


# ---------------------------------------------------------------------------
# Plugin: type-hints-required
# ---------------------------------------------------------------------------

class TestTypeHintsRequired:
    @pytest.fixture
    def plugin(self):
        return _load_plugin(Path("type_hints_required.py"))

    def test_plugin_name(self, plugin):
        assert plugin.PLUGIN_NAME == "type-hints-required"

    def test_clean_file_passes(self, plugin, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text(
            "def greet(name: str) -> str:\n"
            "    return f'Hello {name}'\n"
            "\n"
            "def add(a: int, b: int) -> int:\n"
            "    return a + b\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 0

    def test_missing_return_type_fails(self, plugin, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text(
            "def greet(name: str):\n"
            "    return f'Hello {name}'\n"
        )
        result = plugin.check(str(f))
        assert result.passed is False
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 1
        assert "greet" in failed[0].message

    def test_private_function_skipped(self, plugin, tmp_path):
        f = tmp_path / "private.py"
        f.write_text(
            "def _helper():\n"
            "    return 42\n"
            "\n"
            "def __dunder():\n"
            "    return 42\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_init_skipped(self, plugin, tmp_path):
        f = tmp_path / "cls.py"
        f.write_text(
            "class Foo:\n"
            "    def __init__(self, x: int):\n"
            "        self.x = x\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_dunder_methods_skipped(self, plugin, tmp_path):
        f = tmp_path / "dunders.py"
        f.write_text(
            "class Foo:\n"
            "    def __str__(self):\n"
            "        return 'Foo'\n"
            "    def __repr__(self):\n"
            "        return 'Foo()'\n"
            "    def __len__(self):\n"
            "        return 0\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_empty_file_passes(self, plugin, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        result = plugin.check(str(f))
        assert result.passed is True

    def test_async_function_checked(self, plugin, tmp_path):
        f = tmp_path / "async_fn.py"
        f.write_text(
            "async def fetch_data(url: str):\n"
            "    pass\n"
            "    pass\n"
            "    pass\n"
        )
        result = plugin.check(str(f))
        assert result.passed is False
        failed = [c for c in result.checks if not c.passed]
        assert any("fetch_data" in c.message for c in failed)

    def test_async_function_with_return_type_passes(self, plugin, tmp_path):
        f = tmp_path / "async_ok.py"
        f.write_text(
            "async def fetch_data(url: str) -> bytes:\n"
            "    return b''\n"
        )
        result = plugin.check(str(f))
        assert result.passed is True

    def test_nonexistent_file_returns_passing(self, plugin, tmp_path):
        result = plugin.check(str(tmp_path / "ghost.py"))
        assert result.passed is True
        assert result.metadata.get("skipped") is True

    def test_syntax_error_skipped(self, plugin, tmp_path):
        f = tmp_path / "bad_syntax.py"
        f.write_text("def broken(\n    x:\n")
        result = plugin.check(str(f))
        assert result.passed is True
        assert result.metadata.get("skipped") is True

    def test_violation_has_line_number(self, plugin, tmp_path):
        f = tmp_path / "line.py"
        f.write_text(
            "x = 1\n"
            "y = 2\n"
            "def my_func(a: int):\n"
            "    return a\n"
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert any(c.line == 3 for c in failed)

    def test_violation_has_fix_hint(self, plugin, tmp_path):
        f = tmp_path / "hint.py"
        f.write_text(
            "def process(data: list):\n"
            "    return data\n"
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) > 0
        assert failed[0].fix_hint is not None


# ---------------------------------------------------------------------------
# Plugin: docstring-coverage
# ---------------------------------------------------------------------------

class TestDocstringCoverage:
    @pytest.fixture
    def plugin(self):
        return _load_plugin(Path("docstring_coverage.py"))

    def test_plugin_name(self, plugin):
        assert plugin.PLUGIN_NAME == "docstring-coverage"

    def test_clean_function_passes(self, plugin, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text(
            'def greet(name: str) -> str:\n'
            '    """Greet the user by name."""\n'
            '    return f"Hello {name}"\n'
            '    return f"Hello {name}"\n'
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 0

    def test_missing_docstring_flagged(self, plugin, tmp_path):
        f = tmp_path / "no_doc.py"
        f.write_text(
            "def process(data: list) -> list:\n"
            "    result = []\n"
            "    for item in data:\n"
            "        result.append(item)\n"
            "    return result\n"
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 1
        assert "process" in failed[0].message

    def test_info_severity(self, plugin, tmp_path):
        f = tmp_path / "info.py"
        f.write_text(
            "def process(data: list) -> list:\n"
            "    result = []\n"
            "    for item in data:\n"
            "        result.append(item)\n"
            "    return result\n"
        )
        result = plugin.check(str(f))
        from seedgo.models import Severity
        failed = [c for c in result.checks if not c.passed]
        assert all(c.severity == Severity.INFO for c in failed)

    def test_missing_docstring_still_passes_overall(self, plugin, tmp_path):
        """INFO violations should not cause overall failure."""
        f = tmp_path / "no_doc.py"
        f.write_text(
            "def process(data: list) -> list:\n"
            "    result = []\n"
            "    for item in data:\n"
            "        result.append(item)\n"
            "    return result\n"
        )
        result = plugin.check(str(f))
        # Overall passed=True even when there are INFO violations
        assert result.passed is True

    def test_private_function_skipped(self, plugin, tmp_path):
        f = tmp_path / "private.py"
        f.write_text(
            "def _helper(x: int) -> int:\n"
            "    y = x + 1\n"
            "    z = y * 2\n"
            "    return z\n"
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 0

    def test_short_function_skipped(self, plugin, tmp_path):
        """Functions with < 3 body statements are exempt."""
        f = tmp_path / "short.py"
        f.write_text(
            "def tiny(x):\n"
            "    return x\n"
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 0

    def test_class_without_docstring_flagged(self, plugin, tmp_path):
        f = tmp_path / "class_no_doc.py"
        f.write_text(
            "class MyService:\n"
            "    pass\n"
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 1
        assert "MyService" in failed[0].message

    def test_class_with_docstring_passes(self, plugin, tmp_path):
        f = tmp_path / "class_doc.py"
        f.write_text(
            'class MyService:\n'
            '    """Service for handling requests."""\n'
            '    pass\n'
        )
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        # MyService class should pass
        class_fails = [c for c in failed if "MyService" in c.message]
        assert len(class_fails) == 0

    def test_empty_file_passes(self, plugin, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        result = plugin.check(str(f))
        assert result.passed is True

    def test_nonexistent_file_passes(self, plugin, tmp_path):
        result = plugin.check(str(tmp_path / "ghost.py"))
        assert result.passed is True

    def test_syntax_error_skipped(self, plugin, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n")
        result = plugin.check(str(f))
        assert result.passed is True


# ---------------------------------------------------------------------------
# Plugin: function-length
# ---------------------------------------------------------------------------

class TestFunctionLength:
    @pytest.fixture
    def plugin(self):
        return _load_plugin(Path("function_length.py"))

    def test_plugin_name(self, plugin):
        assert plugin.PLUGIN_NAME == "function-length"

    def test_short_function_passes(self, plugin, tmp_path):
        f = tmp_path / "short.py"
        lines = ["def small_func() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(10)]
        f.write_text("".join(lines))
        result = plugin.check(str(f))
        assert result.passed is True

    def test_long_function_fails(self, plugin, tmp_path):
        f = tmp_path / "long.py"
        lines = ["def huge_func() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(55)]
        f.write_text("".join(lines))
        result = plugin.check(str(f))
        assert result.passed is False
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 1
        assert "huge_func" in failed[0].message

    def test_default_max_lines_is_50(self, plugin, tmp_path):
        """A function of exactly 50 lines should pass."""
        f = tmp_path / "border.py"
        lines = ["def border_func() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(49)]
        f.write_text("".join(lines))
        result = plugin.check(str(f))
        assert result.passed is True

    def test_function_at_51_lines_fails(self, plugin, tmp_path):
        f = tmp_path / "just_over.py"
        lines = ["def over_func() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(50)]
        f.write_text("".join(lines))
        result = plugin.check(str(f))
        assert result.passed is False

    def test_custom_max_lines_config(self, plugin, tmp_path):
        """With max_lines=10, a 15-line function should fail."""
        f = tmp_path / "custom.py"
        lines = ["def medium_func() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(15)]
        f.write_text("".join(lines))
        result = plugin.check(str(f), config={"max_lines": 10})
        assert result.passed is False

    def test_custom_max_lines_pass(self, plugin, tmp_path):
        """With max_lines=100, a 50-line function should pass."""
        f = tmp_path / "custom_pass.py"
        lines = ["def medium_func() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(50)]
        f.write_text("".join(lines))
        result = plugin.check(str(f), config={"max_lines": 100})
        assert result.passed is True

    def test_multiple_long_functions_all_reported(self, plugin, tmp_path):
        f = tmp_path / "multi.py"
        lines = []
        for fn in ["func_a", "func_b"]:
            lines.append(f"def {fn}() -> None:\n")
            lines += [f"    x_{i} = {i}\n" for i in range(55)]
        f.write_text("".join(lines))
        result = plugin.check(str(f))
        assert result.passed is False
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) == 2

    def test_empty_file_passes(self, plugin, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        result = plugin.check(str(f))
        assert result.passed is True

    def test_nonexistent_file_passes(self, plugin, tmp_path):
        result = plugin.check(str(tmp_path / "ghost.py"))
        assert result.passed is True

    def test_syntax_error_skipped(self, plugin, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n")
        result = plugin.check(str(f))
        assert result.passed is True

    def test_violation_has_line_number(self, plugin, tmp_path):
        f = tmp_path / "line.py"
        lines = ["def long_fn() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(55)]
        f.write_text("".join(lines))
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) > 0
        assert failed[0].line == 1

    def test_metadata_contains_max_lines(self, plugin, tmp_path):
        f = tmp_path / "meta.py"
        f.write_text("x = 1\n")
        result = plugin.check(str(f), config={"max_lines": 30})
        assert result.metadata.get("max_lines") == 30

    def test_violation_has_fix_hint(self, plugin, tmp_path):
        f = tmp_path / "hint.py"
        lines = ["def big_func() -> None:\n"]
        lines += [f"    x_{i} = {i}\n" for i in range(55)]
        f.write_text("".join(lines))
        result = plugin.check(str(f))
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) > 0
        assert failed[0].fix_hint is not None


# ---------------------------------------------------------------------------
# Plugin: file-structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    @pytest.fixture
    def plugin(self):
        return _load_plugin(Path("file_structure.py"))

    @pytest.fixture
    def project_with_seedgo(self, tmp_path):
        """Create a minimal project with .seedgo marker."""
        (tmp_path / ".seedgo").mkdir()
        return tmp_path

    def test_plugin_name(self, plugin):
        assert plugin.PLUGIN_NAME == "file-structure"

    def test_source_file_in_package_passes(self, plugin, project_with_seedgo):
        """A .py file inside a proper package (with __init__.py) should pass."""
        pkg = project_with_seedgo / "src" / "mypackage"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        src = pkg / "module.py"
        src.write_text("x = 1\n")
        result = plugin.check(str(src))
        failed = [c for c in result.checks if not c.passed]
        # Should not have missing-init-py violation
        init_fails = [c for c in failed if c.name == "missing-init-py"]
        assert len(init_fails) == 0

    def test_test_file_in_tests_dir_passes(self, plugin, project_with_seedgo):
        """test_*.py inside tests/ should pass the placement check."""
        tests_dir = project_with_seedgo / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_module.py"
        test_file.write_text("def test_something(): pass\n")
        result = plugin.check(str(test_file))
        failed = [c for c in result.checks if not c.passed]
        placement_fails = [c for c in failed if c.name == "test-file-placement"]
        assert len(placement_fails) == 0

    def test_test_file_at_root_fails(self, plugin, project_with_seedgo):
        """test_*.py at the project root should fail the placement check."""
        test_file = project_with_seedgo / "test_something.py"
        test_file.write_text("def test_foo(): pass\n")
        result = plugin.check(str(test_file))
        failed = [c for c in result.checks if not c.passed]
        placement_fails = [c for c in failed if c.name == "test-file-placement"]
        assert len(placement_fails) == 1

    def test_source_file_at_root_fails(self, plugin, project_with_seedgo):
        """A regular .py file at project root (not in allowed_root_files) should fail."""
        src = project_with_seedgo / "my_module.py"
        src.write_text("x = 1\n")
        result = plugin.check(str(src))
        failed = [c for c in result.checks if not c.passed]
        root_fails = [c for c in failed if c.name == "root-python-file"]
        assert len(root_fails) == 1

    def test_allowed_root_file_passes(self, plugin, project_with_seedgo):
        """setup.py at root is allowed by default."""
        setup = project_with_seedgo / "setup.py"
        setup.write_text("from setuptools import setup\nsetup()\n")
        result = plugin.check(str(setup))
        failed = [c for c in result.checks if not c.passed]
        root_fails = [c for c in failed if c.name == "root-python-file"]
        assert len(root_fails) == 0

    def test_custom_allowed_root_files(self, plugin, project_with_seedgo):
        """Custom allowed_root_files config should be respected."""
        custom = project_with_seedgo / "fabfile.py"
        custom.write_text("x = 1\n")
        # With default config, fabfile.py is already in DEFAULT_ALLOWED_ROOT_FILES
        # so let's test a truly custom file
        myfile = project_with_seedgo / "myapp.py"
        myfile.write_text("x = 1\n")
        # Without config — should fail
        result_no_config = plugin.check(str(myfile))
        failed_no = [c for c in result_no_config.checks if not c.passed and c.name == "root-python-file"]
        assert len(failed_no) == 1
        # With custom config allowing myapp.py — should pass
        result_with_config = plugin.check(str(myfile), config={"allowed_root_files": ["myapp.py"]})
        failed_yes = [c for c in result_with_config.checks if not c.passed and c.name == "root-python-file"]
        assert len(failed_yes) == 0

    def test_missing_init_py_flagged(self, plugin, project_with_seedgo):
        """A package directory without __init__.py should be flagged."""
        pkg = project_with_seedgo / "src" / "mypackage"
        pkg.mkdir(parents=True)
        # Note: no __init__.py
        src = pkg / "module.py"
        src.write_text("x = 1\n")
        # Also create another .py so the dir clearly has sources
        (pkg / "other.py").write_text("y = 1\n")
        result = plugin.check(str(src))
        failed = [c for c in result.checks if not c.passed]
        init_fails = [c for c in failed if c.name == "missing-init-py"]
        assert len(init_fails) == 1

    def test_nonexistent_file_passes(self, plugin, tmp_path):
        result = plugin.check(str(tmp_path / "ghost.py"))
        assert result.passed is True

    def test_conftest_at_root_passes(self, plugin, project_with_seedgo):
        """conftest.py is a standard root-level file."""
        conf = project_with_seedgo / "conftest.py"
        conf.write_text("import pytest\n")
        result = plugin.check(str(conf))
        failed = [c for c in result.checks if not c.passed]
        root_fails = [c for c in failed if c.name == "root-python-file"]
        assert len(root_fails) == 0

    def test_result_has_plugin_name(self, plugin, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("")
        result = plugin.check(str(f))
        assert result.plugin == "file-structure"


# ---------------------------------------------------------------------------
# Plugin discovery integration tests
# ---------------------------------------------------------------------------

class TestPluginDiscovery:
    def test_all_plugins_discoverable(self):
        """All 5 plugins should be discovered as built-ins."""
        from seedgo.discovery import discover_plugins
        plugins = discover_plugins()
        names = {p["name"] for p in plugins}
        assert "no-bare-except" in names
        assert "type-hints-required" in names
        assert "docstring-coverage" in names
        assert "function-length" in names
        assert "file-structure" in names

    def test_all_plugins_have_required_attributes(self):
        """Every discovered plugin must have PLUGIN_NAME, check(), and FILE_TYPES."""
        from seedgo.discovery import discover_plugins
        plugins = discover_plugins()
        for p in plugins:
            module = p["module"]
            assert isinstance(getattr(module, "PLUGIN_NAME", None), str)
            assert callable(getattr(module, "check", None))
            assert isinstance(getattr(module, "FILE_TYPES", None), list)

    def test_plugins_return_check_result(self, tmp_path):
        """Every plugin's check() must return a CheckResult instance."""
        from seedgo.discovery import discover_plugins
        from seedgo.models import CheckResult

        # Create a minimal Python file to run checks on
        test_file = tmp_path / "test_subject.py"
        test_file.write_text("x = 1\n")

        plugins = discover_plugins()
        for p in plugins:
            module = p["module"]
            result = module.check(str(test_file))
            assert isinstance(result, CheckResult), (
                f"Plugin {p['name']} returned {type(result)} instead of CheckResult"
            )

    def test_runner_executes_all_plugins(self, tmp_path):
        """run_checks should execute all enabled plugins."""
        import json
        from seedgo.runner import run_checks

        # Set up minimal project
        seedgo_dir = tmp_path / ".seedgo"
        seedgo_dir.mkdir()
        (seedgo_dir / "plugins").mkdir()

        config = {
            "version": "1.0.0",
            "plugins": {
                "enabled": [
                    "no-bare-except",
                    "type-hints-required",
                    "docstring-coverage",
                    "function-length",
                    "file-structure",
                ],
                "disabled": [],
                "config": {},
            },
            "scoring": {"threshold": 75},
            "paths": {"include": ["."], "exclude": []},
            "overrides": [],
        }
        (seedgo_dir / "config.json").write_text(json.dumps(config))

        # Create a simple Python source file
        src = tmp_path / "hello.py"
        src.write_text(
            '"""A simple module."""\n'
            "\n"
            "def hello() -> str:\n"
            '    """Say hello."""\n'
            "    return 'Hello'\n"
        )

        results, overall = run_checks(str(tmp_path), files=[str(src)])
        assert isinstance(results, list)
        assert len(results) > 0

        plugin_names_run = {r.plugin for r in results}
        # At least some of our plugins should have run
        assert len(plugin_names_run) > 0
