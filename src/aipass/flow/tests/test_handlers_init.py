# =================== AIPass ====================
# Name: test_handlers_init.py
# Description: Tests for handlers/__init__.py branch access guard
# Version: 1.0.0
# Created: 2026-05-12
# Modified: 2026-05-12
# =============================================

"""Tests for handlers/__init__.py — branch access guard."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# The handlers __init__.py runs _guard_branch_access() at import time.
# We import the individual functions after the module is already loaded
# (conftest triggers it through transitive imports).  That sidesteps the
# import-time guard and lets us call each function in isolation.
# ---------------------------------------------------------------------------

from aipass.flow.apps.handlers import (  # noqa: E402
    MY_BRANCH,
    _extract_branch_name,
    _find_real_caller,
    _guard_branch_access,
)


# ===================================================================
# 1. _extract_branch_name
# ===================================================================


class TestExtractBranchName:
    """Extract the branch name from various file paths."""

    def test_flow_branch_path(self):
        """Path containing 'aipass/flow' returns 'flow'."""
        result = _extract_branch_name("/home/user/Projects/AIPass/src/aipass/flow/apps/handlers/foo.py")
        assert result == "flow"

    def test_memory_branch_path(self):
        """Path containing 'aipass/memory' returns 'memory'."""
        result = _extract_branch_name("/home/user/Projects/AIPass/src/aipass/memory/apps/modules/vectorize.py")
        assert result == "memory"

    def test_nexus_branch_path(self):
        """Path containing 'Nexus' returns the segment after it."""
        result = _extract_branch_name("/home/user/Projects/AIPass/Nexus/core/main.py")
        assert result == "core"

    def test_aipass_drone_path(self):
        """Path containing 'aipass/drone' returns 'drone'."""
        result = _extract_branch_name("/home/user/Projects/AIPass/src/aipass/drone/handler.py")
        assert result == "drone"

    def test_unknown_path_returns_unknown(self):
        """Path with no recognised branch marker returns 'unknown'."""
        result = _extract_branch_name("/usr/lib/python3/site-packages/some_lib/util.py")
        assert result == "unknown"

    def test_aipass_at_end_of_path(self):
        """If 'aipass' is the last segment there is no branch name after it."""
        result = _extract_branch_name("/home/user/aipass")
        assert result == "unknown"

    def test_forward_slash_path(self):
        """Forward-slash paths are parsed correctly on all platforms."""
        result = _extract_branch_name("C:/Users/dev/Projects/AIPass/src/aipass/flow/test.py")
        assert result == "flow"


# ===================================================================
# 2. _find_real_caller
# ===================================================================


def _make_frame_info(filename: str, code_context: list[str] | None = None):
    """Create a lightweight stand-in for inspect.FrameInfo."""
    fi = MagicMock()
    fi.filename = filename
    fi.code_context = code_context
    return fi


class TestFindRealCaller:
    """Walk the stack and return the first real (non-internal) file."""

    def test_returns_real_file(self):
        """When the stack contains a real file, return its resolved path and import line."""
        real_file = "/home/user/Projects/AIPass/src/aipass/flow/apps/modules/foo.py"
        # Build a stack: __init__.py (skipped), importlib (skipped), then the real caller
        init_path = str(Path(__file__).resolve().parent.parent / "apps" / "handlers" / "__init__.py")
        frames = [
            _make_frame_info(init_path),
            _make_frame_info("<frozen importlib._bootstrap>"),
            _make_frame_info(real_file, ["from aipass.flow.apps.handlers import something\n"]),
        ]

        with patch("aipass.flow.apps.handlers.inspect.stack", return_value=frames):
            filepath, import_line = _find_real_caller()

        assert filepath is not None
        assert filepath == str(Path(real_file).resolve())
        assert import_line is not None
        assert "from aipass.flow.apps.handlers" in import_line

    def test_skips_importlib_internals(self):
        """Frames with 'importlib' in the filename are skipped."""
        frames = [
            _make_frame_info("/usr/lib/python3/importlib/__init__.py"),
            _make_frame_info("/usr/lib/python3/importlib/_bootstrap.py"),
            _make_frame_info("/home/user/real_script.py", ["import handlers\n"]),
        ]

        with patch("aipass.flow.apps.handlers.inspect.stack", return_value=frames):
            filepath, _ = _find_real_caller()

        assert filepath is not None
        assert "real_script" in filepath

    def test_skips_angle_bracket_filenames(self):
        """Frames with filenames starting with '<' are skipped."""
        frames = [
            _make_frame_info("<string>"),
            _make_frame_info("<stdin>"),
            _make_frame_info("/home/user/caller.py", ["import x\n"]),
        ]

        with patch("aipass.flow.apps.handlers.inspect.stack", return_value=frames):
            filepath, _ = _find_real_caller()

        assert filepath is not None
        assert "caller.py" in filepath

    def test_returns_none_when_no_real_frames(self):
        """When every frame is an internal or angle-bracket frame, return (None, None)."""
        frames = [
            _make_frame_info("<string>"),
            _make_frame_info("<frozen importlib._bootstrap>"),
            _make_frame_info("<stdin>"),
        ]

        with patch("aipass.flow.apps.handlers.inspect.stack", return_value=frames):
            filepath, import_line = _find_real_caller()

        assert filepath is None
        assert import_line is None

    def test_none_code_context(self):
        """When code_context is None, import_line is returned as None."""
        frames = [
            _make_frame_info("/home/user/script.py", None),
        ]

        with patch("aipass.flow.apps.handlers.inspect.stack", return_value=frames):
            filepath, import_line = _find_real_caller()

        assert filepath is not None
        assert import_line is None


# ===================================================================
# 3. _guard_branch_access
# ===================================================================


class TestGuardBranchAccess:
    """Test the import guard logic."""

    def test_allows_same_branch_import(self):
        """Caller from the same branch (flow) is allowed through."""
        caller = "/home/user/Projects/AIPass/src/aipass/flow/apps/modules/runner.py"

        with patch(
            "aipass.flow.apps.handlers._find_real_caller",
            return_value=(caller, "from aipass.flow.apps.handlers import x"),
        ):
            # Should not raise
            _guard_branch_access()

    def test_blocks_external_branch_import(self):
        """Caller from a different branch raises ImportError."""
        caller = "/home/user/Projects/AIPass/src/aipass/drone/apps/modules/dispatcher.py"

        with patch(
            "aipass.flow.apps.handlers._find_real_caller",
            return_value=(caller, "from aipass.flow.apps.handlers import x"),
        ):
            with pytest.raises(ImportError, match="ACCESS DENIED"):
                _guard_branch_access()

    def test_error_message_contains_caller_branch(self):
        """The ImportError message includes the caller's branch name."""
        caller = "/home/user/Projects/AIPass/src/aipass/memory/apps/modules/indexer.py"

        with patch(
            "aipass.flow.apps.handlers._find_real_caller",
            return_value=(caller, "from aipass.flow.apps.handlers import y"),
        ):
            with pytest.raises(ImportError, match="memory"):
                _guard_branch_access()

    def test_error_message_contains_import_line(self):
        """The ImportError message includes the blocked import line."""
        caller = "/home/user/Projects/AIPass/src/aipass/drone/handler.py"
        import_line = "from aipass.flow.apps.handlers.json import json_handler"

        with patch(
            "aipass.flow.apps.handlers._find_real_caller",
            return_value=(caller, import_line),
        ):
            with pytest.raises(ImportError, match="json_handler"):
                _guard_branch_access()

    def test_allows_when_caller_none_with_string_in_stack(self):
        """When caller is None and <string> is in the stack, allow through."""
        string_frame = MagicMock()
        string_frame.filename = "<string>"

        with (
            patch(
                "aipass.flow.apps.handlers._find_real_caller",
                return_value=(None, None),
            ),
            patch(
                "aipass.flow.apps.handlers.inspect.stack",
                return_value=[string_frame],
            ),
        ):
            # Should not raise
            _guard_branch_access()

    def test_allows_when_caller_none_with_stdin_in_stack(self):
        """When caller is None and <stdin> is in the stack, allow through."""
        stdin_frame = MagicMock()
        stdin_frame.filename = "<stdin>"

        with (
            patch(
                "aipass.flow.apps.handlers._find_real_caller",
                return_value=(None, None),
            ),
            patch(
                "aipass.flow.apps.handlers.inspect.stack",
                return_value=[stdin_frame],
            ),
        ):
            # Should not raise
            _guard_branch_access()

    def test_allows_when_caller_none_no_special_frames(self):
        """When caller is None and no special frames exist, allow through (can't determine)."""
        normal_frame = MagicMock()
        normal_frame.filename = "/usr/lib/python3/importlib/_bootstrap.py"

        with (
            patch(
                "aipass.flow.apps.handlers._find_real_caller",
                return_value=(None, None),
            ),
            patch(
                "aipass.flow.apps.handlers.inspect.stack",
                return_value=[normal_frame],
            ),
        ):
            # Should not raise — falls through to the final return
            _guard_branch_access()

    def test_blocked_import_says_unknown_when_no_import_line(self):
        """When import_line is None, the error message says 'unknown'."""
        caller = "/home/user/Projects/AIPass/src/aipass/drone/x.py"

        with patch(
            "aipass.flow.apps.handlers._find_real_caller",
            return_value=(caller, None),
        ):
            with pytest.raises(ImportError, match="unknown"):
                _guard_branch_access()

    def test_my_branch_constant(self):
        """MY_BRANCH is set to 'flow'."""
        assert MY_BRANCH == "flow"

    def test_allows_flow_subpath_with_backslashes(self):
        """Windows-style paths with backslashes still match the flow branch."""
        # The guard replaces backslashes with forward slashes before checking
        caller = "C:\\Users\\dev\\Projects\\AIPass\\src\\aipass\\flow\\apps\\modules\\foo.py"

        with patch(
            "aipass.flow.apps.handlers._find_real_caller",
            return_value=(caller, "import x"),
        ):
            # Should not raise
            _guard_branch_access()
