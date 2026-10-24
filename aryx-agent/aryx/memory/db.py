"""
ARYx AGENT - SQLite Memory Engine
Manages episodic conversation logs, FTS5 full-text search, and semantic fact extraction.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aryx.config import MEMORY_DB, ensure_aryx_directories


def get_db_connection() -> sqlite3.Connection:
    """Connect to ~/.aryx/memory.db with WAL mode and table initialization."""
    ensure_aryx_directories()
    conn = sqlite3.connect(str(MEMORY_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Initialize episodic and semantic memory tables."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS semantic_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT DEFAULT 'general',
        fact TEXT NOT NULL UNIQUE,
        confidence REAL DEFAULT 1.0,
        created_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS skills_meta (
        name TEXT PRIMARY KEY,
        version INTEGER DEFAULT 1,
        success_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,
        last_used REAL,
        archived INTEGER DEFAULT 0
    );
    """)

    # Try creating FTS5 table for full-text search over episodic history
    try:
        conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_episodes USING fts5(
            content,
            session_id UNINDEXED,
            role UNINDEXED
        );
        """)
    except sqlite3.OperationalError:
        # FTS5 might not be compiled in rare sqlite environments
        pass
    conn.commit()


def save_message(session_id: str, role: str, content: str) -> None:
    """Save message to episodic memory and index in FTS5."""
    if not content.strip():
        return
    try:
        with get_db_connection() as conn:
            now = time.time()
            conn.execute(
                "INSERT INTO episodes (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
            try:
                conn.execute(
                    "INSERT INTO fts_episodes (content, session_id, role) VALUES (?, ?, ?)",
                    (content, session_id, role),
                )
            except Exception:
                pass
            conn.commit()
    except Exception:
        pass


def add_semantic_fact(fact: str, category: str = "preference") -> bool:
    """Add or update an extracted fact in semantic memory."""
    fact = fact.strip()
    if not fact or len(fact) < 5:
        return False
    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO semantic_facts (category, fact, confidence, created_at)
                VALUES (?, ?, 1.0, ?)
                ON CONFLICT(fact) DO UPDATE SET confidence = confidence + 0.1
                """,
                (category, fact, time.time()),
            )
            conn.commit()
            return True
    except Exception:
        return False


def get_semantic_facts(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve learned semantic facts about user preferences and project context."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT id, category, fact, confidence, created_at FROM semantic_facts ORDER BY confidence DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


def search_history(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search episodic past conversations using full-text search."""
    try:
        with get_db_connection() as conn:
            # Try FTS5 search
            try:
                cur = conn.execute(
                    "SELECT session_id, role, content FROM fts_episodes WHERE fts_episodes MATCH ? LIMIT ?",
                    (query, limit),
                )
                return [dict(row) for row in cur.fetchall()]
            except Exception:
                # Fallback to LIKE search
                cur = conn.execute(
                    "SELECT session_id, role, content FROM episodes WHERE content LIKE ? LIMIT ?",
                    (f"%{query}%", limit),
                )
                return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


def extract_quick_facts(user_text: str) -> None:
    """Heuristic extraction of facts like 'I prefer X' or 'I am using Y'."""
    text_lower = user_text.lower()
    triggers = [
        ("i prefer", "preference"),
        ("i always use", "preference"),
        ("my name is", "identity"),
        ("my project uses", "context"),
        ("never use", "rule"),
        ("do not use", "rule"),
    ]
    import re
    for trigger, cat in triggers:
        if trigger in text_lower:
            start_idx = text_lower.find(trigger)
            snippet = user_text[start_idx : start_idx + 120]
            # Split only on end of line or period followed by whitespace/end, not in decimals like 3.11
            sentences = re.split(r"(?<=[a-zA-Z0-9])\.\s+|\n", snippet)
            fact = sentences[0].strip().rstrip(".")
            if len(fact) > 10:
                add_semantic_fact(fact, category=cat)
