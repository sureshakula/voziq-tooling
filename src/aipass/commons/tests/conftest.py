# =================== AIPass ====================
# Name: conftest.py
# Description: The Commons test configuration
# Version: 1.1.0
# Created: 2026-03-07
# Modified: 2026-06-15
# =============================================

"""
The Commons - Test Configuration

Provides pytest fixtures for database setup, teardown,
and test isolation using temporary databases.
"""

import os
import shutil
import sqlite3
import tempfile

# Redirect prax logs to temp directory during tests
# Must be set before any prax imports to catch logger initialization
if "AIPASS_TEST_LOG_DIR" not in os.environ:
    os.environ["AIPASS_TEST_LOG_DIR"] = tempfile.mkdtemp(prefix="aipass_test_logs_")


import logging  # noqa: E402

import pytest  # noqa: E402

logger = logging.getLogger(__name__)

try:
    from aipass.prax.apps.modules.logger import system_logger as logger  # noqa: E402, F811
except ImportError:
    logger.warning("[conftest] prax logger unavailable — using stdlib logging")


@pytest.fixture(scope="session")
def _template_db_path(tmp_path_factory):
    """Build the initialized schema+seed DB once per session."""
    from aipass.commons.apps.modules.database import close_db, init_db

    template = tmp_path_factory.mktemp("template") / "template_commons.db"
    conn = init_db(db_path=template)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    close_db(conn)
    return template


@pytest.fixture
def tmp_db_path(tmp_path):
    """
    Provide a temporary database path for test isolation.

    Each test gets its own fresh database file that is
    automatically cleaned up after the test completes.

    Yields:
        Path to temporary database file.
    """
    db_file = tmp_path / "test_commons.db"
    yield db_file


@pytest.fixture
def initialized_db(_template_db_path, tmp_path):
    """
    Provide an initialized temporary database with schema and seed data.

    Copies from a session-scoped template instead of re-running init_db,
    keeping the interface stable (yields sqlite3.Connection).

    Yields:
        sqlite3.Connection to the initialized test database.
    """
    db_file = tmp_path / "test_commons.db"
    shutil.copy2(str(_template_db_path), str(db_file))

    conn = sqlite3.connect(str(db_file), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA synchronous = OFF")
    yield conn
    conn.close()


@pytest.fixture
def sample_data():
    """
    Provide sample_data for tests that need representative data structures.

    Returns a dict with sample post, comment, and agent data
    that mirrors the commons database schema.
    """
    return {
        "post": {
            "title": "Test Post",
            "content": "This is a test post body.",
            "room": "general",
            "author": "TEST_AGENT",
        },
        "comment": {
            "content": "This is a test comment.",
            "post_id": 1,
            "author": "TEST_AGENT",
        },
        "agent": {
            "branch_name": "TEST_AGENT",
            "display_name": "Test Agent",
        },
    }
