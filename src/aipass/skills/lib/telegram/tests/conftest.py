# ===================AIPASS====================
# META DATA HEADER
# Name: conftest.py - Telegram skill test configuration
# Date: 2026-06-15
# Version: 1.0.0
# Category: skills/telegram/tests
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-06-15): Initial implementation — prax log redirect + path setup
#
# CODE STANDARDS:
#   - Adds src/ and skill root to sys.path for test imports
# =============================================

"""Telegram skill test configuration."""

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

# Add src/ to path so aipass.* is importable
_src_root = Path(__file__).resolve().parents[5]  # noqa: E402
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

# Add telegram skill root so apps.handlers.* is importable
_skill_root = Path(__file__).resolve().parents[1]  # noqa: E402
if str(_skill_root) not in sys.path:
    sys.path.insert(0, str(_skill_root))


# Telethon stub — telethon is an OPTIONAL runtime dependency (MTProto client),
# deliberately NOT in pyproject so the core stays lightweight (botfather_client.py
# guards it with TELETHON_AVAILABLE). The botfather_client tests mock all Telethon
# classes (patch("telethon.TelegramClient"), etc.), but unittest.mock.patch must
# IMPORT the target's parent module to set the attribute — which raises
# ModuleNotFoundError when telethon isn't installed (e.g. in CI). Register a minimal
# stub so those patch targets resolve. The guard never clobbers a real telethon if
# one is installed. Real FloodWaitError/RPCError classes are required for the
# success/timeout tests, where _send_and_wait imports them but does not patch them.
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
