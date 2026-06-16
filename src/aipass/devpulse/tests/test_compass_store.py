# =================== AIPass ====================
# Name: test_compass_store.py
# Description: Tests for the compass SQLite/FTS5 storage core
# Version: 1.0.0
# Created: 2026-06-16
# Modified: 2026-06-16
# =============================================

"""Tests for compass storage core — add/query round-trip, rating filter,
stats, rate, archive, review, and FTS5 BM25 ranking.

Every test uses a tmp_path DB via the ``db_path=`` kwarg — never the real
branch-root compass.db.
"""

import sqlite3

import pytest

from aipass.devpulse.apps.handlers import compass
from aipass.devpulse.apps.handlers.compass import store  # internal probe access only


@pytest.fixture
def db(tmp_path):
    """Return a temp compass DB path (file created lazily on first use)."""
    return tmp_path / "compass.db"


class TestFts5Available:
    """FTS5 must be present for compass to function at all."""

    def test_fts5_compiled_in(self):
        """The FTS5 probe used by _connect succeeds on this interpreter."""
        conn = sqlite3.connect(":memory:")
        try:
            store._verify_fts5(conn)  # should not raise
        finally:
            conn.close()


class TestAddQueryRoundTrip:
    """add → query round-trip: the decision is found and its rating returned."""

    def test_add_returns_id(self, db):
        """add_decision returns a positive integer id."""
        new_id = compass.add_decision(
            "Choosing a storage backend",
            "Use SQLite with FTS5",
            "good",
            db_path=db,
        )
        assert isinstance(new_id, int)
        assert new_id > 0

    def test_query_finds_added_decision_with_rating(self, db):
        """A keyword query finds the added decision and returns its rating + fields."""
        compass.add_decision(
            "Choosing a storage backend for compass",
            "Use SQLite with FTS5 instead of ChromaDB",
            "good",
            note="Lighter, no heavy deps",
            tags="storage,sqlite",
            db_path=db,
        )
        results = compass.query_decisions("sqlite", db_path=db)
        assert len(results) == 1
        hit = results[0]
        assert hit["rating"] == "good"
        assert "SQLite" in hit["decision"]
        assert hit["context"].startswith("Choosing a storage backend")
        # Useful fields are present.
        for field in ("id", "created", "note", "tags", "source", "status", "times_surfaced"):
            assert field in hit

    def test_query_matches_on_tags_and_note(self, db):
        """FTS search matches terms that only appear in the note or tags columns."""
        compass.add_decision(
            "Picking a search ranking",
            "BM25 ranking",
            "interesting",
            note="relevance ordering matters",
            tags="ranking,fts5",
            db_path=db,
        )
        # 'relevance' only appears in the note; 'ranking' in tags + context.
        assert len(compass.query_decisions("relevance", db_path=db)) == 1
        assert len(compass.query_decisions("ranking", db_path=db)) == 1

    def test_created_date_is_stamped(self, db):
        """add_decision stamps the supplied created date."""
        compass.add_decision("ctx", "dec", "good", created="2026-06-16", db_path=db)
        hit = compass.query_decisions("ctx", db_path=db)[0]
        assert hit["created"] == "2026-06-16"

    def test_query_increments_times_surfaced(self, db):
        """Each query increments times_surfaced for the returned rows."""
        compass.add_decision("surfacing test context", "a decision", "good", db_path=db)
        first = compass.query_decisions("surfacing", db_path=db)[0]
        assert first["times_surfaced"] == 1
        second = compass.query_decisions("surfacing", db_path=db)[0]
        assert second["times_surfaced"] == 2


class TestRatingFilter:
    """query rating filter returns only matching-rated rows."""

    def test_rating_filter_returns_only_bad(self, db):
        """rating='bad' returns only the bad-rated decision."""
        compass.add_decision("auth approach alpha", "store passwords in plaintext", "bad", db_path=db)
        compass.add_decision("auth approach beta", "hash passwords with bcrypt", "good", db_path=db)
        bad = compass.query_decisions("passwords", rating="bad", db_path=db)
        assert len(bad) == 1
        assert bad[0]["rating"] == "bad"
        assert "plaintext" in bad[0]["decision"]

    def test_invalid_rating_filter_raises(self, db):
        """An unknown rating filter raises ValueError."""
        compass.add_decision("ctx", "dec", "good", db_path=db)
        with pytest.raises(ValueError):
            compass.query_decisions("ctx", rating="terrible", db_path=db)


class TestStats:
    """stats counts by rating, by status, and total."""

    def test_stats_counts(self, db):
        """stats reports correct totals broken down by rating and status."""
        compass.add_decision("c1", "d1", "good", db_path=db)
        compass.add_decision("c2", "d2", "good", db_path=db)
        compass.add_decision("c3", "d3", "bad", db_path=db)
        archived_id = compass.add_decision("c4", "d4", "interesting", db_path=db)
        compass.archive(archived_id, db_path=db)

        s = compass.stats(db_path=db)
        assert s["total"] == 4
        assert s["by_rating"]["good"] == 2
        assert s["by_rating"]["bad"] == 1
        assert s["by_rating"]["interesting"] == 1
        assert s["by_rating"]["impressive"] == 0
        assert s["by_status"]["active"] == 3
        assert s["by_status"]["archived"] == 1

    def test_stats_empty_db(self, db):
        """stats on an empty DB returns zeroed counts for all keys."""
        s = compass.stats(db_path=db)
        assert s["total"] == 0
        assert s["by_rating"] == {"good": 0, "bad": 0, "impressive": 0, "interesting": 0}
        assert s["by_status"] == {"active": 0, "archived": 0}


class TestRate:
    """rate() changes the rating of an existing decision."""

    def test_rate_changes_rating(self, db):
        """rate updates an existing decision's rating and returns True."""
        did = compass.add_decision("revisited choice", "the chosen path", "good", db_path=db)
        assert compass.rate(did, "bad", db_path=db) is True
        hit = compass.query_decisions("revisited", db_path=db)[0]
        assert hit["rating"] == "bad"

    def test_rate_missing_id_returns_false(self, db):
        """rate on a non-existent id returns False (no silent create)."""
        compass.add_decision("ctx", "dec", "good", db_path=db)
        assert compass.rate(9999, "bad", db_path=db) is False

    def test_rate_invalid_rating_raises(self, db):
        """rate with an invalid rating raises ValueError."""
        did = compass.add_decision("ctx", "dec", "good", db_path=db)
        with pytest.raises(ValueError):
            compass.rate(did, "nope", db_path=db)


class TestArchive:
    """archive() removes a decision from active query results."""

    def test_archive_removes_from_active_query(self, db):
        """An archived decision no longer appears in active query results."""
        did = compass.add_decision("archivable context", "some decision", "good", db_path=db)
        assert len(compass.query_decisions("archivable", db_path=db)) == 1
        assert compass.archive(did, db_path=db) is True
        assert compass.query_decisions("archivable", db_path=db) == []

    def test_archive_missing_id_returns_false(self, db):
        """archive on a non-existent id returns False."""
        assert compass.archive(9999, db_path=db) is False


class TestReview:
    """review() surfaces one active entry and stamps last_reviewed."""

    def test_review_returns_entry_and_stamps(self, db):
        """review returns an entry and stamps its last_reviewed date."""
        compass.add_decision("review me context", "a reviewable decision", "good", db_path=db)
        result = compass.review(db_path=db, reviewed_on="2026-06-16")
        assert result is not None
        assert result["last_reviewed"] == "2026-06-16"

    def test_review_prefers_never_reviewed_first(self, db):
        """review surfaces a never-reviewed (NULL last_reviewed) entry before reviewed ones."""
        first = compass.add_decision("alpha context", "alpha decision", "good", db_path=db)
        second = compass.add_decision("beta context", "beta decision", "good", db_path=db)
        # First review picks one of the two NULL-last_reviewed rows and stamps it.
        picked = compass.review(db_path=db, reviewed_on="2026-06-10")
        assert picked is not None
        assert picked["id"] in (first, second)
        # The other row is still NULL → it must be surfaced next (NULL-first).
        other = second if picked["id"] == first else first
        next_picked = compass.review(db_path=db, reviewed_on="2026-06-11")
        assert next_picked is not None
        assert next_picked["id"] == other
        assert next_picked["last_reviewed"] == "2026-06-11"

    def test_review_none_when_empty(self, db):
        """review returns None when there are no active decisions."""
        assert compass.review(db_path=db) is None

    def test_review_skips_archived(self, db):
        """review ignores archived decisions and returns None when only archived exist."""
        did = compass.add_decision("only entry", "decision", "good", db_path=db)
        compass.archive(did, db_path=db)
        assert compass.review(db_path=db) is None


class TestFts5Ranking:
    """FTS5 BM25 ranking returns the more relevant entry first."""

    def test_more_relevant_first(self, db):
        """The entry with denser keyword matches ranks ahead of the sparse one."""
        # Entry A mentions 'caching' once; entry B mentions it repeatedly and
        # in multiple fields → B should rank above A for the term 'caching'.
        compass.add_decision(
            "A general note about performance",
            "We briefly touched on caching",
            "interesting",
            db_path=db,
        )
        compass.add_decision(
            "Caching strategy for the API",
            "Add a caching layer with caching invalidation",
            "good",
            note="caching is the dominant theme here",
            tags="caching,performance",
            db_path=db,
        )
        results = compass.query_decisions("caching", limit=5, db_path=db)
        assert len(results) == 2
        # The caching-heavy entry ranks first.
        assert results[0]["context"].startswith("Caching strategy")
        assert results[0]["rating"] == "good"


class TestInputValidation:
    """Bad input raises, never silently no-ops."""

    def test_empty_context_raises(self, db):
        """add_decision rejects an empty/whitespace context."""
        with pytest.raises(ValueError):
            compass.add_decision("   ", "dec", "good", db_path=db)

    def test_empty_decision_raises(self, db):
        """add_decision rejects an empty decision."""
        with pytest.raises(ValueError):
            compass.add_decision("ctx", "", "good", db_path=db)

    def test_invalid_rating_raises(self, db):
        """add_decision rejects an out-of-range rating."""
        with pytest.raises(ValueError):
            compass.add_decision("ctx", "dec", "meh", db_path=db)

    def test_invalid_source_raises(self, db):
        """add_decision rejects an unknown source."""
        with pytest.raises(ValueError):
            compass.add_decision("ctx", "dec", "good", source="stranger", db_path=db)

    def test_empty_query_raises(self, db):
        """query_decisions rejects an empty query string."""
        with pytest.raises(ValueError):
            compass.query_decisions("   ", db_path=db)

    def test_nonpositive_limit_raises(self, db):
        """query_decisions rejects a non-positive limit."""
        compass.add_decision("ctx", "dec", "good", db_path=db)
        with pytest.raises(ValueError):
            compass.query_decisions("ctx", limit=0, db_path=db)
