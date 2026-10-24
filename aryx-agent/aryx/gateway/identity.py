"""
ARYx AGENT - Gateway identity & session store (Section 16.2).

One human = one identity, no matter how many channels they use.
A Telegram user and a CLI user are the SAME identity once linked,
so memory, skills and config are shared across every channel.

Linking flow (no passwords, no OAuth dance):
  1. CLI:  `aryx gateway link`  -> prints a 6-character code (10 min).
  2. Chat: `/link A7K9P2` on Telegram/WhatsApp/etc.
  3. That channel-user is now bound to the CLI identity.

Tables live in ~/.aryx/gateway.db (SQLite, like the main memory DB).
"""

from __future__ import annotations

import secrets
import sqlite3
import string
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from aryx.gateway.config import GATEWAY_DB

# Readable codes: no 0/O/1/I confusion, still 6 chars (~1.5B combos).
_LINK_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LINK_TTL_SECONDS = 10 * 60

CLI_IDENTITY_ID = "cli"


def get_gateway_db_connection(path: Optional[Path] = None) -> sqlite3.Connection:
    target = Path(path) if path else GATEWAY_DB
    target.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: adapters run in their own threads
    # (Telegram polling, Web UI workers, Discord/Slack callbacks) but
    # share this connection. GatewayCore serialises all access through
    # one re-entrant lock, so the shared connection stays safe.
    conn = sqlite3.connect(str(target), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS identities (
            id TEXT PRIMARY KEY,
            display_name TEXT,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS channel_links (
            channel TEXT NOT NULL,
            channel_user_id TEXT NOT NULL,
            identity_id TEXT NOT NULL,
            PRIMARY KEY (channel, channel_user_id)
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            identity_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            created_at REAL,
            last_active REAL,
            closed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identity_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts REAL
        );
        CREATE TABLE IF NOT EXISTS link_codes (
            code TEXT PRIMARY KEY,
            identity_id TEXT NOT NULL,
            expires_at REAL NOT NULL,
            used INTEGER DEFAULT 0
        );
        """
    )
    conn.commit()


def _now() -> float:
    return time.time()


def create_identity(conn: sqlite3.Connection, display_name: str = "") -> str:
    identity_id = f"id_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO identities (id, display_name, created_at) VALUES (?, ?, ?)",
        (identity_id, display_name, _now()),
    )
    conn.commit()
    return identity_id


def ensure_cli_identity(conn: sqlite3.Connection) -> str:
    """The CLI user is always identity 'cli' (created on first use)."""
    row = conn.execute(
        "SELECT id FROM identities WHERE id = ?", (CLI_IDENTITY_ID,)
    ).fetchone()
    if row:
        return CLI_IDENTITY_ID
    conn.execute(
        "INSERT INTO identities (id, display_name, created_at) VALUES (?, ?, ?)",
        (CLI_IDENTITY_ID, "cli-user", _now()),
    )
    conn.commit()
    return CLI_IDENTITY_ID


def get_identity_for_channel(
    conn: sqlite3.Connection, channel: str, channel_user_id: str
) -> Optional[str]:
    row = conn.execute(
        "SELECT identity_id FROM channel_links WHERE channel = ? AND channel_user_id = ?",
        (channel, str(channel_user_id)),
    ).fetchone()
    return row["identity_id"] if row else None


def get_or_create_identity_for_channel(
    conn: sqlite3.Connection, channel: str, channel_user_id: str, username: str = ""
) -> str:
    """Unlinked channel users get their own identity until /link binds them."""
    existing = get_identity_for_channel(conn, channel, channel_user_id)
    if existing:
        return existing
    identity_id = create_identity(conn, display_name=username or f"{channel}:{channel_user_id}")
    conn.execute(
        "INSERT INTO channel_links (channel, channel_user_id, identity_id) VALUES (?, ?, ?)",
        (channel, str(channel_user_id), identity_id),
    )
    conn.commit()
    return identity_id


def generate_link_code(conn: sqlite3.Connection, identity_id: str) -> str:
    """A fresh 6-character code, valid for 10 minutes, single use."""
    for _ in range(20):  # collision retry; alphabet makes this near-impossible
        code = "".join(secrets.choice(_LINK_ALPHABET) for _ in range(6))
        try:
            conn.execute(
                "INSERT INTO link_codes (code, identity_id, expires_at, used) VALUES (?, ?, ?, 0)",
                (code, identity_id, _now() + LINK_TTL_SECONDS),
            )
            conn.commit()
            return code
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("Could not generate a unique link code")


def consume_link_code(
    conn: sqlite3.Connection, code: str, channel: str, channel_user_id: str
) -> Optional[str]:
    """Bind a channel-user to the code owner's identity. None = bad/expired/used."""
    code = code.strip().upper()
    row = conn.execute(
        "SELECT identity_id, expires_at, used FROM link_codes WHERE code = ?", (code,)
    ).fetchone()
    if not row or row["used"] or row["expires_at"] < _now():
        return None
    identity_id = row["identity_id"]
    conn.execute("UPDATE link_codes SET used = 1 WHERE code = ?", (code,))
    conn.execute(
        "INSERT OR REPLACE INTO channel_links (channel, channel_user_id, identity_id)"
        " VALUES (?, ?, ?)",
        (channel, str(channel_user_id), identity_id),
    )
    conn.commit()
    return identity_id


def get_or_create_session(
    conn: sqlite3.Connection, identity_id: str, channel: str
) -> str:
    """One open session per identity, shared across channels (the point)."""
    row = conn.execute(
        "SELECT id FROM sessions WHERE identity_id = ? AND closed = 0"
        " ORDER BY last_active DESC LIMIT 1",
        (identity_id,),
    ).fetchone()
    if row:
        session_id = row["id"]
        conn.execute(
            "UPDATE sessions SET last_active = ?, channel = ? WHERE id = ?",
            (_now(), channel, session_id),
        )
        conn.commit()
        return session_id
    session_id = f"gw_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO sessions (id, identity_id, channel, created_at, last_active, closed)"
        " VALUES (?, ?, ?, ?, ?, 0)",
        (session_id, identity_id, channel, _now(), _now()),
    )
    conn.commit()
    return session_id


def new_session(conn: sqlite3.Connection, identity_id: str, channel: str) -> str:
    """Close the current session and open a fresh one (/new)."""
    conn.execute(
        "UPDATE sessions SET closed = 1 WHERE identity_id = ? AND closed = 0",
        (identity_id,),
    )
    conn.commit()
    return get_or_create_session(conn, identity_id, channel)


def resume_session(conn: sqlite3.Connection, identity_id: str, channel: str) -> Optional[str]:
    """Reopen the most recent session, even if closed (/resume)."""
    row = conn.execute(
        "SELECT id FROM sessions WHERE identity_id = ? ORDER BY last_active DESC LIMIT 1",
        (identity_id,),
    ).fetchone()
    if not row:
        return None
    session_id = row["id"]
    conn.execute(
        "UPDATE sessions SET closed = 0, last_active = ?, channel = ? WHERE id = ?",
        (_now(), channel, session_id),
    )
    conn.commit()
    return session_id


def save_gateway_message(
    conn: sqlite3.Connection,
    identity_id: str,
    session_id: str,
    channel: str,
    role: str,
    content: str,
) -> None:
    conn.execute(
        "INSERT INTO messages (identity_id, session_id, channel, role, content, ts)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (identity_id, session_id, channel, role, content, _now()),
    )
    conn.execute(
        "UPDATE sessions SET last_active = ? WHERE id = ?", (_now(), session_id)
    )
    conn.commit()


def get_session_history(
    conn: sqlite3.Connection, session_id: str, limit: int = 30
) -> List[Dict[str, str]]:
    """Recent turns for this session, oldest first, for agent context."""
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ?"
        " ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def count_messages_today(conn: sqlite3.Connection, channel: str) -> int:
    day_start = _now() - (_now() % 86400)
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM messages WHERE channel = ? AND ts >= ?",
        (channel, day_start),
    ).fetchone()
    return int(row["n"]) if row else 0
