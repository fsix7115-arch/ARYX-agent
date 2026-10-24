"""
ARYx AGENT - Gateway auth + core tests (Section 16.3/16.8).

No network, no real tokens, no real provider calls. The fake agent
runner stands in for the LLM so auth, sessions, rate limits and the
approval handshake are tested in isolation.
"""

from aryx.gateway.agent import TurnResult
from aryx.gateway.config import (
    channel_config,
    load_gateway_config,
    redact_gateway_text,
    save_gateway_config,
)
from aryx.gateway.core import AuthManager, GatewayCore, RateLimiter
from aryx.gateway.identity import get_gateway_db_connection
from aryx.gateway.types import ApprovalRequest, IncomingMessage


def _config(**overrides):
    cfg = load_gateway_config()
    for section, values in overrides.items():
        cfg.setdefault(section, {}).update(values)
    return cfg


def _msg(channel="telegram", user_id="111", username="", text="hello", **kw):
    return IncomingMessage(channel=channel, user_id=user_id, username=username, text=text, **kw)


def test_telegram_allowlist_by_id_and_username():
    cfg = _config(telegram={"allowed_user_ids": [111], "allowed_usernames": ["@aryxuser"]})
    assert AuthManager.is_allowed(_msg(user_id="111"), cfg)[0] is True
    assert AuthManager.is_allowed(_msg(user_id="999", username="aryxuser"), cfg)[0] is True
    assert AuthManager.is_allowed(_msg(user_id="999", username="AryxUser"), cfg)[0] is True
    assert AuthManager.is_allowed(_msg(user_id="999", username="stranger"), cfg)[0] is False


def test_whatsapp_discord_slack_allowlists():
    cfg = _config(
        whatsapp={"allowed_numbers": ["+919999999999"]},
        discord={"allowed_guilds": [123], "allowed_roles": ["role1"]},
        slack={"allowed_workspaces": ["T1"], "allowed_users": ["U1"]},
    )
    assert AuthManager.is_allowed(_msg("whatsapp", "+91 99999 99999"), cfg)[0] is True
    assert AuthManager.is_allowed(_msg("whatsapp", "+911111111111"), cfg)[0] is False
    assert AuthManager.is_allowed(_msg("discord", "7", guild_id="123", role_ids=["role1"]), cfg)[0] is True
    assert AuthManager.is_allowed(_msg("discord", "7", guild_id="999", role_ids=["role1"]), cfg)[0] is False
    assert AuthManager.is_allowed(_msg("discord", "7", guild_id="123", role_ids=["other"]), cfg)[0] is False
    assert AuthManager.is_allowed(_msg("slack", "U1", workspace_id="T1"), cfg)[0] is True
    assert AuthManager.is_allowed(_msg("slack", "U2", workspace_id="T1"), cfg)[0] is False
    assert AuthManager.is_allowed(_msg("carrier-pigeon", "1"), cfg)[0] is False


def test_messaging_channels_force_safe_mode():
    cfg = _config(telegram={"default_approval_mode": "yolo", "allow_yolo_users": [111]})
    assert AuthManager.effective_approval_mode(_msg(user_id="111"), cfg) == "yolo"
    assert AuthManager.effective_approval_mode(_msg(user_id="222"), cfg) == "safe"
    cfg2 = _config(webui={"default_approval_mode": "yolo"})
    assert AuthManager.effective_approval_mode(_msg("webui", "webui"), cfg2) == "yolo"


def test_rate_limiter():
    limiter = RateLimiter(per_minute=2, per_day=2)
    assert limiter.allow("telegram", "1")[0] is True
    assert limiter.allow("telegram", "1")[0] is True
    ok, retry = limiter.allow("telegram", "1")
    assert ok is False and retry >= 1
    # A different user is unaffected.
    assert limiter.allow("telegram", "2")[0] is True


class FakeRunner:
    """Scripted agent: first turn pauses for approval, tap resumes it."""

    def __init__(self):
        self.calls = []

    def start_turn(self, history, user_text, approval_mode="safe", stop_flag=None):
        self.calls.append(user_text)
        if user_text == "please write":
            return TurnResult(
                "approval",
                "",
                approval=ApprovalRequest(tool_name="write_file", args={"path": "/tmp/x"}, summary="write_file: /tmp/x"),
                continuation=FakeContinuation(),
            )
        return TurnResult("reply", f"echo: {user_text}")


class FakeContinuation:
    def resolve(self, approved):
        return TurnResult("reply", "approved and done" if approved else "cancelled by user")


def _core(tmp_path, runner, **overrides):
    cfg = _config(**overrides)
    conn = get_gateway_db_connection(tmp_path / "gateway.db")
    core = GatewayCore(config=cfg, conn=conn, agent_runner=runner)
    core.logger.path = tmp_path / "gateway.log"
    return core


def test_core_silently_ignores_strangers(tmp_path, monkeypatch):
    monkeypatch.setattr("aryx.memory.save_message", lambda *a, **k: None)
    core = _core(tmp_path, FakeRunner(), telegram={"allowed_user_ids": [111]})
    assert core.handle_message(_msg(user_id="999")) is None
    reply = core.handle_message(_msg(user_id="111", text="hi"))
    assert reply is not None and reply.text == "echo: hi"


def test_core_rate_limit_message(tmp_path, monkeypatch):
    monkeypatch.setattr("aryx.memory.save_message", lambda *a, **k: None)
    core = _core(
        tmp_path,
        FakeRunner(),
        telegram={"allowed_user_ids": [111]},
        rate_limits={"messages_per_minute": 1, "messages_per_day": 500},
    )
    assert core.handle_message(_msg(user_id="111", text="one")) is not None
    reply = core.handle_message(_msg(user_id="111", text="two"))
    assert reply is not None and "Slow down" in reply.text


def test_core_approval_pause_and_resume(tmp_path, monkeypatch):
    monkeypatch.setattr("aryx.memory.save_message", lambda *a, **k: None)
    core = _core(tmp_path, FakeRunner(), telegram={"allowed_user_ids": [111]})
    reply = core.handle_message(_msg(user_id="111", text="please write"))
    assert reply is not None and reply.approval is not None
    assert [b["data"] for b in reply.buttons] == ["approve", "reject"]
    done = core.handle_message(_msg(user_id="111", callback_data="approve"))
    assert done is not None and done.text == "approved and done"


def test_core_slash_commands(tmp_path, monkeypatch):
    monkeypatch.setattr("aryx.memory.save_message", lambda *a, **k: None)
    core = _core(tmp_path, FakeRunner(), telegram={"allowed_user_ids": [111]})
    who = core.handle_message(_msg(user_id="111", text="/whoami"))
    assert who is not None and "111" in who.text
    bad = core.handle_message(_msg(user_id="111", text="/link NOPE12"))
    assert bad is not None and "invalid or expired" in bad.text
