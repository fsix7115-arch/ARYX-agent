"""
ARYx AGENT - Gateway core (Section 16.8).

Shared by every channel: auth, sessions, rate limiting, queuing,
logging and the approval handshake. Adapters stay thin: they only
translate platform events into IncomingMessage and render
OutgoingMessage natively.

Security defaults (Section 16.3):
  - Default = DENY. A message from a non-allow-listed user is
    SILENTLY ignored (no "unauthorized" reply — that reveals the bot).
  - Messaging channels (Telegram/WhatsApp/Discord/Slack) are FORCED
    into "safe" approval mode unless the owner explicitly lists that
    user in the channel's allow_yolo_users.
  - Logs never contain message text or secrets: lengths + hashes only.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Optional, Tuple

from aryx.gateway.config import (
    GATEWAY_FILE,
    GATEWAY_LOG,
    channel_config,
    load_gateway_config,
    redact_gateway_text,
)
from aryx.gateway.identity import (
    consume_link_code,
    count_messages_today,
    generate_link_code,
    get_gateway_db_connection,
    get_identity_for_channel,
    get_or_create_identity_for_channel,
    get_or_create_session,
    get_session_history,
    new_session,
    resume_session,
    save_gateway_message,
)
from aryx.gateway.types import ApprovalRequest, IncomingMessage, OutgoingMessage

MESSAGING_CHANNELS = ("telegram", "whatsapp", "discord", "slack")


def _norm_id(value: Any) -> str:
    return str(value).strip()


def _norm_username(value: str) -> str:
    return value.strip().lstrip("@").lower()


def _norm_phone(value: str) -> str:
    return "".join(c for c in str(value) if c.isdigit() or c == "+").strip()


class AuthManager:
    """Allowlist checks. Returns (allowed, reason). Default = deny."""

    @staticmethod
    def is_allowed(msg: IncomingMessage, config: Dict[str, Any]) -> Tuple[bool, str]:
        channel = msg.channel
        if channel == "cli":
            return True, "local cli"
        if channel == "webui":
            # The WebUI adapter authenticates the token before a message
            # ever reaches the core, so an arriving webui message is authed.
            return True, "webui token checked by adapter"
        cfg = channel_config(config, channel)
        if channel == "telegram":
            ids = {_norm_id(v) for v in cfg.get("allowed_user_ids", [])}
            names = {_norm_username(v) for v in cfg.get("allowed_usernames", [])}
            if _norm_id(msg.user_id) in ids:
                return True, "telegram id allowlisted"
            if msg.username and _norm_username(msg.username) in names:
                return True, "telegram username allowlisted"
            return False, "telegram user not allowlisted"
        if channel == "whatsapp":
            numbers = {_norm_phone(v) for v in cfg.get("allowed_numbers", [])}
            if _norm_phone(msg.user_id) in numbers:
                return True, "whatsapp number allowlisted"
            return False, "whatsapp number not allowlisted"
        if channel == "discord":
            guilds = {_norm_id(v) for v in cfg.get("allowed_guilds", [])}
            if not msg.guild_id or _norm_id(msg.guild_id) not in guilds:
                return False, "discord guild not allowlisted"
            roles = {_norm_id(v) for v in cfg.get("allowed_roles", [])}
            if roles and not (roles & {_norm_id(r) for r in msg.role_ids}):
                return False, "discord role not allowlisted"
            return True, "discord guild/role allowlisted"
        if channel == "slack":
            workspaces = {_norm_id(v) for v in cfg.get("allowed_workspaces", [])}
            users = {_norm_id(v) for v in cfg.get("allowed_users", [])}
            if msg.workspace_id and _norm_id(msg.workspace_id) not in workspaces:
                return False, "slack workspace not allowlisted"
            if users and _norm_id(msg.user_id) not in users:
                return False, "slack user not allowlisted"
            if not workspaces and not users:
                return False, "slack allowlist empty"
            return True, "slack allowlisted"
        return False, f"unknown channel {channel}"

    @staticmethod
    def effective_approval_mode(
        msg: IncomingMessage, config: Dict[str, Any]
    ) -> str:
        """Messaging channels are forced to 'safe' unless explicitly exempt."""
        cfg = channel_config(config, msg.channel)
        mode = str(cfg.get("default_approval_mode", "safe")).lower()
        if msg.channel in MESSAGING_CHANNELS:
            yolo_users = {_norm_id(v) for v in cfg.get("allow_yolo_users", [])}
            if mode == "yolo" and _norm_id(msg.user_id) not in yolo_users:
                return "safe"
        return mode if mode in ("safe", "auto", "yolo") else "safe"


class RateLimiter:
    """Per-user, per-channel limits. Default 20/min, 500/day (spec 16.8)."""

    def __init__(self, per_minute: int = 20, per_day: int = 500) -> None:
        self.per_minute = per_minute
        self.per_day = per_day
        self._minute: Dict[Tuple[str, str], Deque[float]] = {}
        self._day: Dict[Tuple[str, str], Tuple[float, int]] = {}
        self._lock = threading.Lock()

    def allow(self, channel: str, user_id: str) -> Tuple[bool, int]:
        now = time.time()
        key = (channel, str(user_id))
        with self._lock:
            window = self._minute.setdefault(key, deque())
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= self.per_minute:
                return False, max(1, int(60 - (now - window[0])))
            day_start = now - (now % 86400)
            day, count = self._day.get(key, (day_start, 0))
            if day != day_start:
                day, count = day_start, 0
            if count >= self.per_day:
                return False, max(1, int(86400 - (now - day_start)))
            window.append(now)
            self._day[key] = (day, count + 1)
            return True, 0


class QueueManager:
    """One sequential queue per identity: no parallel chaos (spec 16.8)."""

    def __init__(self) -> None:
        self._locks: Dict[str, threading.Lock] = {}
        self._busy: Dict[str, bool] = {}
        self._guard = threading.Lock()

    def try_acquire(self, identity_id: str) -> bool:
        with self._guard:
            lock = self._locks.setdefault(identity_id, threading.Lock())
            if self._busy.get(identity_id):
                return False
            acquired = lock.acquire(blocking=False)
            if acquired:
                self._busy[identity_id] = True
            return acquired

    def release(self, identity_id: str) -> None:
        with self._guard:
            lock = self._locks.get(identity_id)
            if lock and self._busy.get(identity_id):
                self._busy[identity_id] = False
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def is_busy(self, identity_id: str) -> bool:
        return bool(self._busy.get(identity_id))


class GatewayLogger:
    """JSONL logs with lengths + hashes only. NEVER full text or secrets."""

    def __init__(self, path: Optional[Path] = None, config: Optional[Dict[str, Any]] = None) -> None:
        self.path = Path(path) if path else GATEWAY_LOG
        self.config = config
        self._lock = threading.Lock()

    def log(
        self,
        channel: str,
        user_id: str,
        direction: str,
        text: str = "",
        tokens: int = 0,
        latency_ms: int = 0,
    ) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "ts": time.time(),
                "channel": channel,
                "user_id_hash": hashlib.sha256(str(user_id).encode()).hexdigest()[:12],
                "direction": direction,
                "text_len": len(text),
                "text_hash": hashlib.sha256(text.encode()).hexdigest()[:12],
                "tokens": tokens,
                "latency_ms": latency_ms,
            }
            with self._lock, open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # Logging must never break message handling.


class PendingApproval:
    def __init__(self, identity_id: str, session_id: str, continuation: Any) -> None:
        self.identity_id = identity_id
        self.session_id = session_id
        self.continuation = continuation
        self.created_at = time.time()


class GatewayCore:
    """Routes channel messages to the agent and back (spec 16.1/16.8)."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        conn: Any = None,
        agent_runner: Any = None,
        config_path: Optional[Path] = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path else GATEWAY_FILE
        self.config = config if config is not None else load_gateway_config(self.config_path)
        self._config_mtime: Optional[float] = None
        try:
            self._config_mtime = self.config_path.stat().st_mtime
        except OSError:
            pass
        self.conn = conn if conn is not None else get_gateway_db_connection()
        self.agent_runner = agent_runner
        limits = self.config.get("rate_limits", {})
        self.rate_limiter = RateLimiter(
            per_minute=int(limits.get("messages_per_minute", 20)),
            per_day=int(limits.get("messages_per_day", 500)),
        )
        self.queue = QueueManager()
        self.logger = GatewayLogger(config=self.config)
        self.pending: Dict[str, PendingApproval] = {}
        self.stop_flags: Dict[str, threading.Event] = {}
        self.started_at = time.time()
        self.counts: Dict[str, int] = {}
        # One lock for ALL database access through the core. Adapters
        # run in different threads but share one SQLite connection;
        # without this, ThreadingHTTPServer workers crash with
        # "SQLite objects created in a thread can only be used in
        # that same thread". RLock: handle_message calls
        # resolve_approval for button taps (nested acquisition).
        self._db_lock = threading.RLock()

    # -- config hot-reload (allowlists apply without a restart) --------
    def _maybe_reload_config(self) -> None:
        try:
            mtime = self.config_path.stat().st_mtime
        except OSError:
            return
        if self._config_mtime is None or mtime != self._config_mtime:
            try:
                self.config = load_gateway_config(self.config_path)
                self._config_mtime = mtime
                self.logger.config = self.config
            except Exception:
                pass  # Keep serving on the last good config.

    def reload_config(self) -> Optional[str]:
        """Validate + reload now. Returns an error string or None."""
        from aryx.gateway.config import validate_gateway_config

        err = validate_gateway_config(self.config_path)
        if err:
            return err
        self.config = load_gateway_config(self.config_path)
        try:
            self._config_mtime = self.config_path.stat().st_mtime
        except OSError:
            pass
        return None

    # -- slash commands -------------------------------------------------
    def _handle_command(self, msg: IncomingMessage, identity_id: str) -> Optional[OutgoingMessage]:
        parts = msg.text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd == "/start":
            return OutgoingMessage(
                text="Hi, I'm ARYx — your terminal agent, here too. "
                "Send me a task, or /help for commands."
            )
        if cmd == "/help":
            return OutgoingMessage(
                text="Commands: /whoami (show your channel ID), /link CODE "
                "(bind this chat to your CLI identity), /resume (reopen last "
                "session), /new (fresh session), /stop (cancel current task)."
            )
        if cmd == "/whoami":
            return OutgoingMessage(
                text=f"Channel: {msg.channel}\nYour ID: {msg.user_id}\n"
                "Give this ID to the bot owner to add you to the allowlist."
            )
        if cmd == "/link":
            if not arg:
                return OutgoingMessage(text="Usage: /link CODE — get a code from `aryx gateway link` on your computer.")
            bound = consume_link_code(self.conn, arg, msg.channel, msg.user_id)
            if bound:
                return OutgoingMessage(
                    text="Linked! This chat now shares memory, skills and "
                    "config with your CLI identity. What you start here, "
                    "you can continue on the terminal."
                )
            return OutgoingMessage(text="That code is invalid or expired (codes last 10 minutes). Run `aryx gateway link` again for a fresh one.")
        if cmd == "/resume":
            session_id = resume_session(self.conn, identity_id, msg.channel)
            if session_id:
                return OutgoingMessage(text="Resumed your last session — I remember where we left off. What next?")
            return OutgoingMessage(text="No previous session found. Just send me a task to start one.")
        if cmd == "/new":
            new_session(self.conn, identity_id, msg.channel)
            return OutgoingMessage(text="Fresh session started. Previous history is kept, but we start clean.")
        if cmd == "/stop":
            flag = self.stop_flags.setdefault(identity_id, threading.Event())
            flag.set()
            self.pending.pop(identity_id, None)
            self.queue.release(identity_id)
            return OutgoingMessage(text="Stopped the current task.")
        return None  # Not a command we handle here.

    # -- main entry -----------------------------------------------------
    def handle_message(self, msg: IncomingMessage) -> Optional[OutgoingMessage]:
        """Returns None when the adapter must stay silent (spec 16.3)."""
        with self._db_lock:
            return self._handle_message_locked(msg)

    def _handle_message_locked(self, msg: IncomingMessage) -> Optional[OutgoingMessage]:
        started = time.time()
        self._maybe_reload_config()
        allowed, reason = AuthManager.is_allowed(msg, self.config)
        if not allowed:
            # SILENT: never confirm the bot exists to strangers.
            self.logger.log(msg.channel, msg.user_id, "rejected", msg.text)
            return None
        ok, retry = self.rate_limiter.allow(msg.channel, msg.user_id)
        if not ok:
            return OutgoingMessage(text=f"Slow down — try again in {retry}s.")
        identity_id = get_or_create_identity_for_channel(
            self.conn, msg.channel, msg.user_id, msg.username
        )
        # Button taps arrive as callbacks, not new tasks.
        if msg.callback_data:
            return self.resolve_approval(msg, identity_id)
        if msg.text.strip().startswith("/"):
            reply = self._handle_command(msg, identity_id)
            if reply is not None:
                self.logger.log(msg.channel, msg.user_id, "out", reply.text)
                return reply
        if self.queue.is_busy(identity_id):
            return OutgoingMessage(
                text="Working on your previous message. Send /stop to cancel, or wait."
            )
        if not self.queue.try_acquire(identity_id):
            return OutgoingMessage(text="Working on your previous message. Send /stop to cancel, or wait.")
        try:
            session_id = get_or_create_session(self.conn, identity_id, msg.channel)
            save_gateway_message(self.conn, identity_id, session_id, msg.channel, "user", msg.text)
            self._mirror_to_cli_memory(identity_id, session_id, "user", msg.text)
            self.counts[msg.channel] = self.counts.get(msg.channel, 0) + 1
            if self.agent_runner is None:
                reply = OutgoingMessage(
                    text="The agent is not configured yet. Run `aryx` once on "
                    "your computer to set up a provider, then try again."
                )
            else:
                reply = self._run_agent(msg, identity_id, session_id)
            if reply is not None and not reply.approval:
                save_gateway_message(self.conn, identity_id, session_id, msg.channel, "assistant", reply.text)
                self._mirror_to_cli_memory(identity_id, session_id, "assistant", reply.text)
            if reply is not None:
                latency = int((time.time() - started) * 1000)
                self.logger.log(msg.channel, msg.user_id, "out", reply.text, latency_ms=latency)
            return reply
        finally:
            self.queue.release(identity_id)

    def _run_agent(
        self, msg: IncomingMessage, identity_id: str, session_id: str
    ) -> OutgoingMessage:
        history = get_session_history(self.conn, session_id, limit=30)
        approval_mode = AuthManager.effective_approval_mode(msg, self.config)
        stop_flag = self.stop_flags.setdefault(identity_id, threading.Event())
        stop_flag.clear()
        result = self.agent_runner.start_turn(
            history=history,
            user_text=msg.text,
            approval_mode=approval_mode,
            stop_flag=stop_flag,
        )
        if result.kind == "approval" and result.approval is not None:
            self.pending[identity_id] = PendingApproval(identity_id, session_id, result.continuation)
            summary = redact_gateway_text(result.approval.summary, self.config)
            return OutgoingMessage(
                text=f"I want to run: {summary}\nApprove or reject?",
                buttons=[
                    {"label": "Approve", "data": "approve"},
                    {"label": "Reject", "data": "reject"},
                ],
                approval=result.approval,
            )
        return OutgoingMessage(text=result.text)

    def resolve_approval(
        self, msg: IncomingMessage, identity_id: str
    ) -> Optional[OutgoingMessage]:
        """A button tap: continue the paused agent turn, or cancel it."""
        with self._db_lock:
            return self._resolve_approval_locked(msg, identity_id)

    def _resolve_approval_locked(
        self, msg: IncomingMessage, identity_id: str
    ) -> Optional[OutgoingMessage]:
        pending = self.pending.pop(identity_id, None)
        if pending is None:
            return OutgoingMessage(text="Nothing is waiting for approval right now.")
        # Approvals expire after 5 minutes (spec 16.9): a stale tap must
        # never execute a write. The entry is already popped, so an
        # expired approval cannot be retried either.
        if time.time() - pending.created_at > 300:
            return OutgoingMessage(
                text="This approval expired after 5 minutes — nothing was run. Please send the task again."
            )
        approved = (msg.callback_data or "").strip().lower() == "approve"
        result = pending.continuation.resolve(approved)
        if result.kind == "approval" and result.approval is not None:
            self.pending[identity_id] = PendingApproval(identity_id, pending.session_id, result.continuation)
            summary = redact_gateway_text(result.approval.summary, self.config)
            return OutgoingMessage(
                text=f"I want to run: {summary}\nApprove or reject?",
                buttons=[
                    {"label": "Approve", "data": "approve"},
                    {"label": "Reject", "data": "reject"},
                ],
                approval=result.approval,
            )
        save_gateway_message(self.conn, identity_id, pending.session_id, msg.channel, "assistant", result.text)
        self._mirror_to_cli_memory(identity_id, pending.session_id, "assistant", result.text)
        return OutgoingMessage(text=result.text)

    def _mirror_to_cli_memory(
        self, identity_id: str, session_id: str, role: str, content: str
    ) -> None:
        """Gateway turns also land in the CLI memory DB, so `aryx`
        /history on the terminal shows what happened on Telegram/Web."""
        try:
            from aryx.memory import save_message as cli_save_message

            cli_save_message(f"gateway_{identity_id}", role, content)
        except Exception:
            pass  # Mirroring is best-effort; the gateway store is primary.

    # -- health ---------------------------------------------------------
    def status_table(self) -> Dict[str, Any]:
        uptime = int(time.time() - self.started_at)
        rows = []
        for channel in ("telegram", "whatsapp", "discord", "slack", "webui"):
            cfg = channel_config(self.config, channel)
            rows.append(
                {
                    "channel": channel,
                    "enabled": bool(cfg.get("enabled")),
                    "messages_today": self.counts.get(channel, 0),
                }
            )
        return {"uptime_seconds": uptime, "channels": rows}

    def messages_today(self, channel: str) -> int:
        try:
            return count_messages_today(self.conn, channel)
        except Exception:
            return self.counts.get(channel, 0)
