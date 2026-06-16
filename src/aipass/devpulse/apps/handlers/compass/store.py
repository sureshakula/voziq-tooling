# =================== AIPass ====================
# Name: store.py
# Description: Compass storage core — SQLite/FTS5 rated decision store
# Version: 1.0.0
# Created: 2026-06-16
# Modified: 2026-06-16
# =============================================

"""Compass storage core — the SQLite/FTS5 layer for rated decisions.

Compass holds short, *rated* decisions (``good | bad | impressive |
interesting``). The rating is the signal: repeat the good, avoid the bad.
This is deliberately separate from the @memory vector store — compass is
truth (curated), @memory is story (ingest-all). See DPLAN-0212.

Storage is one SQLite file with a ``decisions`` table and an FTS5 virtual
table (``decisions_fts``) mirroring ``context, decision, note, tags``. Search
ranks by FTS5 BM25 relevance. Stdlib ``sqlite3`` only — no embeddings, no
ChromaDB, no extra dependencies. FTS5 is compiled into standard CPython's
sqlite3; availability is verified at runtime and a clear error is raised if
it is missing.

Every public function accepts an optional ``db_path`` so tests can point at a
temp file. The default path is resolved relative to the branch root via
``Path(__file__)`` parents — never a hardcoded absolute path.

This module is the storage core ONLY (FPLAN P1). The drone command, slash
command, and maintenance UX are later phases.
"""

import logging
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

# Prefer the prax system logger so compass logs land with the rest of the
# ecosystem; fall back to stdlib logging if prax is unavailable in this
# context (e.g. an isolated test run). Verified working at build time —
# prax import is clean here, so this is the active path.
try:
    from aipass.prax.apps.modules.logger import system_logger as logger
except Exception as _prax_exc:  # pragma: no cover - defensive fallback only
    logger = logging.getLogger("aipass.devpulse.compass")
    logger.info("[compass] prax logger unavailable, using stdlib logging: %s", _prax_exc)

from aipass.devpulse.apps.handlers.json import json_handler

# Branch-root-relative default DB path. store.py lives at
# <branch_root>/apps/handlers/compass/store.py, so parents[3] is the branch
# root. NEVER hardcode an absolute /home/... path here.
_BRANCH_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = _BRANCH_ROOT / "devpulse_json" / "compass" / "compass.db"

VALID_RATINGS = ("good", "bad", "impressive", "interesting")
VALID_SOURCES = ("devpulse", "patrick")
VALID_STATUSES = ("active", "archived")

# Columns we return / surface from the decisions table (everything useful).
_DECISION_COLUMNS = (
    "id",
    "created",
    "context",
    "decision",
    "rating",
    "note",
    "tags",
    "source",
    "score",
    "status",
    "last_reviewed",
    "times_surfaced",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id              INTEGER PRIMARY KEY,
    created         TEXT,
    context         TEXT NOT NULL,
    decision        TEXT NOT NULL,
    rating          TEXT NOT NULL CHECK(rating IN ('good','bad','impressive','interesting')),
    note            TEXT,
    tags            TEXT,
    source          TEXT NOT NULL DEFAULT 'devpulse',
    score           INTEGER,
    status          TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
    last_reviewed   TEXT,
    times_surfaced  INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    context,
    decision,
    note,
    tags,
    content='decisions',
    content_rowid='id'
);

-- Keep the FTS5 mirror in sync with the decisions table via triggers.
CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO decisions_fts(rowid, context, decision, note, tags)
    VALUES (new.id, new.context, new.decision, new.note, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, context, decision, note, tags)
    VALUES ('delete', old.id, old.context, old.decision, old.note, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, context, decision, note, tags)
    VALUES ('delete', old.id, old.context, old.decision, old.note, old.tags);
    INSERT INTO decisions_fts(rowid, context, decision, note, tags)
    VALUES (new.id, new.context, new.decision, new.note, new.tags);
END;
"""


def _verify_fts5(conn: sqlite3.Connection) -> None:
    """Raise a clear error if FTS5 is not compiled into this sqlite3.

    FTS5 ships with standard CPython, but we never assume — a missing module
    must fail loudly, not silently degrade search.
    """
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts5_probe")
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Compass requires SQLite FTS5, which is not available in this "
            "Python's sqlite3 build. Compass cannot operate without it."
        ) from exc


def _resolve_db_path(db_path: Optional[Path | str]) -> Path:
    """Resolve the effective DB path, defaulting to the branch-root location."""
    return Path(db_path) if db_path is not None else DEFAULT_DB_PATH


def _connect(db_path: Optional[Path | str]) -> sqlite3.Connection:
    """Open (and lazily initialise) the compass DB.

    Creates parent directories on first use, verifies FTS5, ensures schema.
    Rows come back as ``sqlite3.Row`` so we can build clean dicts.
    """
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _verify_fts5(conn)
    conn.executescript(_SCHEMA)
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a decisions ``sqlite3.Row`` into a plain dict of useful fields."""
    return {col: row[col] for col in _DECISION_COLUMNS}


def add_decision(
    context: str,
    decision: str,
    rating: str,
    note: Optional[str] = None,
    tags: Optional[str] = None,
    source: str = "devpulse",
    db_path: Optional[Path | str] = None,
    created: Optional[str] = None,
) -> int:
    """Add a rated decision and return its new id.

    Args:
        context: Short description of the situation / the fork.
        decision: Short description of what was chosen.
        rating: One of ``good | bad | impressive | interesting``.
        note: Optional human observation.
        tags: Optional comma-separated tags.
        source: ``devpulse`` or ``patrick`` (default ``devpulse``).
        db_path: Optional DB path override (tests pass a temp path).
        created: Optional ISO date override; defaults to today. This is the
            ONLY place a "today" date is stamped.

    Returns:
        The new row's integer id.

    Raises:
        ValueError: On empty context/decision or invalid rating/source.
    """
    if not context or not context.strip():
        raise ValueError("context must be a non-empty string")
    if not decision or not decision.strip():
        raise ValueError("decision must be a non-empty string")
    if rating not in VALID_RATINGS:
        raise ValueError(f"rating must be one of {VALID_RATINGS}, got {rating!r}")
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {VALID_SOURCES}, got {source!r}")

    stamp = created if created is not None else date.today().isoformat()

    conn = _connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO decisions (created, context, decision, rating, note, tags, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (stamp, context.strip(), decision.strip(), rating, note, tags, source),
        )
        conn.commit()
        if cur.lastrowid is None:  # pragma: no cover - sqlite always sets this on INSERT
            raise RuntimeError("compass: INSERT did not return a rowid")
        new_id = int(cur.lastrowid)
    finally:
        conn.close()

    logger.info("[compass] added decision id=%s rating=%s source=%s", new_id, rating, source)
    json_handler.log_operation("compass_add", {"id": new_id, "rating": rating, "source": source})
    return new_id


def query_decisions(
    query: str,
    rating: Optional[str] = None,
    limit: int = 5,
    db_path: Optional[Path | str] = None,
) -> list[dict]:
    """Search active decisions, ranked by FTS5 BM25 relevance.

    Increments ``times_surfaced`` for every returned row.

    Args:
        query: FTS5 match query (keywords).
        rating: Optional exact rating filter (one of VALID_RATINGS).
        limit: Max rows to return (default 5).
        db_path: Optional DB path override.

    Returns:
        A list of decision dicts (most relevant first). Each dict includes the
        rating and all useful fields.

    Raises:
        ValueError: On empty query, bad rating filter, or non-positive limit.
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    if rating is not None and rating not in VALID_RATINGS:
        raise ValueError(f"rating filter must be one of {VALID_RATINGS}, got {rating!r}")
    if limit <= 0:
        raise ValueError(f"limit must be a positive integer, got {limit!r}")

    select_cols = ", ".join(f"d.{c}" for c in _DECISION_COLUMNS)
    sql = f"""
        SELECT {select_cols}
        FROM decisions_fts f
        JOIN decisions d ON d.id = f.rowid
        WHERE decisions_fts MATCH ?
          AND d.status = 'active'
    """
    params: list = [query.strip()]
    if rating is not None:
        sql += " AND d.rating = ?"
        params.append(rating)
    sql += " ORDER BY bm25(decisions_fts) ASC LIMIT ?"
    params.append(limit)

    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        results = [_row_to_dict(r) for r in rows]
        ids = [r["id"] for r in results]
        if ids:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"UPDATE decisions SET times_surfaced = times_surfaced + 1 WHERE id IN ({placeholders})",
                ids,
            )
            conn.commit()
            # Reflect the increment in the returned dicts without a re-query.
            for r in results:
                r["times_surfaced"] = (r["times_surfaced"] or 0) + 1
    finally:
        conn.close()

    logger.info("[compass] query %r rating=%s -> %d hit(s)", query, rating, len(results))
    return results


def stats(db_path: Optional[Path | str] = None) -> dict:
    """Return decision counts by rating, by status, and the total.

    Returns:
        ``{"total": int, "by_rating": {...}, "by_status": {...}}`` where each
        valid rating/status key is always present (zero when none).
    """
    conn = _connect(db_path)
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])

        by_rating = {r: 0 for r in VALID_RATINGS}
        for row in conn.execute("SELECT rating, COUNT(*) AS n FROM decisions GROUP BY rating"):
            by_rating[row["rating"]] = int(row["n"])

        by_status = {s: 0 for s in VALID_STATUSES}
        for row in conn.execute("SELECT status, COUNT(*) AS n FROM decisions GROUP BY status"):
            by_status[row["status"]] = int(row["n"])
    finally:
        conn.close()

    return {"total": total, "by_rating": by_rating, "by_status": by_status}


def rate(decision_id: int, rating: str, db_path: Optional[Path | str] = None) -> bool:
    """Change the rating of an existing decision.

    Args:
        decision_id: Target decision id.
        rating: New rating (one of VALID_RATINGS).
        db_path: Optional DB path override.

    Returns:
        True if a row was updated, False if no such id.

    Raises:
        ValueError: On invalid rating.
    """
    if rating not in VALID_RATINGS:
        raise ValueError(f"rating must be one of {VALID_RATINGS}, got {rating!r}")

    conn = _connect(db_path)
    try:
        cur = conn.execute("UPDATE decisions SET rating = ? WHERE id = ?", (rating, decision_id))
        conn.commit()
        changed = cur.rowcount > 0
    finally:
        conn.close()

    logger.info("[compass] rate id=%s -> %s (changed=%s)", decision_id, rating, changed)
    json_handler.log_operation("compass_rate", {"id": decision_id, "rating": rating, "changed": changed})
    return changed


def archive(decision_id: int, db_path: Optional[Path | str] = None) -> bool:
    """Archive a decision (sets ``status='archived'``).

    Archived rows drop out of ``query_decisions`` and ``review`` but are never
    deleted — bad decisions are kept on purpose as an avoid-list.

    Args:
        decision_id: Target decision id.
        db_path: Optional DB path override.

    Returns:
        True if a row was updated, False if no such id.
    """
    conn = _connect(db_path)
    try:
        cur = conn.execute("UPDATE decisions SET status = 'archived' WHERE id = ?", (decision_id,))
        conn.commit()
        changed = cur.rowcount > 0
    finally:
        conn.close()

    logger.info("[compass] archive id=%s (changed=%s)", decision_id, changed)
    json_handler.log_operation("compass_archive", {"id": decision_id, "changed": changed})
    return changed


def review(
    db_path: Optional[Path | str] = None,
    reviewed_on: Optional[str] = None,
) -> Optional[dict]:
    """Surface ONE active decision to review and stamp ``last_reviewed``.

    Selection prefers the oldest ``last_reviewed`` (NULL/never-reviewed first);
    among ties it picks randomly. The chosen row's ``last_reviewed`` is stamped
    before returning.

    Args:
        db_path: Optional DB path override.
        reviewed_on: Optional ISO date override for the stamp; defaults to today.

    Returns:
        The reviewed decision dict (with the fresh ``last_reviewed`` stamp), or
        None if there are no active decisions.
    """
    stamp = reviewed_on if reviewed_on is not None else date.today().isoformat()

    conn = _connect(db_path)
    try:
        # NULLs first, then oldest reviewed; random() breaks ties (and orders
        # within the all-NULL group, satisfying "else random").
        row = conn.execute(
            """
            SELECT * FROM decisions
            WHERE status = 'active'
            ORDER BY (last_reviewed IS NOT NULL), last_reviewed ASC, random()
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None

        decision_id = row["id"]
        conn.execute("UPDATE decisions SET last_reviewed = ? WHERE id = ?", (stamp, decision_id))
        conn.commit()

        refreshed = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        result = _row_to_dict(refreshed)
    finally:
        conn.close()

    logger.info("[compass] review surfaced id=%s stamped=%s", result["id"], stamp)
    json_handler.log_operation("compass_review", {"id": result["id"], "last_reviewed": stamp})
    return result
