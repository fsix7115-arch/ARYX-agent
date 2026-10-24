"""
ARYx AGENT - Gateway identity/session tests (Section 16.2).

Covers linking codes (single-use, 10-minute expiry), one shared
session per identity across channels, /new and /resume semantics,
and history ordering. Uses throwaway SQLite files, never ~/.aryx.
"""

import time

from aryx.gateway.identity import (
    consume_link_code,
    ensure_cli_identity,
    generate_link_code,
    get_gateway_db_connection,
    get_or_create_identity_for_channel,
    get_or_create_session,
    get_session_history,
    new_session,
    resume_session,
    save_gateway_message,
)


def _conn(tmp_path):
    return get_gateway_db_connection(tmp_path / "gateway.db")


def test_link_code_binds_and_is_single_use(tmp_path):
    conn = _conn(tmp_path)
    cli = ensure_cli_identity(conn)
    code = generate_link_code(conn, cli)
    assert len(code) == 6
    bound = consume_link_code(conn, code, "telegram", "777")
    assert bound == cli
    # Second use fails (single-use).
    assert consume_link_code(conn, code, "telegram", "888") is None
    # And the bound channel user now resolves to the CLI identity.
    assert get_or_create_identity_for_channel(conn, "telegram", "777") == cli


def test_expired_link_code_rejected(tmp_path):
    conn = _conn(tmp_path)
    cli = ensure_cli_identity(conn)
    code = generate_link_code(conn, cli)
    conn.execute("UPDATE link_codes SET expires_at = ? WHERE code = ?", (time.time() - 1, code))
    conn.commit()
    assert consume_link_code(conn, code, "telegram", "777") is None


def test_one_shared_session_across_channels(tmp_path):
    conn = _conn(tmp_path)
    identity = get_or_create_identity_for_channel(conn, "telegram", "777", "alice")
    s1 = get_or_create_session(conn, identity, "telegram")
    save_gateway_message(conn, identity, s1, "telegram", "user", "research X topic")
    # Same identity on Web UI gets the SAME open session.
    s2 = get_or_create_session(conn, identity, "webui")
    assert s2 == s1
    history = get_session_history(conn, s1)
    assert [m["content"] for m in history] == ["research X topic"]


def test_new_and_resume_sessions(tmp_path):
    conn = _conn(tmp_path)
    identity = get_or_create_identity_for_channel(conn, "telegram", "777")
    s1 = get_or_create_session(conn, identity, "telegram")
    s2 = new_session(conn, identity, "telegram")
    assert s2 != s1
    resumed = resume_session(conn, identity, "telegram")
    assert resumed == s2
    assert resume_session(conn, "no-such-identity", "telegram") is None


def test_history_is_oldest_first_and_bounded(tmp_path):
    conn = _conn(tmp_path)
    identity = get_or_create_identity_for_channel(conn, "telegram", "777")
    session = get_or_create_session(conn, identity, "telegram")
    for i in range(5):
        save_gateway_message(conn, identity, session, "telegram", "user", f"msg {i}")
    history = get_session_history(conn, session, limit=3)
    assert [m["content"] for m in history] == ["msg 2", "msg 3", "msg 4"]
