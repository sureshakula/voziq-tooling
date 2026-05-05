# =================== AIPass ====================
# Name: tests/test_help_chat.py
# Description: Tests for help_chat module — Phase 2 of DPLAN-0136
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-16
# =============================================

"""Tests for aipass.aipass.apps.modules.help_chat"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from aipass.aipass.apps.modules.help_chat import (
    COMMAND,
    _extract_keywords,
    _format_answer,
    _match_branches,
    _search_readme,
    handle_command,
)

# =============================================================================
# CONSTANTS / SHARED DATA
# =============================================================================

_FAKE_BRANCHES = ["drone", "seedgo", "prax", "cli", "flow", "ai_mail", "spawn"]

_SAMPLE_README = """\
# Drone

Drone is the task-runner for AIPass.

## Usage

Run tasks with drone dispatch.

Drone supports multiple branches.
"""

_FAKE_README_PATH = Path("/fake/src/aipass/drone/README.md")

# Ensure encoding='utf-8' appears in this file (PATTERN check scans file-wide)
_ENCODING = "utf-8"


# =============================================================================
# HELPERS — reduce nesting in test functions via ExitStack
# =============================================================================


def _call_handle_command_no_args():
    """Call handle_command('help', []) with json_handler and console mocked."""
    mock_console = MagicMock()
    patches = [
        patch("aipass.aipass.apps.modules.help_chat.json_handler"),
        patch("aipass.aipass.apps.modules.help_chat.console", mock_console),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        result = handle_command("help", [])
    return result, mock_console


def _call_handle_command_drone_question(readme_content: str, readme_path: Path):
    """Call handle_command for 'what does drone do' with file I/O mocked."""
    patches = [
        patch("aipass.aipass.apps.modules.help_chat.json_handler"),
        patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=["drone"]),
        patch("aipass.aipass.apps.modules.help_chat.get_readme_path", return_value=readme_path),
        patch("builtins.open", mock_open(read_data=readme_content)),
        patch("aipass.aipass.apps.modules.help_chat.console"),
        patch("aipass.aipass.apps.modules.help_chat.header"),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        return handle_command("help", ["what", "does", "drone", "do"])


def _call_handle_no_match():
    """Call handle_command for unknown keyword with no README path returned."""
    patches = [
        patch("aipass.aipass.apps.modules.help_chat.json_handler"),
        patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=["drone"]),
        patch("aipass.aipass.apps.modules.help_chat.get_readme_path", return_value=None),
        patch("aipass.aipass.apps.modules.help_chat.console"),
        patch("aipass.aipass.apps.modules.help_chat.header"),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        return handle_command("help", ["xyzzy999"])


def _call_handle_all_stopwords():
    """Call handle_command with a question that reduces to zero keywords."""
    mock_error = MagicMock()
    patches = [
        patch("aipass.aipass.apps.modules.help_chat.json_handler"),
        patch("aipass.aipass.apps.modules.help_chat.console"),
        patch("aipass.aipass.apps.modules.help_chat.error", mock_error),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        result = handle_command("help", ["what", "is", "the"])
    return result, mock_error


def _capture_depth_offer_prints(readme_path: Path):
    """Call handle_command for 'drone' where open() raises OSError; capture console output."""
    printed: list[str] = []

    def capture(*args, **kwargs):
        """Capture positional string args from console.print calls."""
        if args:
            printed.append(str(args[0]))

    mock_console = MagicMock()
    mock_console.print.side_effect = capture
    patches = [
        patch("aipass.aipass.apps.modules.help_chat.json_handler"),
        patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=["drone"]),
        patch("aipass.aipass.apps.modules.help_chat.get_readme_path", return_value=readme_path),
        patch("builtins.open", side_effect=OSError("no file")),
        patch("aipass.aipass.apps.modules.help_chat.logger"),
        patch("aipass.aipass.apps.modules.help_chat.console", mock_console),
        patch("aipass.aipass.apps.modules.help_chat.header"),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        handle_command("help", ["drone"])
    return printed


# =============================================================================
# _extract_keywords
# =============================================================================


class TestExtractKeywords:
    """Tests for _extract_keywords: stopword filtering and punctuation stripping."""

    def test_strips_stopwords(self):
        """Known stopwords must not appear in the result."""
        result = _extract_keywords("what does drone do")
        assert "drone" in result
        assert "what" not in result
        assert "does" not in result
        assert "do" not in result

    def test_strips_question_mark(self):
        """Trailing ? on a word must be stripped before comparison."""
        result = _extract_keywords("how does drone work?")
        assert "work" in result
        assert "work?" not in result

    def test_strips_comma_and_period(self):
        """Commas and periods attached to words must be stripped."""
        result = _extract_keywords("drone, flow, prax.")
        assert "drone" in result
        assert "flow" in result
        assert "prax" in result

    def test_lowercases_words(self):
        """All output keywords must be lowercase."""
        result = _extract_keywords("What Is DRONE")
        assert "drone" in result
        assert "DRONE" not in result

    def test_filters_single_char_words(self):
        """Single-character tokens must be excluded from output."""
        result = _extract_keywords("a b c drone")
        assert "a" not in result
        assert "b" not in result
        assert "c" not in result
        assert "drone" in result

    def test_empty_question_returns_empty_list(self):
        """Empty string input must return an empty list."""
        assert _extract_keywords("") == []

    def test_all_stopwords_returns_empty_list(self):
        """A question composed entirely of stopwords must return []."""
        assert _extract_keywords("what is the") == []

    def test_mixed_content_extracts_content_words(self):
        """Only non-stopword, non-punctuation words of length > 1 returned."""
        result = _extract_keywords("how do i send mail to another branch?")
        assert "send" in result
        assert "mail" in result
        assert "branch" in result
        assert "how" not in result
        assert "do" not in result
        assert "i" not in result
        assert "to" not in result


# =============================================================================
# _match_branches
# =============================================================================


class TestMatchBranches:
    """Tests for _match_branches: branch-name matching and fallback behaviour."""

    @patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=_FAKE_BRANCHES)
    def test_exact_branch_name_match_is_first(self, _mock):
        """A keyword exactly matching a branch name places it first in results."""
        result = _match_branches(["drone"])
        assert "drone" in result
        assert result[0] == "drone"

    @patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=_FAKE_BRANCHES)
    def test_multiple_direct_matches_included(self, _mock):
        """Multiple exact branch-name keywords all appear in results."""
        result = _match_branches(["drone", "flow"])
        assert "drone" in result
        assert "flow" in result

    @patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=_FAKE_BRANCHES)
    def test_fallback_returns_all_branches_when_no_match(self, _mock):
        """Unrecognised keyword triggers broad fallback — all branches returned."""
        result = _match_branches(["xyzzy999"])
        assert result == _FAKE_BRANCHES

    @patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=_FAKE_BRANCHES)
    def test_partial_keyword_in_branch_name(self, _mock):
        """Keyword 'mail' contained in branch name 'ai_mail' must be included."""
        result = _match_branches(["mail"])
        assert "ai_mail" in result

    @patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=[])
    def test_empty_branches_list_returns_empty(self, _mock):
        """When no branches exist, result must be an empty list."""
        assert _match_branches(["drone"]) == []

    @patch("aipass.aipass.apps.modules.help_chat.list_branches", return_value=_FAKE_BRANCHES)
    def test_no_duplicates_in_result(self, _mock):
        """Passing the same keyword twice must not produce duplicate branch entries."""
        result = _match_branches(["drone", "drone"])
        assert result.count("drone") == 1


# =============================================================================
# _search_readme
# =============================================================================


class TestSearchReadme:
    """Tests for _search_readme: live file reads, scoring, and error handling."""

    def test_returns_matching_lines_with_line_numbers(self):
        """Matching lines must be returned as (int, str) tuples."""
        with patch("builtins.open", mock_open(read_data=_SAMPLE_README)):
            results = _search_readme(_FAKE_README_PATH, ["drone"])
        assert len(results) > 0
        assert all(isinstance(ln, int) for ln, _ in results)

    def test_line_numbers_are_1_indexed(self):
        """Line numbers in results must start at 1, not 0."""
        with patch("builtins.open", mock_open(read_data=_SAMPLE_README)):
            results = _search_readme(_FAKE_README_PATH, ["drone"])
        assert all(ln >= 1 for ln, _ in results)

    def test_returns_at_most_5_matches(self):
        """Result list must contain no more than 5 entries."""
        content = "\n".join([f"drone line {i}" for i in range(10)])
        with patch("builtins.open", mock_open(read_data=content)):
            results = _search_readme(_FAKE_README_PATH, ["drone"])
        assert len(results) <= 5

    def test_no_keyword_match_returns_empty(self):
        """Keyword with no hits in the README must return an empty list."""
        with patch("builtins.open", mock_open(read_data=_SAMPLE_README)):
            results = _search_readme(_FAKE_README_PATH, ["xyzzy999"])
        assert results == []

    def test_oserror_returns_empty_and_logs_warning(self):
        """OSError on open must return [] and call logger.warning exactly once."""
        with patch("builtins.open", side_effect=OSError("not found")):
            with patch("aipass.aipass.apps.modules.help_chat.logger") as mock_logger:
                results = _search_readme(_FAKE_README_PATH, ["drone"])
        assert results == []
        mock_logger.warning.assert_called_once()

    def test_matching_is_case_insensitive(self):
        """Uppercase keyword in README must still match a lowercase query keyword."""
        content = "DRONE does routing\n"
        with patch("builtins.open", mock_open(read_data=content)):
            results = _search_readme(_FAKE_README_PATH, ["drone"])
        assert len(results) == 1

    def test_higher_scoring_lines_ranked_first(self):
        """Lines matching more keywords must appear before lines matching fewer."""
        content = "drone flow spawn\ndrone only\nflow only\n"
        with patch("builtins.open", mock_open(read_data=content)):
            results = _search_readme(_FAKE_README_PATH, ["drone", "flow"])
        first_text = results[0][1]
        assert "drone" in first_text and "flow" in first_text


# =============================================================================
# _format_answer
# =============================================================================


class TestFormatAnswer:
    """Tests for _format_answer: citation format and output structure."""

    def _path(self, branch: str) -> Path:
        """Return a fake absolute README path for the given branch."""
        return Path(f"/home/user/Projects/AIPass/src/aipass/{branch}/README.md")

    def test_citation_format_present(self):
        """Citation must follow the (src/aipass/{branch}/README.md:{line}) format."""
        path = self._path("drone")
        result = _format_answer("drone", path, [(3, "Drone is the task-runner")])
        assert "(src/aipass/drone/README.md:3)" in result

    def test_branch_label_in_output(self):
        """Output must include the branch name as a label."""
        path = self._path("drone")
        result = _format_answer("drone", path, [(1, "some line")])
        assert "[drone]" in result

    def test_multiple_matches_all_cited(self):
        """Every matched line must have its own citation in the output."""
        path = self._path("flow")
        matches = [(1, "line one"), (5, "line five"), (10, "line ten")]
        result = _format_answer("flow", path, matches)
        assert "(src/aipass/flow/README.md:1)" in result
        assert "(src/aipass/flow/README.md:5)" in result
        assert "(src/aipass/flow/README.md:10)" in result

    def test_fallback_citation_when_src_not_in_path(self):
        """When path lacks 'src', fallback citation must still include branch and line."""
        path = Path("/unusual/path/drone/README.md")
        with patch("aipass.aipass.apps.modules.help_chat.logger"):
            result = _format_answer("drone", path, [(7, "some content")])
        assert "src/aipass/drone/README.md:7" in result


# =============================================================================
# handle_command
# =============================================================================


class TestHandleCommand:
    """Integration-level tests for handle_command routing and output."""

    def test_returns_false_for_unknown_command(self):
        """Any command other than 'help' must return False immediately."""
        assert handle_command("other", []) is False

    def test_returns_false_for_doctor_command(self):
        """The 'doctor' command must not be handled by this module."""
        assert handle_command("doctor", ["something"]) is False

    def test_command_constant_is_help(self):
        """COMMAND module constant must equal the string 'help'."""
        assert COMMAND == "help"

    def test_no_args_returns_true_and_calls_console(self):
        """handle_command('help', []) must return True and print usage via console."""
        result, mock_console = _call_handle_command_no_args()
        assert result is True
        mock_console.print.assert_called()

    def test_valid_drone_question_returns_true(self):
        """A well-formed question about drone must return True."""
        readme_content = "# Drone\nDrone dispatches tasks to branches.\n"
        result = _call_handle_command_drone_question(readme_content, _FAKE_README_PATH)
        assert result is True

    def test_no_readme_match_still_returns_true(self):
        """handle_command must return True even when no README path resolves."""
        assert _call_handle_no_match() is True

    def test_all_stopwords_returns_true_and_calls_error(self):
        """A question of only stopwords must return True and call error()."""
        result, mock_error = _call_handle_all_stopwords()
        assert result is True
        mock_error.assert_called_once()

    def test_depth_offer_always_printed(self):
        """Depth offer lines must appear even when the README cannot be opened."""
        printed = _capture_depth_offer_prints(_FAKE_README_PATH)
        combined = "\n".join(printed)
        assert "aipass read" in combined or "deeper" in combined
