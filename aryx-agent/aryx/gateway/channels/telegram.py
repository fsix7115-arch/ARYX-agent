"""
ARYx AGENT - Telegram adapter (Section 16.4, recommended first channel).

Why no python-telegram-bot dependency: the Bot API over plain HTTPS
(httpx, already a dependency) covers everything this adapter needs —
long-polling, inline keyboards, chunking, file sends. Zero new
install weight, and the same code runs everywhere Python runs.

Long-polling is the default: no public IP, no webhook, no server.
The bot just works from the user's laptop.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from aryx.gateway.core import GatewayCore
from aryx.gateway.types import IncomingMessage, OutgoingMessage

TELEGRAM_MAX_CHARS = 4096

BOT_COMMANDS_TEXT = (
    "start - Start ARYx\n"
    "help - Show help\n"
    "whoami - Show your Telegram ID\n"
    "link - Link this chat to your CLI identity\n"
    "resume - Resume last session\n"
    "new - Start a fresh session\n"
    "stop - Stop current task"
)


class TelegramError(Exception):
    pass


def split_message(text: str, limit: int = TELEGRAM_MAX_CHARS) -> List[str]:
    """Split on line boundaries where possible (Telegram's 4096 cap)."""
    if len(text) <= limit:
        return [text]
    chunks: List[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            chunks.append(current)
            current = ""
        if len(line) > limit:  # one giant line: hard-split it
            for i in range(0, len(line), limit):
                chunks.append(line[i : i + limit])
            continue
        current += line
    if current:
        chunks.append(current)
    return chunks or [""]


class TelegramAdapter:
    def __init__(self, token: str, core: GatewayCore) -> None:
        if not token:
            raise TelegramError(
                "No Telegram bot token configured. Run `aryx gateway add telegram` first."
            )
        self.token = token
        self.core = core
        self.base = f"https://api.telegram.org/bot{token}"
        self._offset: Optional[int] = None
        self._client = httpx.Client(timeout=35.0)

    # -- Bot API primitives ------------------------------------------------
    def _api(self, method: str, **params: Any) -> Dict[str, Any]:
        resp = self._client.post(f"{self.base}/{method}", json=params)
        data = resp.json()
        if not data.get("ok"):
            raise TelegramError(f"Telegram API error on {method}: {data.get('description', data)}")
        return data["result"]

    def test_connection(self) -> str:
        """getMe check used by `aryx gateway test telegram`."""
        me = self._api("getMe")
        return f"@{me.get('username', '?')} (id {me.get('id', '?')})"

    def send_message(
        self,
        chat_id: Any,
        text: str,
        buttons: Optional[List[Dict[str, str]]] = None,
        reply_to: Optional[Any] = None,
    ) -> None:
        payload_base: Dict[str, Any] = {"chat_id": chat_id}
        if reply_to:
            payload_base["reply_to_message_id"] = reply_to
        chunks = split_message(text or "…")
        for index, chunk in enumerate(chunks):
            payload = dict(payload_base)
            payload["text"] = chunk
            # Buttons only on the last chunk (they belong to the prompt).
            if buttons and index == len(chunks) - 1:
                payload["reply_markup"] = {
                    "inline_keyboard": [[{"text": b["label"], "callback_data": b["data"]}] for b in buttons]
                }
            self._api("sendMessage", **payload)

    def send_file(self, chat_id: Any, path: str, caption: str = "") -> None:
        file_path = Path(path)
        if not file_path.exists():
            raise TelegramError(f"Attachment not found: {path}")
        with open(file_path, "rb") as f:
            resp = self._client.post(
                f"{self.base}/sendDocument",
                data={"chat_id": str(chat_id), "caption": caption[:1024]},
                files={"document": (file_path.name, f)},
            )
        data = resp.json()
        if not data.get("ok"):
            raise TelegramError(f"Telegram sendDocument failed: {data.get('description', data)}")

    # -- update -> message --------------------------------------------------
    def _handle_update(self, update: Dict[str, Any]) -> None:
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            sender = message.get("from", {})
            text = message.get("text", "") or message.get("caption", "") or ""
            attachments: List[Dict[str, Any]] = []
            if "photo" in message:
                attachments.append({"type": "photo", "file_id": message["photo"][-1]["file_id"]})
            if "document" in message:
                attachments.append({"type": "document", "file_id": message["document"]["file_id"]})
            if "voice" in message:
                # Voice transcription is not enabled in this build: the
                # note is kept as an attachment record, and the user is
                # told plainly instead of a fake transcript.
                attachments.append({"type": "voice", "file_id": message["voice"]["file_id"]})
                if not text:
                    text = "[voice note received — transcription is not enabled in this build]"
            incoming = IncomingMessage(
                channel="telegram",
                user_id=str(sender.get("id", chat_id)),
                username=sender.get("username", "") or sender.get("first_name", ""),
                text=text,
                attachments=attachments,
                reply_to=str(message.get("message_id")),
                raw={"chat_id": chat_id, "update": update},
            )
            reply = self.core.handle_message(incoming)
            if reply is not None:
                self._send_reply(chat_id, reply, reply_to=message.get("message_id"))
        elif "callback_query" in update:
            query = update["callback_query"]
            chat_id = query["message"]["chat"]["id"]
            sender = query.get("from", {})
            try:
                self._api("answerCallbackQuery", callback_query_id=query["id"])
            except TelegramError:
                pass  # Non-fatal: the tap still counts.
            incoming = IncomingMessage(
                channel="telegram",
                user_id=str(sender.get("id", chat_id)),
                username=sender.get("username", "") or sender.get("first_name", ""),
                text="",
                callback_id=query["id"],
                callback_data=query.get("data", ""),
                raw={"chat_id": chat_id, "update": update},
            )
            reply = self.core.handle_message(incoming)
            if reply is not None:
                self._send_reply(chat_id, reply, reply_to=query["message"].get("message_id"))

    def _send_reply(self, chat_id: Any, reply: OutgoingMessage, reply_to: Optional[Any] = None) -> None:
        if reply.text:
            self.send_message(chat_id, reply.text, buttons=reply.buttons or None, reply_to=reply_to)
        for attachment in reply.attachments:
            path = attachment.get("path")
            if path:
                self.send_file(chat_id, path, caption=attachment.get("caption", ""))

    # -- long-polling loop ----------------------------------------------------
    def run_polling(self, stop_event: Optional[threading.Event] = None) -> None:
        """Blocking loop. Runs in its own thread under `aryx gateway start`."""
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            try:
                params: Dict[str, Any] = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
                if self._offset is not None:
                    params["offset"] = self._offset
                resp = self._client.post(f"{self.base}/getUpdates", json=params)
                updates = resp.json().get("result", [])
            except Exception:
                time.sleep(3)  # Network blip: back off, don't crash the gateway.
                continue
            for update in updates:
                self._offset = update["update_id"] + 1
                try:
                    self._handle_update(update)
                except Exception:
                    # One bad update must never kill the bot.
                    continue
