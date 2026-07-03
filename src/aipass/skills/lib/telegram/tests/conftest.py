# =================== AIPass ====================
# Name: conftest.py
# Description: Telegram skill test configuration — path setup and shared fixtures
# Version: 1.0.0
# Created: 2026-06-15
# Modified: 2026-06-29
# =============================================

"""
Telegram skill test configuration.

Sets up sys.path so that both aipass.* (installed package) and the local
apps.handlers.* namespace are importable from tests without a full pip install.
Also stubs the optional telethon dependency and redirects Prax logger output
to a temp dir so test runs don't pollute production log files.
"""

import os
import shutil
import sys
import tempfile
import types
from pathlib import Path
from typing import Generator

if "AIPASS_TEST_LOG_DIR" not in os.environ:
    os.environ["AIPASS_TEST_LOG_DIR"] = tempfile.mkdtemp(prefix="telegram_test_logs_")

import pytest

# sys.path setup is intentional test infrastructure — both entries are needed:
#   _src_root  → resolves aipass.* installed-package imports
#   _skill_root → resolves the local apps.handlers.* namespace used by all tests
_src_root = Path(__file__).resolve().parents[5]
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

_skill_root = Path(__file__).resolve().parents[1]
if str(_skill_root) not in sys.path:
    sys.path.insert(0, str(_skill_root))


# Telethon stub — telethon is an optional dependency (pyproject [telegram] extra).
# In CI or minimal installs it may not be present. botfather_client.py guards with
# TELETHON_AVAILABLE. The tests mock Telethon classes (patch("telethon.TelegramClient")),
# but unittest.mock.patch must IMPORT the parent module — which raises
# ModuleNotFoundError when telethon isn't installed. Register a minimal stub so those
# patch targets resolve. Never clobbers a real telethon if one is installed.
if "telethon" not in sys.modules:
    _telethon_stub = types.ModuleType("telethon")
    _telethon_errors = types.ModuleType("telethon.errors")

    class StubFloodWaitError(Exception):
        def __init__(self, *args: object, seconds: int = 0, **kwargs: object) -> None:
            self.seconds = seconds
            super().__init__(*args)

    class StubRPCError(Exception):
        pass

    # ModuleType attributes are dynamic — assign via setattr so the type checker
    # does not flag assignment to "unknown" module attributes.
    setattr(_telethon_stub, "TelegramClient", type("TelegramClient", (), {}))  # patched per-test
    setattr(_telethon_errors, "FloodWaitError", StubFloodWaitError)
    setattr(_telethon_errors, "RPCError", StubRPCError)
    setattr(_telethon_stub, "errors", _telethon_errors)

    sys.modules["telethon"] = _telethon_stub
    sys.modules["telethon.errors"] = _telethon_errors


@pytest.fixture(autouse=True, scope="session")
def _redirect_prax_logs(tmp_path_factory):
    """Redirect Prax logger output to temp dir during tests.

    Prevents test log output from bleeding into production log files,
    which causes false positives in Trigger's error monitoring.
    The env var AIPASS_TEST_LOG_DIR (set above at module level) is the
    primary redirect — get_system_logs_dir() checks it. This fixture
    also clears cached loggers so they pick up the redirected path.
    """
    import aipass.prax.apps.handlers.logging.direct as direct_mod

    direct_mod._direct_loggers.clear()

    yield

    direct_mod._direct_loggers.clear()


@pytest.fixture
def temp_test_dir() -> Generator[Path, None, None]:
    """Creates temporary directory for testing, cleans up after."""
    test_dir = Path(tempfile.mkdtemp())
    yield test_dir
    if test_dir.exists():
        shutil.rmtree(test_dir)
