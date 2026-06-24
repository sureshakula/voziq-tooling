# =================== AIPass ====================
# Name: test_compass_command.py
# Description: Tests for the compass module command router (FPLAN P2)
# Version: 1.0.0
# Created: 2026-06-16
# Modified: 2026-06-16
# =============================================

"""Tests for the compass command router (FPLAN-0212 P2).

These exercise the thin command layer (``apps/modules/compass.py``) end to
end against a real temp SQLite store via the ``--db`` flag — the same path the
live ``drone @devpulse compass`` invocation takes. Everything goes through the
module entry point (``handle_command``): the round-trip (add -> query -> see
rating) is driven and asserted entirely via the command's own console output,
so the storage handler is never reached into directly.
"""

import re
from pathlib import Path

import pytest

from aipass.devpulse.apps.modules import compass as compass_cmd


@pytest.fixture
def db(tmp_path: Path) -> str:
    """A temp DB path string, passed through to the command via --db."""
    return str(tmp_path / "compass_cmd_test.db")


def _output(capsys) -> str:
    """Combined stdout+stderr (err_console / error() route to stderr)."""
    captured = capsys.readouterr()
    return captured.out + captured.err


def _add(capsys, db, context, decision, rating, *extra) -> int:
    """Drive an add through the command entry point; return the new id.

    The id is parsed from the command's own ``#<id>`` confirmation line — we
    never reach into the storage handler.
    """
    capsys.readouterr()  # isolate this add's output
    compass_cmd.handle_command("compass", ["add", context, decision, "--rating", rating, "--db", db, *extra])
    out = _output(capsys)
    match = re.search(r"#(\d+)", out)
    assert match, f"add did not report a new id; output was: {out!r}"
    return int(match.group(1))


def _query_out(capsys, db, query, *extra) -> str:
    """Run a query via the command and return its captured output (drained)."""
    capsys.readouterr()  # drop anything pending so we only see this query
    compass_cmd.handle_command("compass", ["query", query, "--db", db, *extra])
    return _output(capsys)


def _stats_out(capsys, db) -> str:
    """Run stats via the command and return its captured output (drained)."""
    capsys.readouterr()
    compass_cmd.handle_command("compass", ["stats", "--db", db])
    return _output(capsys)


# ---------------------------------------------------------------------------
# Routing basics
# ---------------------------------------------------------------------------


def test_rejects_unrelated_command():
    """Router returns False for commands that aren't 'compass'."""
    assert compass_cmd.handle_command("watchdog", []) is False


def test_no_args_shows_introspection(capsys):
    """Bare 'compass' shows introspection that mentions compass + subcommands."""
    assert compass_cmd.handle_command("compass", []) is True
    out = _output(capsys).lower()
    assert "compass" in out
    assert "add" in out and "query" in out


def test_help_flag_shows_usage(capsys):
    """--help prints usage covering every subcommand."""
    assert compass_cmd.handle_command("compass", ["--help"]) is True
    out = _output(capsys).lower()
    assert "usage" in out
    for sub in ("add", "query", "stats", "rate", "archive", "review"):
        assert sub in out


def test_unknown_subcommand_errors(capsys):
    """Unknown subcommand surfaces a clean error, still returns True."""
    assert compass_cmd.handle_command("compass", ["bogus"]) is True
    out = _output(capsys).lower()
    assert "bogus" in out or "unknown" in out


# ---------------------------------------------------------------------------
# add -> query round-trip (rating must be visible)
# ---------------------------------------------------------------------------


def test_add_then_query_shows_rating(capsys, db):
    """add stores a decision; query surfaces it with the [GOOD] rating tag."""
    assert (
        compass_cmd.handle_command(
            "compass",
            ["add", "auth fork", "chose JWT over sessions", "--rating", "good", "--note", "worked", "--db", db],
        )
        is True
    )
    add_out = _output(capsys)
    assert "GOOD" in add_out  # rating shown on add too

    assert compass_cmd.handle_command("compass", ["query", "JWT", "--db", db]) is True
    q_out = _output(capsys)
    assert "GOOD" in q_out  # the rating tag is the whole point
    assert "chose JWT over sessions" in q_out
    assert "auth fork" in q_out


def test_query_rating_filter(capsys, db):
    """--rating filters query results to the matching rating only."""
    compass_cmd.handle_command("compass", ["add", "ctx good", "good choice here", "--rating", "good", "--db", db])
    compass_cmd.handle_command("compass", ["add", "ctx bad", "bad choice here", "--rating", "bad", "--db", db])
    capsys.readouterr()  # drain add output

    assert compass_cmd.handle_command("compass", ["query", "choice", "--rating", "bad", "--db", db]) is True
    out = _output(capsys)
    assert "bad choice here" in out
    assert "good choice here" not in out


def test_add_persists_to_store(capsys, db):
    """add persists to the store; a later query surfaces it with its rating."""
    _add(capsys, db, "persist ctx", "persist decision", "interesting")

    out = _query_out(capsys, db, "persist")
    assert "INTERESTING" in out
    assert "persist decision" in out
    assert "1 result(s)" in out


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


def test_stats_reports_counts(capsys, db):
    """stats shows total plus by-rating / by-status breakdown."""
    compass_cmd.handle_command("compass", ["add", "c1", "d1", "--rating", "good", "--db", db])
    compass_cmd.handle_command("compass", ["add", "c2", "d2", "--rating", "bad", "--db", db])
    capsys.readouterr()

    assert compass_cmd.handle_command("compass", ["stats", "--db", db]) is True
    out = _output(capsys).lower()
    assert "total" in out
    assert "2" in out
    assert "good" in out and "bad" in out
    assert "active" in out


# ---------------------------------------------------------------------------
# rate
# ---------------------------------------------------------------------------


def test_rate_changes_rating(capsys, db):
    """rate <id> <rating> re-rates an existing decision."""
    new_id = _add(capsys, db, "rate ctx", "rate decision", "good")

    assert compass_cmd.handle_command("compass", ["rate", str(new_id), "bad", "--db", db]) is True
    out = _output(capsys)
    assert "BAD" in out

    # Confirm the new rating sticks: querying the row now shows [BAD], not [GOOD].
    q_out = _query_out(capsys, db, "rate")
    assert "BAD" in q_out
    assert "GOOD" not in q_out


def test_rate_missing_id_warns(capsys, db):
    """rate on a non-existent id reports 'nothing changed', does not crash."""
    assert compass_cmd.handle_command("compass", ["rate", "999", "good", "--db", db]) is True
    out = _output(capsys).lower()
    assert "999" in out and ("nothing changed" in out or "no decision" in out)


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------


def test_archive_removes_from_query(capsys, db):
    """archive flips status; archived rows drop out of query, stats reflect it."""
    new_id = _add(capsys, db, "arch ctx", "arch decision", "good")

    assert compass_cmd.handle_command("compass", ["archive", str(new_id), "--db", db]) is True
    out = _output(capsys).lower()
    assert "archived" in out

    # Archived rows no longer surface in query...
    q_out = _query_out(capsys, db, "arch")
    assert "0 result(s)" in q_out
    assert "arch decision" not in q_out
    # ...but stats still count them under archived.
    s_out = _stats_out(capsys, db).lower()
    assert "archived" in s_out


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------


def test_review_surfaces_a_decision(capsys, db):
    """review surfaces an active decision with its rating shown."""
    _add(capsys, db, "review ctx", "review decision", "impressive")

    capsys.readouterr()
    assert compass_cmd.handle_command("compass", ["review", "--db", db]) is True
    out = _output(capsys)
    assert "IMPRESSIVE" in out
    assert "review decision" in out


def test_review_empty_store(capsys, db):
    """review on an empty store reports nothing to review (no crash)."""
    assert compass_cmd.handle_command("compass", ["review", "--db", db]) is True
    out = _output(capsys).lower()
    assert "no active" in out or "nothing" in out


# ---------------------------------------------------------------------------
# Error surfacing — must fail loud, never silent
# ---------------------------------------------------------------------------


def test_bad_rating_error_surfaces(capsys, db):
    """add with an invalid rating surfaces the handler's ValueError message."""
    assert compass_cmd.handle_command("compass", ["add", "ctx", "decision", "--rating", "terrible", "--db", db]) is True
    out = _output(capsys).lower()
    assert "rating" in out and "terrible" in out
    # Nothing should have been stored — stats reports total 0.
    assert "total decisions: 0" in _stats_out(capsys, db).lower()


def test_add_requires_rating(capsys, db):
    """add without --rating fails loud."""
    assert compass_cmd.handle_command("compass", ["add", "ctx", "decision", "--db", db]) is True
    out = _output(capsys).lower()
    assert "rating" in out


def test_add_missing_positionals(capsys, db):
    """add with too few positional args shows usage, stores nothing."""
    assert compass_cmd.handle_command("compass", ["add", "only-context", "--rating", "good", "--db", db]) is True
    out = _output(capsys).lower()
    assert "usage" in out
    assert "total decisions: 0" in _stats_out(capsys, db).lower()


def test_query_bad_limit_errors(capsys, db):
    """query with a non-integer --limit fails loud."""
    assert compass_cmd.handle_command("compass", ["query", "anything", "--limit", "abc", "--db", db]) is True
    out = _output(capsys).lower()
    assert "limit" in out


def test_flag_without_value_errors(capsys, db):
    """A flag given without a following value fails loud (no silent swallow)."""
    assert compass_cmd.handle_command("compass", ["query", "x", "--rating"]) is True
    out = _output(capsys).lower()
    assert "rating" in out and "value" in out
