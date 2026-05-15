# =================== AIPass ====================
# Name: conftest.py
# Description: Shared pytest fixtures for devpulse tests
# Version: 1.1.0
# Created: 2025-11-08
# Modified: 2026-05-15
# =============================================

"""Shared pytest fixtures for cortex tests"""

from unittest.mock import patch

import pytest
import shutil
import tempfile
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_test_dir() -> Generator[Path, None, None]:
    """Creates temporary directory for testing, cleans up after"""
    test_dir = Path(tempfile.mkdtemp())
    yield test_dir
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def sample_test_data() -> dict:
    """Provides sample test data."""
    return {"test_key": "test_value", "sample_data": "example"}


@pytest.fixture
def mock_logger():
    """Mock the prax logger to suppress output during tests."""
    with patch("aipass.prax.logger") as mock_log:
        yield mock_log


@pytest.fixture
def mock_json_handler():
    """Mock json_handler to prevent filesystem writes during tests."""
    with patch("aipass.devpulse.apps.handlers.json.json_handler.log_operation") as mock_json:
        yield mock_json
