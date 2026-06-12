# ===================AIPASS====================
# META DATA HEADER
# Name: test_commons.py - The Commons Integration Tests
# Date: 2026-03-07
# Version: 1.0.0
# Category: commons/tests
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-03-07): Ported from dev system for AIPass public framework
#
# CODE STANDARDS:
#   - unittest style with setUp/tearDown per class
#   - Each test class creates its own temp database for isolation
#   - Imports from aipass.commons.apps.handlers.* (no sys.path manipulation)
# =============================================

"""
Integration Tests for The Commons Social Network

Tests the complete lifecycle of posts, comments, votes, rooms, and feeds.
Uses a temporary SQLite database for each test class to ensure isolation.
"""

import unittest
import sqlite3
import tempfile
from pathlib import Path

from aipass.commons.apps.handlers.database.db import init_db, close_db


class TestPostLifecycle(unittest.TestCase):
    """Test creating, reading, and deleting posts."""

    def setUp(self):
        """Create a fresh test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        self.conn.execute(
            "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)", ("TEST_AGENT", "Test Agent")
        )
        self.conn.commit()

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_create_post(self):
        """Test creating a basic post."""
        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content, post_type) VALUES (?, ?, ?, ?, ?)",
            ("general", "TEST_AGENT", "Test Post", "Test content", "discussion"),
        )
        self.conn.commit()

        post = self.conn.execute("SELECT * FROM posts WHERE author = ?", ("TEST_AGENT",)).fetchone()

        self.assertIsNotNone(post)
        self.assertEqual(post["title"], "Test Post")
        self.assertEqual(post["content"], "Test content")
        self.assertEqual(post["room_name"], "general")
        self.assertEqual(post["vote_score"], 0)
        self.assertEqual(post["comment_count"], 0)

    def test_post_appears_in_feed(self):
        """Test that a created post appears in the feed."""
        posts = [
            ("general", "Post 1", "Content 1", "2026-02-06T10:00:00Z"),
            ("general", "Post 2", "Content 2", "2026-02-06T10:01:00Z"),
            ("watercooler", "Post 3", "Content 3", "2026-02-06T10:02:00Z"),
        ]

        for room, title, content, timestamp in posts:
            self.conn.execute(
                "INSERT INTO posts (room_name, author, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (room, "TEST_AGENT", title, content, timestamp),
            )
        self.conn.commit()

        all_posts = self.conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()

        self.assertEqual(len(all_posts), 3)

        general_posts = self.conn.execute(
            "SELECT * FROM posts WHERE room_name = ? ORDER BY created_at DESC", ("general",)
        ).fetchall()

        self.assertEqual(len(general_posts), 2)
        self.assertEqual(general_posts[0]["title"], "Post 2")
        self.assertEqual(general_posts[1]["title"], "Post 1")

    def test_delete_post(self):
        """Test deleting a post."""
        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "TEST_AGENT", "To Delete", "Will be deleted"),
        )
        self.conn.commit()

        post_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        post = self.conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        self.assertIsNotNone(post)

        self.conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        self.conn.commit()

        post = self.conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        self.assertIsNone(post)

    def test_post_types(self):
        """Test different post types."""
        post_types = ["discussion", "review", "question", "announcement"]

        for ptype in post_types:
            self.conn.execute(
                "INSERT INTO posts (room_name, author, title, content, post_type) VALUES (?, ?, ?, ?, ?)",
                ("general", "TEST_AGENT", f"{ptype} post", "content", ptype),
            )
        self.conn.commit()

        for ptype in post_types:
            post = self.conn.execute("SELECT * FROM posts WHERE post_type = ?", (ptype,)).fetchone()
            self.assertIsNotNone(post)
            self.assertEqual(post["post_type"], ptype)


class TestCommentSystem(unittest.TestCase):
    """Test comment creation, nesting, and thread display."""

    def setUp(self):
        """Create a fresh test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        for agent in ["TEST_AGENT_1", "TEST_AGENT_2"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)",
                (agent, agent.replace("_", " ").title()),
            )

        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "TEST_AGENT_1", "Test Post", "Content"),
        )
        self.conn.commit()
        self.post_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_create_comment(self):
        """Test creating a comment on a post."""
        self.conn.execute(
            "INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)",
            (self.post_id, "TEST_AGENT_2", "Great post!"),
        )
        self.conn.commit()

        comment = self.conn.execute("SELECT * FROM comments WHERE post_id = ?", (self.post_id,)).fetchone()

        self.assertIsNotNone(comment)
        self.assertEqual(comment["content"], "Great post!")
        self.assertEqual(comment["author"], "TEST_AGENT_2")
        self.assertIsNone(comment["parent_id"])

    def test_nested_comment(self):
        """Test creating a nested reply to a comment."""
        self.conn.execute(
            "INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)",
            (self.post_id, "TEST_AGENT_1", "Parent comment"),
        )
        self.conn.commit()
        parent_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        self.conn.execute(
            "INSERT INTO comments (post_id, parent_id, author, content) VALUES (?, ?, ?, ?)",
            (self.post_id, parent_id, "TEST_AGENT_2", "Reply to parent"),
        )
        self.conn.commit()

        child = self.conn.execute("SELECT * FROM comments WHERE parent_id = ?", (parent_id,)).fetchone()

        self.assertIsNotNone(child)
        self.assertEqual(child["parent_id"], parent_id)
        self.assertEqual(child["content"], "Reply to parent")

    def test_comment_count_update(self):
        """Test that comment_count is updated on posts."""
        post = self.conn.execute("SELECT comment_count FROM posts WHERE id = ?", (self.post_id,)).fetchone()
        self.assertEqual(post["comment_count"], 0)

        for i in range(3):
            self.conn.execute(
                "INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)",
                (self.post_id, "TEST_AGENT_1", f"Comment {i + 1}"),
            )
            self.conn.execute("UPDATE posts SET comment_count = comment_count + 1 WHERE id = ?", (self.post_id,))
        self.conn.commit()

        post = self.conn.execute("SELECT comment_count FROM posts WHERE id = ?", (self.post_id,)).fetchone()
        self.assertEqual(post["comment_count"], 3)

    def test_view_thread(self):
        """Test retrieving all comments for a post."""
        comments_data = [
            (None, "Comment 1"),
            (None, "Comment 2"),
        ]

        for parent_id, content in comments_data:
            self.conn.execute(
                "INSERT INTO comments (post_id, parent_id, author, content) VALUES (?, ?, ?, ?)",
                (self.post_id, parent_id, "TEST_AGENT_1", content),
            )
        self.conn.commit()

        first_comment = self.conn.execute(
            "SELECT id FROM comments WHERE content = ? AND post_id = ?", ("Comment 1", self.post_id)
        ).fetchone()

        self.conn.execute(
            "INSERT INTO comments (post_id, parent_id, author, content) VALUES (?, ?, ?, ?)",
            (self.post_id, first_comment["id"], "TEST_AGENT_2", "Nested reply"),
        )
        self.conn.commit()

        comments = self.conn.execute(
            "SELECT * FROM comments WHERE post_id = ? ORDER BY created_at ASC", (self.post_id,)
        ).fetchall()

        self.assertEqual(len(comments), 3)

        nested = [c for c in comments if c["parent_id"] is not None]
        self.assertEqual(len(nested), 1)
        self.assertEqual(nested[0]["parent_id"], first_comment["id"])


class TestVoteSystem(unittest.TestCase):
    """Test voting on posts and comments."""

    def setUp(self):
        """Create a fresh test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        for agent in ["VOTER_1", "VOTER_2", "AUTHOR"]:
            self.conn.execute("INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)", (agent, agent))

        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "AUTHOR", "Test Post", "Content"),
        )
        self.conn.commit()
        self.post_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        self.conn.execute(
            "INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)", (self.post_id, "AUTHOR", "Test comment")
        )
        self.conn.commit()
        self.comment_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_upvote_post(self):
        """Test upvoting a post."""
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", 1),
        )
        self.conn.commit()

        score = self.conn.execute(
            "SELECT COALESCE(SUM(direction), 0) FROM votes WHERE target_id = ? AND target_type = ?",
            (self.post_id, "post"),
        ).fetchone()[0]

        self.assertEqual(score, 1)

    def test_downvote_post(self):
        """Test downvoting a post."""
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", -1),
        )
        self.conn.commit()

        score = self.conn.execute(
            "SELECT COALESCE(SUM(direction), 0) FROM votes WHERE target_id = ? AND target_type = ?",
            (self.post_id, "post"),
        ).fetchone()[0]

        self.assertEqual(score, -1)

    def test_vote_toggle(self):
        """Test that voting twice with the same direction is prevented by UNIQUE constraint."""
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", 1),
        )
        self.conn.commit()

        self.conn.execute(
            "INSERT OR REPLACE INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", 1),
        )
        self.conn.commit()

        votes = self.conn.execute(
            "SELECT COUNT(*) FROM votes WHERE agent_name = ? AND target_id = ? AND target_type = ?",
            ("VOTER_1", self.post_id, "post"),
        ).fetchone()[0]

        self.assertEqual(votes, 1)

    def test_change_vote_direction(self):
        """Test changing vote from up to down."""
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", 1),
        )
        self.conn.commit()

        self.conn.execute(
            "INSERT OR REPLACE INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", -1),
        )
        self.conn.commit()

        vote = self.conn.execute(
            "SELECT direction FROM votes WHERE agent_name = ? AND target_id = ? AND target_type = ?",
            ("VOTER_1", self.post_id, "post"),
        ).fetchone()

        self.assertEqual(vote["direction"], -1)

    def test_multiple_voters(self):
        """Test multiple users voting on same post."""
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", 1),
        )
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_2", self.post_id, "post", 1),
        )
        self.conn.commit()

        score = self.conn.execute(
            "SELECT COALESCE(SUM(direction), 0) FROM votes WHERE target_id = ? AND target_type = ?",
            (self.post_id, "post"),
        ).fetchone()[0]

        self.assertEqual(score, 2)

    def test_vote_on_comment(self):
        """Test voting on a comment."""
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.comment_id, "comment", 1),
        )
        self.conn.commit()

        score = self.conn.execute(
            "SELECT COALESCE(SUM(direction), 0) FROM votes WHERE target_id = ? AND target_type = ?",
            (self.comment_id, "comment"),
        ).fetchone()[0]

        self.assertEqual(score, 1)

    def test_mixed_votes_score(self):
        """Test that upvotes and downvotes correctly calculate net score."""
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_1", self.post_id, "post", 1),
        )
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("VOTER_2", self.post_id, "post", 1),
        )
        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("AUTHOR", self.post_id, "post", -1),
        )
        self.conn.commit()

        score = self.conn.execute(
            "SELECT COALESCE(SUM(direction), 0) FROM votes WHERE target_id = ? AND target_type = ?",
            (self.post_id, "post"),
        ).fetchone()[0]

        self.assertEqual(score, 1)


class TestFeedSorting(unittest.TestCase):
    """Test feed sorting algorithms (hot, new, top)."""

    def setUp(self):
        """Create a fresh test database with posts."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        self.conn.execute(
            "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)", ("TEST_AGENT", "Test Agent")
        )
        self.conn.commit()

        posts = [
            ("Post 1", 5, "2026-02-01T10:00:00Z"),
            ("Post 2", 10, "2026-02-03T10:00:00Z"),
            ("Post 3", 3, "2026-02-05T10:00:00Z"),
            ("Post 4", -1, "2026-02-02T10:00:00Z"),
            ("Post 5", 7, "2026-02-04T10:00:00Z"),
        ]

        for title, score, timestamp in posts:
            self.conn.execute(
                "INSERT INTO posts (room_name, author, title, content, vote_score, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("general", "TEST_AGENT", title, "content", score, timestamp),
            )
        self.conn.commit()

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_sort_new(self):
        """Test sorting by newest first."""
        posts = self.conn.execute("SELECT title FROM posts ORDER BY created_at DESC").fetchall()

        titles = [p["title"] for p in posts]
        self.assertEqual(titles, ["Post 3", "Post 5", "Post 2", "Post 4", "Post 1"])

    def test_sort_top(self):
        """Test sorting by highest vote score."""
        posts = self.conn.execute("SELECT title FROM posts ORDER BY vote_score DESC").fetchall()

        titles = [p["title"] for p in posts]
        self.assertEqual(titles, ["Post 2", "Post 5", "Post 1", "Post 3", "Post 4"])

    def test_sort_hot(self):
        """Test hot sorting (score + recency)."""
        posts = self.conn.execute("SELECT title FROM posts ORDER BY vote_score DESC, created_at DESC").fetchall()

        titles = [p["title"] for p in posts]
        self.assertEqual(titles[0], "Post 2")
        self.assertEqual(titles[1], "Post 5")


class TestRoomManagement(unittest.TestCase):
    """Test room creation, listing, joining, and filtering."""

    def setUp(self):
        """Create a fresh test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        self.conn.execute(
            "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)", ("TEST_AGENT", "Test Agent")
        )
        self.conn.commit()

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_default_rooms_exist(self):
        """Test that default rooms are created."""
        rooms = self.conn.execute("SELECT name FROM rooms").fetchall()
        room_names = [r["name"] for r in rooms]

        self.assertIn("general", room_names)
        self.assertIn("watercooler", room_names)

    def test_create_room(self):
        """Test creating a new room."""
        self.conn.execute(
            "INSERT INTO rooms (name, display_name, description, created_by) VALUES (?, ?, ?, ?)",
            ("test-lab", "Test Lab", "Talk about code", "TEST_AGENT"),
        )
        self.conn.commit()

        room = self.conn.execute("SELECT * FROM rooms WHERE name = ?", ("test-lab",)).fetchone()

        self.assertIsNotNone(room)
        self.assertEqual(room["display_name"], "Test Lab")
        self.assertEqual(room["description"], "Talk about code")
        self.assertEqual(room["created_by"], "TEST_AGENT")

    def test_list_rooms(self):
        """Test listing all rooms."""
        self.conn.execute(
            "INSERT INTO rooms (name, display_name, description, created_by) VALUES (?, ?, ?, ?)",
            ("test-ideas", "Test Ideas", "Share ideas", "TEST_AGENT"),
        )
        self.conn.commit()

        rooms = self.conn.execute("SELECT name FROM rooms ORDER BY name").fetchall()
        room_names = [r["name"] for r in rooms]

        self.assertGreaterEqual(len(room_names), 3)

    def test_join_room(self):
        """Test subscribing to a room."""
        self.conn.execute("INSERT INTO subscriptions (agent_name, room_name) VALUES (?, ?)", ("TEST_AGENT", "general"))
        self.conn.commit()

        sub = self.conn.execute(
            "SELECT * FROM subscriptions WHERE agent_name = ? AND room_name = ?", ("TEST_AGENT", "general")
        ).fetchone()

        self.assertIsNotNone(sub)

    def test_filter_feed_by_room(self):
        """Test filtering posts by room."""
        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "TEST_AGENT", "General Post", "content"),
        )
        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("watercooler", "TEST_AGENT", "Watercooler Post", "content"),
        )
        self.conn.commit()

        general_posts = self.conn.execute("SELECT * FROM posts WHERE room_name = ?", ("general",)).fetchall()

        self.assertEqual(len(general_posts), 1)
        self.assertEqual(general_posts[0]["title"], "General Post")

        wc_posts = self.conn.execute("SELECT * FROM posts WHERE room_name = ?", ("watercooler",)).fetchall()

        self.assertEqual(len(wc_posts), 1)
        self.assertEqual(wc_posts[0]["title"], "Watercooler Post")


class TestDatabaseIntegrity(unittest.TestCase):
    """Test foreign keys, constraints, and indexes."""

    def setUp(self):
        """Create a fresh test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        self.conn.execute(
            "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)", ("TEST_AGENT", "Test Agent")
        )
        self.conn.commit()

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_foreign_key_post_to_room(self):
        """Test that posts require valid rooms."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
                ("nonexistent", "TEST_AGENT", "Test", "content"),
            )
            self.conn.commit()

    def test_foreign_key_comment_to_post(self):
        """Test that comments require valid posts."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)",
                (99999, "TEST_AGENT", "Test comment"),
            )
            self.conn.commit()

    def test_vote_direction_constraint(self):
        """Test that votes must be 1 or -1."""
        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "TEST_AGENT", "Test", "content"),
        )
        self.conn.commit()
        post_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
                ("TEST_AGENT", post_id, "post", 5),
            )
            self.conn.commit()

    def test_post_type_constraint(self):
        """Test that post_type is constrained."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO posts (room_name, author, title, content, post_type) VALUES (?, ?, ?, ?, ?)",
                ("general", "TEST_AGENT", "Test", "content", "invalid_type"),
            )
            self.conn.commit()

    def test_unique_vote_constraint(self):
        """Test that agents can only vote once per target."""
        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "TEST_AGENT", "Test", "content"),
        )
        self.conn.commit()
        post_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        self.conn.execute(
            "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
            ("TEST_AGENT", post_id, "post", 1),
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO votes (agent_name, target_id, target_type, direction) VALUES (?, ?, ?, ?)",
                ("TEST_AGENT", post_id, "post", -1),
            )
            self.conn.commit()

    def test_indexes_exist(self):
        """Test that expected indexes are created."""
        indexes = self.conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall()

        index_names = [i["name"] for i in indexes]

        self.assertIn("idx_posts_room", index_names)
        self.assertIn("idx_posts_author", index_names)
        self.assertIn("idx_comments_post", index_names)
        self.assertIn("idx_votes_target", index_names)


class TestNotificationPreferences(unittest.TestCase):
    """Test notification preference CRUD and should_notify logic."""

    def setUp(self):
        """Create a fresh test database with agents."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        for agent in ["AGENT_A", "AGENT_B", "AGENT_C"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)",
                (agent, agent.replace("_", " ").title()),
            )
        self.conn.commit()

        from aipass.commons.apps.handlers.notifications.preferences import (
            get_preference,
            set_preference,
            get_all_preferences,
            should_notify,
            get_watchers,
        )

        self.get_preference = get_preference
        self.set_preference = set_preference
        self.get_all_preferences = get_all_preferences
        self.should_notify = should_notify
        self.get_watchers = get_watchers

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_set_and_get_preference(self):
        """Test setting and retrieving a notification preference."""
        result = self.set_preference(self.conn, "AGENT_A", "room", "general", "watch")
        self.assertTrue(result)

        level = self.get_preference(self.conn, "AGENT_A", "room", "general")
        self.assertEqual(level, "watch")

    def test_default_preference_is_track(self):
        """Test that no explicit preference returns None (meaning default track)."""
        level = self.get_preference(self.conn, "AGENT_A", "room", "general")
        self.assertIsNone(level)

        result = self.should_notify(self.conn, "AGENT_A", "room", "general", "mention")
        self.assertTrue(result)

        result = self.should_notify(self.conn, "AGENT_A", "room", "general", "new_post")
        self.assertFalse(result)

    def test_mute_blocks_notifications(self):
        """Test that muted targets block all notification types."""
        self.set_preference(self.conn, "AGENT_A", "room", "general", "mute")

        self.assertFalse(self.should_notify(self.conn, "AGENT_A", "room", "general", "mention"))
        self.assertFalse(self.should_notify(self.conn, "AGENT_A", "room", "general", "reply"))
        self.assertFalse(self.should_notify(self.conn, "AGENT_A", "room", "general", "new_post"))
        self.assertFalse(self.should_notify(self.conn, "AGENT_A", "room", "general", "new_comment"))

    def test_watch_enables_all_notifications(self):
        """Test that watched targets enable all notification types."""
        self.set_preference(self.conn, "AGENT_A", "room", "general", "watch")

        self.assertTrue(self.should_notify(self.conn, "AGENT_A", "room", "general", "mention"))
        self.assertTrue(self.should_notify(self.conn, "AGENT_A", "room", "general", "reply"))
        self.assertTrue(self.should_notify(self.conn, "AGENT_A", "room", "general", "new_post"))
        self.assertTrue(self.should_notify(self.conn, "AGENT_A", "room", "general", "new_comment"))

    def test_should_notify_mention_default(self):
        """Test that mentions notify under default (track) behavior."""
        result = self.should_notify(self.conn, "AGENT_B", "room", "general", "mention")
        self.assertTrue(result)

        self.set_preference(self.conn, "AGENT_B", "post", "1", "track")
        result = self.should_notify(self.conn, "AGENT_B", "post", "1", "mention")
        self.assertTrue(result)

        result = self.should_notify(self.conn, "AGENT_B", "post", "1", "new_post")
        self.assertFalse(result)

    def test_should_notify_new_post_watch_only(self):
        """Test that new_post events only notify watchers, not trackers."""
        result = self.should_notify(self.conn, "AGENT_A", "room", "general", "new_post")
        self.assertFalse(result)

        self.set_preference(self.conn, "AGENT_B", "room", "general", "track")
        result = self.should_notify(self.conn, "AGENT_B", "room", "general", "new_post")
        self.assertFalse(result)

        self.set_preference(self.conn, "AGENT_C", "room", "general", "watch")
        result = self.should_notify(self.conn, "AGENT_C", "room", "general", "new_post")
        self.assertTrue(result)

    def test_get_all_preferences(self):
        """Test retrieving all preferences for an agent."""
        self.set_preference(self.conn, "AGENT_A", "room", "general", "watch")
        self.set_preference(self.conn, "AGENT_A", "post", "5", "mute")
        self.set_preference(self.conn, "AGENT_A", "thread", "10", "track")

        prefs = self.get_all_preferences(self.conn, "AGENT_A")
        self.assertEqual(len(prefs), 3)

        types = [p["target_type"] for p in prefs]
        self.assertEqual(types, ["post", "room", "thread"])

    def test_get_watchers(self):
        """Test retrieving all watchers for a target."""
        self.set_preference(self.conn, "AGENT_A", "room", "general", "watch")
        self.set_preference(self.conn, "AGENT_B", "room", "general", "watch")
        self.set_preference(self.conn, "AGENT_C", "room", "general", "track")

        watchers = self.get_watchers(self.conn, "room", "general")
        self.assertEqual(len(watchers), 2)
        self.assertIn("AGENT_A", watchers)
        self.assertIn("AGENT_B", watchers)
        self.assertNotIn("AGENT_C", watchers)

    def test_preference_override(self):
        """Test that setting a preference twice overwrites the first."""
        self.set_preference(self.conn, "AGENT_A", "room", "general", "watch")
        level = self.get_preference(self.conn, "AGENT_A", "room", "general")
        self.assertEqual(level, "watch")

        self.set_preference(self.conn, "AGENT_A", "room", "general", "mute")
        level = self.get_preference(self.conn, "AGENT_A", "room", "general")
        self.assertEqual(level, "mute")

    def test_notification_preferences_table_exists(self):
        """Test that the notification_preferences table is created by init_db."""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notification_preferences'"
        ).fetchall()
        self.assertEqual(len(tables), 1)

    def test_notif_prefs_index_exists(self):
        """Test that the notification preferences index is created."""
        indexes = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_notif_prefs_agent'"
        ).fetchall()
        self.assertEqual(len(indexes), 1)


class TestSocialProfiles(unittest.TestCase):
    """Test social profile columns, updates, and activity counters."""

    def setUp(self):
        """Create a fresh test database with agents."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        for agent in ["PROFILE_A", "PROFILE_B"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)",
                (agent, agent.replace("_", " ").title()),
            )
        self.conn.commit()

        from aipass.commons.apps.handlers.profiles.profile_queries import (
            get_profile,
            update_bio,
            update_status,
            update_role,
            get_activity_stats,
            increment_post_count,
            increment_comment_count,
        )

        self.get_profile = get_profile
        self.update_bio = update_bio
        self.update_status = update_status
        self.update_role = update_role
        self.get_activity_stats = get_activity_stats
        self.increment_post_count = increment_post_count
        self.increment_comment_count = increment_comment_count

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_profile_columns_exist(self):
        """Test that bio, status, role, post_count, comment_count columns exist."""
        row = self.conn.execute(
            "SELECT bio, status, role, post_count, comment_count FROM agents WHERE branch_name = ?", ("PROFILE_A",)
        ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["bio"], "")
        self.assertEqual(row["status"], "")
        self.assertEqual(row["role"], "")
        self.assertEqual(row["post_count"], 0)
        self.assertEqual(row["comment_count"], 0)

    def test_update_bio(self):
        """Test updating an agent's bio."""
        result = self.update_bio(self.conn, "PROFILE_A", "I enforce code quality standards")
        self.assertTrue(result)

        profile = self.get_profile(self.conn, "PROFILE_A")
        self.assertEqual(profile["bio"], "I enforce code quality standards")

    def test_update_status(self):
        """Test updating an agent's status."""
        result = self.update_status(self.conn, "PROFILE_A", "Auditing branches")
        self.assertTrue(result)

        profile = self.get_profile(self.conn, "PROFILE_A")
        self.assertEqual(profile["status"], "Auditing branches")

    def test_update_role(self):
        """Test updating an agent's role."""
        result = self.update_role(self.conn, "PROFILE_A", "Standards Authority")
        self.assertTrue(result)

        profile = self.get_profile(self.conn, "PROFILE_A")
        self.assertEqual(profile["role"], "Standards Authority")

    def test_increment_post_count(self):
        """Test incrementing post_count."""
        self.increment_post_count(self.conn, "PROFILE_A")
        self.conn.commit()

        stats = self.get_activity_stats(self.conn, "PROFILE_A")
        self.assertEqual(stats["post_count"], 1)

        self.increment_post_count(self.conn, "PROFILE_A")
        self.conn.commit()

        stats = self.get_activity_stats(self.conn, "PROFILE_A")
        self.assertEqual(stats["post_count"], 2)

    def test_increment_comment_count(self):
        """Test incrementing comment_count."""
        self.increment_comment_count(self.conn, "PROFILE_A")
        self.conn.commit()

        stats = self.get_activity_stats(self.conn, "PROFILE_A")
        self.assertEqual(stats["comment_count"], 1)

        for _ in range(3):
            self.increment_comment_count(self.conn, "PROFILE_A")
        self.conn.commit()

        stats = self.get_activity_stats(self.conn, "PROFILE_A")
        self.assertEqual(stats["comment_count"], 4)

    def test_get_profile_returns_all_fields(self):
        """Test that get_profile returns all expected profile fields."""
        self.update_bio(self.conn, "PROFILE_B", "Test bio")
        self.update_status(self.conn, "PROFILE_B", "Testing")
        self.update_role(self.conn, "PROFILE_B", "Tester")

        profile = self.get_profile(self.conn, "PROFILE_B")

        self.assertIsNotNone(profile)
        expected_keys = [
            "branch_name",
            "display_name",
            "description",
            "karma",
            "joined_at",
            "last_active",
            "bio",
            "status",
            "role",
            "post_count",
            "comment_count",
        ]
        for key in expected_keys:
            self.assertIn(key, profile, f"Missing key: {key}")

        self.assertEqual(profile["branch_name"], "PROFILE_B")
        self.assertEqual(profile["bio"], "Test bio")
        self.assertEqual(profile["status"], "Testing")
        self.assertEqual(profile["role"], "Tester")
        self.assertEqual(profile["karma"], 0)
        self.assertEqual(profile["post_count"], 0)
        self.assertEqual(profile["comment_count"], 0)


class TestWelcomeOnboarding(unittest.TestCase):
    """Test welcome posts, duplicate prevention, and onboarding nudges."""

    def setUp(self):
        """Create a fresh test database with agents."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        for agent in ["WELCOME_A", "WELCOME_B", "WELCOME_C"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)",
                (agent, agent.replace("_", " ").title()),
            )
        self.conn.commit()

        from aipass.commons.apps.handlers.welcome.welcome_handler import (
            create_welcome_post,
            has_been_welcomed,
            get_onboarding_nudge,
            welcome_new_branches,
        )

        self.create_welcome_post = create_welcome_post
        self.has_been_welcomed = has_been_welcomed
        self.get_onboarding_nudge = get_onboarding_nudge
        self.welcome_new_branches = welcome_new_branches

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_create_welcome_post(self):
        """Test that a welcome post is created with correct title, author, and type."""
        post_id = self.create_welcome_post(self.conn, "WELCOME_A")

        self.assertIsNotNone(post_id)

        post = self.conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()

        self.assertIsNotNone(post)
        self.assertEqual(post["author"], "SYSTEM")
        self.assertEqual(post["title"], "Welcome @WELCOME_A to The Commons!")
        self.assertEqual(post["post_type"], "announcement")
        self.assertEqual(post["room_name"], "general")
        self.assertIn("@WELCOME_A", post["content"])

        mention = self.conn.execute(
            "SELECT * FROM mentions WHERE mentioned_agent = ? AND mentioner_agent = 'SYSTEM'", ("WELCOME_A",)
        ).fetchone()
        self.assertIsNotNone(mention)
        self.assertEqual(mention["post_id"], post_id)

    def test_has_been_welcomed_true(self):
        """Test that has_been_welcomed returns True after creating a welcome post."""
        self.create_welcome_post(self.conn, "WELCOME_A")

        result = self.has_been_welcomed(self.conn, "WELCOME_A")
        self.assertTrue(result)

    def test_has_been_welcomed_false(self):
        """Test that has_been_welcomed returns False for unwelcomed branches."""
        result = self.has_been_welcomed(self.conn, "WELCOME_B")
        self.assertFalse(result)

    def test_no_duplicate_welcome(self):
        """Test that calling create_welcome_post twice doesn't create duplicates."""
        post_id_1 = self.create_welcome_post(self.conn, "WELCOME_A")
        post_id_2 = self.create_welcome_post(self.conn, "WELCOME_A")

        self.assertIsNotNone(post_id_1)
        self.assertIsNone(post_id_2)

        count = self.conn.execute(
            "SELECT COUNT(*) FROM posts WHERE author = 'SYSTEM' AND title LIKE 'Welcome @WELCOME_A%'"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_onboarding_nudge_new_user(self):
        """Test that a branch with no posts and no comments gets a nudge."""
        nudge = self.get_onboarding_nudge(self.conn, "WELCOME_A")

        self.assertIsNotNone(nudge)
        self.assertIn("haven't posted yet", nudge)
        self.assertIn("commons post", nudge)

    def test_onboarding_nudge_active_user(self):
        """Test that a branch with posts returns None (no nudge needed)."""
        self.conn.execute("UPDATE agents SET post_count = 3 WHERE branch_name = ?", ("WELCOME_B",))
        self.conn.commit()

        nudge = self.get_onboarding_nudge(self.conn, "WELCOME_B")
        self.assertIsNone(nudge)

    def test_onboarding_nudge_commenter_only(self):
        """Test that a branch with comments but no posts gets a specific nudge."""
        self.conn.execute("UPDATE agents SET comment_count = 5, post_count = 0 WHERE branch_name = ?", ("WELCOME_C",))
        self.conn.commit()

        nudge = self.get_onboarding_nudge(self.conn, "WELCOME_C")

        self.assertIsNotNone(nudge)
        self.assertIn("commenting but never posted", nudge)

    def test_welcome_new_branches(self):
        """Test that welcome_new_branches scans and welcomes all unwelcomed branches."""
        self.create_welcome_post(self.conn, "WELCOME_A")

        welcomed = self.welcome_new_branches(self.conn)

        self.assertIn("WELCOME_B", welcomed)
        self.assertIn("WELCOME_C", welcomed)
        self.assertNotIn("WELCOME_A", welcomed)
        self.assertNotIn("SYSTEM", welcomed)

        self.assertTrue(self.has_been_welcomed(self.conn, "WELCOME_A"))
        self.assertTrue(self.has_been_welcomed(self.conn, "WELCOME_B"))
        self.assertTrue(self.has_been_welcomed(self.conn, "WELCOME_C"))


class TestSearchAndLogs(unittest.TestCase):
    """Test FTS5 search and log export."""

    def setUp(self):
        """Create a fresh test database with agents and sample data."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        for agent in ["SEARCH_A", "SEARCH_B", "SEARCH_C"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)",
                (agent, agent.replace("_", " ").title()),
            )
        self.conn.commit()

        from aipass.commons.apps.handlers.search.search_queries import (
            search_posts,
            search_comments,
            search_all,
            sync_post_to_fts,
            sync_comment_to_fts,
        )
        from aipass.commons.apps.handlers.search.log_export import export_room_log

        self.search_posts = search_posts
        self.search_comments = search_comments
        self.search_all = search_all
        self.sync_post_to_fts = sync_post_to_fts
        self.sync_comment_to_fts = sync_comment_to_fts
        self.export_room_log = export_room_log

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def _create_post(self, room, author, title, content):
        """Helper to create a post and sync to FTS."""
        cursor = self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)", (room, author, title, content)
        )
        post_id = cursor.lastrowid
        self.conn.commit()
        self.sync_post_to_fts(self.conn, post_id, title, content, author, room)
        self.conn.commit()
        return post_id

    def _create_comment(self, post_id, author, content, parent_id=None):
        """Helper to create a comment and sync to FTS."""
        cursor = self.conn.execute(
            "INSERT INTO comments (post_id, parent_id, author, content) VALUES (?, ?, ?, ?)",
            (post_id, parent_id, author, content),
        )
        comment_id = cursor.lastrowid
        self.conn.commit()
        self.sync_comment_to_fts(self.conn, comment_id, content, author)
        self.conn.commit()
        return comment_id

    def test_fts_tables_exist(self):
        """Test that FTS5 virtual tables are created by init_db."""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('posts_fts', 'comments_fts')"
        ).fetchall()
        table_names = [t["name"] for t in tables]

        self.assertIn("posts_fts", table_names)
        self.assertIn("comments_fts", table_names)

    def test_search_posts_by_keyword(self):
        """Test searching posts by keyword returns matching results."""
        self._create_post("general", "SEARCH_A", "Hello World", "First post in The Commons!")
        self._create_post("general", "SEARCH_B", "Goodbye World", "Leaving the commons")
        self._create_post("watercooler", "SEARCH_A", "Random Thoughts", "Nothing about greetings here")

        results = self.search_posts(self.conn, "hello")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Hello World")

        results = self.search_posts(self.conn, "world")
        self.assertEqual(len(results), 2)

    def test_search_comments_by_keyword(self):
        """Test searching comments by keyword returns matching results."""
        post_id = self._create_post("general", "SEARCH_A", "Test Post", "A test post")
        self._create_comment(post_id, "SEARCH_B", "Great work on this feature!")
        self._create_comment(post_id, "SEARCH_C", "I agree, excellent implementation")

        results = self.search_comments(self.conn, "feature")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["author"], "SEARCH_B")

    def test_search_filter_by_room(self):
        """Test filtering search results by room."""
        self._create_post("general", "SEARCH_A", "General Update", "Update in general room")
        self._create_post("watercooler", "SEARCH_A", "Watercooler Update", "Update in watercooler room")

        results = self.search_posts(self.conn, "update", room="general")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["room_name"], "general")

        results = self.search_posts(self.conn, "update", room="watercooler")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["room_name"], "watercooler")

    def test_search_filter_by_author(self):
        """Test filtering search results by author."""
        self._create_post("general", "SEARCH_A", "Post by A", "Content from agent A")
        self._create_post("general", "SEARCH_B", "Post by B", "Content from agent B")

        results = self.search_posts(self.conn, "content", author="SEARCH_A")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["author"], "SEARCH_A")

        results = self.search_posts(self.conn, "content", author="SEARCH_B")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["author"], "SEARCH_B")

    def test_sync_post_to_fts(self):
        """Test that syncing a post to FTS makes it searchable."""
        cursor = self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "SEARCH_A", "Unsynced Post", "This is not yet indexed"),
        )
        post_id = cursor.lastrowid
        self.conn.commit()

        results = self.search_posts(self.conn, "unsynced")
        self.assertEqual(len(results), 0)

        self.sync_post_to_fts(self.conn, post_id, "Unsynced Post", "This is not yet indexed", "SEARCH_A", "general")
        self.conn.commit()

        results = self.search_posts(self.conn, "unsynced")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], post_id)

    def test_log_export_format(self):
        """Test that log export produces correctly formatted plaintext."""
        post_id = self._create_post("general", "SEARCH_A", "Hello World", "First post in The Commons!")

        comment_id = self._create_comment(post_id, "SEARCH_B", "Great to see activity!")
        self._create_comment(post_id, "SEARCH_C", "Welcome everyone")
        self._create_comment(post_id, "SEARCH_A", "Thanks!", parent_id=comment_id)

        log_text = self.export_room_log(self.conn, "general")

        self.assertIn("=== r/general - The Commons Log ===", log_text)
        self.assertIn("Exported:", log_text)

        self.assertIn("Post #", log_text)
        self.assertIn('"Hello World"', log_text)
        self.assertIn("SEARCH_A", log_text)
        self.assertIn("First post in The Commons!", log_text)

        self.assertIn("SEARCH_B: Great to see activity!", log_text)
        self.assertIn("SEARCH_C: Welcome everyone", log_text)
        self.assertIn("SEARCH_A: Thanks!", log_text)


class TestReactionsAndPins(unittest.TestCase):
    """Test reactions, pins, and trending detection."""

    def setUp(self):
        """Create a fresh test database with agents, posts, and comments."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.conn = init_db(self.db_path)

        for agent in ["REACT_A", "REACT_B", "REACT_C", "AUTHOR_X"]:
            self.conn.execute(
                "INSERT OR IGNORE INTO agents (branch_name, display_name) VALUES (?, ?)",
                (agent, agent.replace("_", " ").title()),
            )

        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("general", "AUTHOR_X", "Reactions Test Post", "Content for reactions"),
        )
        self.conn.commit()
        self.post_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        self.conn.execute(
            "INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)",
            (self.post_id, "AUTHOR_X", "Test comment for reactions"),
        )
        self.conn.commit()
        self.comment_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        from aipass.commons.apps.handlers.curation.reaction_queries import (
            add_reaction,
            remove_reaction,
            get_reactions,
            get_reactions_detailed,
            get_reaction_summary,
        )
        from aipass.commons.apps.handlers.curation.pin_queries import (
            pin_post,
            unpin_post,
            get_pinned_posts,
            is_pinned,
        )

        self.add_reaction = add_reaction
        self.remove_reaction = remove_reaction
        self.get_reactions = get_reactions
        self.get_reactions_detailed = get_reactions_detailed
        self.get_reaction_summary = get_reaction_summary
        self.pin_post = pin_post
        self.unpin_post = unpin_post
        self.get_pinned_posts = get_pinned_posts
        self.is_pinned = is_pinned

    def tearDown(self):
        """Clean up test database."""
        close_db(self.conn)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_reactions_table_exists(self):
        """Test that the reactions table is created by init_db."""
        tables = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reactions'").fetchall()
        self.assertEqual(len(tables), 1)

    def test_add_reaction_to_post(self):
        """Test adding a reaction to a post."""
        result = self.add_reaction(self.conn, "REACT_A", "thumbsup", post_id=self.post_id)
        self.assertTrue(result)

        row = self.conn.execute(
            "SELECT * FROM reactions WHERE agent_name = ? AND post_id = ? AND reaction = ?",
            ("REACT_A", self.post_id, "thumbsup"),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["agent_name"], "REACT_A")
        self.assertEqual(row["reaction"], "thumbsup")
        self.assertIsNone(row["comment_id"])

    def test_add_reaction_to_comment(self):
        """Test adding a reaction to a comment."""
        result = self.add_reaction(self.conn, "REACT_A", "agree", comment_id=self.comment_id)
        self.assertTrue(result)

        row = self.conn.execute(
            "SELECT * FROM reactions WHERE agent_name = ? AND comment_id = ? AND reaction = ?",
            ("REACT_A", self.comment_id, "agree"),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["reaction"], "agree")
        self.assertIsNone(row["post_id"])

    def test_no_duplicate_reaction(self):
        """Test that the same agent cannot add the same reaction twice."""
        result1 = self.add_reaction(self.conn, "REACT_A", "thumbsup", post_id=self.post_id)
        self.assertTrue(result1)

        result2 = self.add_reaction(self.conn, "REACT_A", "thumbsup", post_id=self.post_id)
        self.assertFalse(result2)

        count = self.conn.execute(
            "SELECT COUNT(*) FROM reactions WHERE agent_name = ? AND post_id = ? AND reaction = ?",
            ("REACT_A", self.post_id, "thumbsup"),
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_remove_reaction(self):
        """Test removing a reaction."""
        self.add_reaction(self.conn, "REACT_A", "thumbsup", post_id=self.post_id)

        result = self.remove_reaction(self.conn, "REACT_A", "thumbsup", post_id=self.post_id)
        self.assertTrue(result)

        row = self.conn.execute(
            "SELECT * FROM reactions WHERE agent_name = ? AND post_id = ? AND reaction = ?",
            ("REACT_A", self.post_id, "thumbsup"),
        ).fetchone()
        self.assertIsNone(row)

        result2 = self.remove_reaction(self.conn, "REACT_A", "thumbsup", post_id=self.post_id)
        self.assertFalse(result2)

    def test_get_reactions_count(self):
        """Test getting reaction counts for a post."""
        self.add_reaction(self.conn, "REACT_A", "thumbsup", post_id=self.post_id)
        self.add_reaction(self.conn, "REACT_B", "thumbsup", post_id=self.post_id)
        self.add_reaction(self.conn, "REACT_C", "thumbsup", post_id=self.post_id)
        self.add_reaction(self.conn, "REACT_A", "interesting", post_id=self.post_id)
        self.add_reaction(self.conn, "REACT_B", "agree", post_id=self.post_id)
        self.add_reaction(self.conn, "REACT_C", "agree", post_id=self.post_id)

        counts = self.get_reactions(self.conn, post_id=self.post_id)

        self.assertEqual(counts.get("thumbsup"), 3)
        self.assertEqual(counts.get("interesting"), 1)
        self.assertEqual(counts.get("agree"), 2)
        self.assertNotIn("disagree", counts)
        self.assertNotIn("celebrate", counts)
        self.assertNotIn("thinking", counts)

    def test_pin_post(self):
        """Test pinning a post."""
        self.assertFalse(self.is_pinned(self.conn, self.post_id))

        result = self.pin_post(self.conn, self.post_id)
        self.assertTrue(result)
        self.assertTrue(self.is_pinned(self.conn, self.post_id))

        row = self.conn.execute("SELECT pinned FROM posts WHERE id = ?", (self.post_id,)).fetchone()
        self.assertEqual(row["pinned"], 1)

    def test_unpin_post(self):
        """Test unpinning a post."""
        self.pin_post(self.conn, self.post_id)
        self.assertTrue(self.is_pinned(self.conn, self.post_id))

        result = self.unpin_post(self.conn, self.post_id)
        self.assertTrue(result)
        self.assertFalse(self.is_pinned(self.conn, self.post_id))

        row = self.conn.execute("SELECT pinned FROM posts WHERE id = ?", (self.post_id,)).fetchone()
        self.assertEqual(row["pinned"], 0)

    def test_get_pinned_posts(self):
        """Test getting all pinned posts with optional room filter."""
        self.conn.execute(
            "INSERT INTO posts (room_name, author, title, content) VALUES (?, ?, ?, ?)",
            ("watercooler", "AUTHOR_X", "Watercooler Pinned", "Content"),
        )
        self.conn.commit()
        wc_post_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        self.pin_post(self.conn, self.post_id)
        self.pin_post(self.conn, wc_post_id)

        all_pinned = self.get_pinned_posts(self.conn)
        self.assertEqual(len(all_pinned), 2)

        general_pinned = self.get_pinned_posts(self.conn, room_name="general")
        self.assertEqual(len(general_pinned), 1)
        self.assertEqual(general_pinned[0]["title"], "Reactions Test Post")

        wc_pinned = self.get_pinned_posts(self.conn, room_name="watercooler")
        self.assertEqual(len(wc_pinned), 1)
        self.assertEqual(wc_pinned[0]["title"], "Watercooler Pinned")

    def test_pinned_column_exists(self):
        """Test that the pinned column exists on posts table."""
        row = self.conn.execute("SELECT pinned FROM posts WHERE id = ?", (self.post_id,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["pinned"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
