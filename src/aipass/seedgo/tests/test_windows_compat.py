# =================== AIPass ====================
# Name: test_windows_compat.py
# Description: Tests for windows_compat_check.py
# Version: 1.0.0
# Created: 2026-05-14
# Modified: 2026-05-14
# =============================================

"""Tests for windows_compat_check — both POSIX-import detection and test-file skipif enforcement."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def _mock_infrastructure(monkeypatch):
    import sys

    mock_logger = MagicMock()
    mock_json_handler = MagicMock()
    mock_json_handler.log_operation = MagicMock(return_value=True)

    prax_mod = MagicMock()
    prax_mod.logger = mock_logger
    monkeypatch.setitem(sys.modules, "aipass.prax", prax_mod)

    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json", json_pkg)
    json_mod = MagicMock()
    json_mod.log_operation = mock_json_handler.log_operation
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json.json_handler", json_mod)

    bypass_pkg = MagicMock()
    bypass_ignore = MagicMock()
    bypass_ignore.get_template_ignore_patterns = MagicMock(return_value=[])
    from aipass.seedgo.apps.handlers.bypass.utils import is_bypassed as real_is_bypassed

    bypass_utils = MagicMock()
    bypass_utils.is_bypassed = real_is_bypassed
    bypass_pkg.utils = bypass_utils
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass", bypass_pkg)
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass.ignore_handler", bypass_ignore)
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass.utils", bypass_utils)

    for mod_name in ["aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check"]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


# ===========================================================================
# Existing POSIX-import detection
# ===========================================================================


def test_clean_file_passes(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("import os\nx = os.path.join('a', 'b')\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True
    assert result["score"] == 100


def test_unguarded_fcntl_import_fails(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("import fcntl\nfcntl.flock(0, 0)\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "import fcntl" in result["checks"][0]["message"]


def test_guarded_fcntl_import_passes(tmp_path):
    f = tmp_path / "guarded.py"
    f.write_text("import sys\ntry:\n    import fcntl\nexcept ImportError:\n    fcntl = None\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_platform_guarded_os_kill_passes(tmp_path):
    f = tmp_path / "guarded_kill.py"
    f.write_text("import os, sys\nif sys.platform != 'win32':\n    os.kill(1, 9)\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_unguarded_os_kill_fails(tmp_path):
    f = tmp_path / "bad_kill.py"
    f.write_text("import os\nos.kill(1, 9)\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.kill()" in result["checks"][0]["message"]


def test_init_file_skipped(tmp_path):
    f = tmp_path / "__init__.py"
    f.write_text("import fcntl\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True
    assert result["checks"][0]["message"] == "File skipped (non-target)"


def test_posix_only_call_fork_fails(tmp_path):
    f = tmp_path / "forker.py"
    f.write_text("import os\npid = os.fork()\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.fork()" in result["checks"][0]["message"]


def test_posix_constant_wnohang_fails(tmp_path):
    f = tmp_path / "waiter.py"
    f.write_text("import os\nflags = os.WNOHANG\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.WNOHANG" in result["checks"][0]["message"]


# ===========================================================================
# Test-file skipif enforcement (new)
# ===========================================================================


def test_unguarded_chmod_in_test_file_fails(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_perms.py"
    f.write_text("import os\n\ndef test_permissions():\n    os.chmod('file', 0o600)\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.chmod()" in result["checks"][0]["message"]


def test_skipif_guarded_chmod_passes(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_perms.py"
    f.write_text(
        "import os, sys, pytest\n\n"
        '@pytest.mark.skipif(sys.platform == "win32", reason="no perms")\n'
        "def test_permissions():\n"
        "    os.chmod('file', 0o600)\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_unguarded_stat_imode_in_test_fails(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_perms.py"
    f.write_text(
        "import os, stat\n\n"
        "def test_file_mode():\n"
        "    mode = stat.S_IMODE(os.stat('file').st_mode)\n"
        "    assert mode == 0o600\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "stat.S_IMODE()" in result["checks"][0]["message"]


def test_unguarded_stat_constant_in_test_fails(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_perms.py"
    f.write_text("import stat\n\ndef test_check_bits():\n    expected = stat.S_IRUSR | stat.S_IWUSR\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "stat.S_IRUSR" in result["checks"][0]["message"]


def test_unguarded_symlink_in_test_fails(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_links.py"
    f.write_text("import os\n\ndef test_symlink():\n    os.symlink('a', 'b')\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.symlink()" in result["checks"][0]["message"]


def test_unguarded_getuid_in_test_fails(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_user.py"
    f.write_text("import os\n\ndef test_uid():\n    uid = os.getuid()\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.getuid()" in result["checks"][0]["message"]


def test_class_level_skipif_guards_all_methods(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_perms.py"
    f.write_text(
        "import os, sys, pytest\n\n"
        '@pytest.mark.skipif(sys.platform == "win32", reason="unix only")\n'
        "class TestPermissions:\n"
        "    def test_chmod(self):\n"
        "        os.chmod('file', 0o600)\n"
        "    def test_getuid(self):\n"
        "        os.getuid()\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_method_level_skipif_in_unguarded_class(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_mixed.py"
    f.write_text(
        "import os, sys, pytest\n\n"
        "class TestMixed:\n"
        '    @pytest.mark.skipif(sys.platform == "win32", reason="unix")\n'
        "    def test_guarded(self):\n"
        "        os.chmod('file', 0o600)\n"
        "    def test_unguarded(self):\n"
        "        os.chmod('file', 0o700)\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.chmod()" in result["checks"][0]["message"]


def test_pytest_mark_skip_unconditional_passes(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_skipped.py"
    f.write_text(
        "import os, pytest\n\n@pytest.mark.skip(reason=\"not yet\")\ndef test_perms():\n    os.chmod('file', 0o600)\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_non_test_file_ignores_chmod(tmp_path):
    f = tmp_path / "handler.py"
    f.write_text("import os\n\ndef set_perms():\n    os.chmod('file', 0o600)\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_inline_platform_guard_in_test_passes(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_guarded_inline.py"
    f.write_text(
        "import os, sys\n\ndef test_perms():\n    if sys.platform != \"win32\":\n        os.chmod('file', 0o600)\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_os_name_skipif_passes(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_osname.py"
    f.write_text(
        "import os, pytest\n\n"
        '@pytest.mark.skipif(os.name != "posix", reason="posix only")\n'
        "def test_chmod():\n"
        "    os.chmod('file', 0o600)\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_non_test_function_in_test_file_ignored(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_helpers.py"
    f.write_text(
        "import os\n\ndef helper_setup():\n    os.chmod('file', 0o600)\n\ndef test_clean():\n    assert True\n"
    )
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True


def test_chown_in_test_fails(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_owner.py"
    f.write_text("import os\n\ndef test_ownership():\n    os.chown('file', 1000, 1000)\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.chown()" in result["checks"][0]["message"]


def test_getgid_in_test_fails(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "test_gid.py"
    f.write_text("import os\n\ndef test_group():\n    gid = os.getgid()\n")
    from aipass.seedgo.apps.handlers.aipass_standards.windows_compat_check import check_module

    result = check_module(str(f))
    assert result["passed"] is False
    assert "os.getgid()" in result["checks"][0]["message"]
