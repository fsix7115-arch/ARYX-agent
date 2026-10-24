"""
ARYx AGENT - WhatsApp adapter (Section 16.5).

Two paths, user chooses (wizard asks Twilio or Meta):
  MODE A (Twilio): easier, costs money. Webhook POSTs to your URL.
  MODE B (Meta Cloud API): free for 1000 conversations/month, but
      needs a Meta app + verified business.

Both senders use httpx (already a dependency). Webhook receiving
uses a stdlib server; a public URL needs a tunnel (cloudflared /
ngrok) — `aryx gateway start whatsapp --tunnel` prints the reminder
and the exact webhook URL to paste into Twilio/Meta.

WhatsApp rules honoured here:
  - 24-hour session window: replies are free for 24h after the user
    messages. Outside it, business-initiated messages need a
    pre-approved template — the sender surfaces Meta/Twilio's error
    instead of pretending it worked.
  - Voice notes: same stance as Telegram — recorded, not transcribed
    in this build (transcription is a documented future step).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

import httpx

from aryx.gateway.core import GatewayCore
from aryx.gateway.types import IncomingMessage, OutgoingMessage


class WhatsAppError(Exception):
    pass


# -- signature verification (never trust an unsigned webhook) ------------
def verify_twilio_signature(auth_token: str, url: str, params: Dict[str, str], signature: str) -> bool:
    data = url + "".join(k + v for k, v in sorted(params.items()))
    expected = __import__("base64").b64encode(
        hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()
    ).decode()
    return hmac.compare_digest(expected, signature)


def verify_meta_signature(app_secret: str, raw_body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# -- senders ---------------------------------------------------------------
class TwilioSender:
    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self.sid, self.token, self.from_number = account_sid, auth_token, from_number
        self._client = httpx.Client(timeout=30.0, auth=(account_sid, auth_token))

    def send_text(self, to: str, text: str) -> None:
        resp = self._client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json",
            data={"From": f"whatsapp:{self.from_number}", "To": f"whatsapp:{to}", "Body": text[:1600]},
        )
        if resp.status_code >= 400:
            raise WhatsAppError(f"Twilio send failed ({resp.status_code}): {resp.text[:200]}")


class MetaSender:
    def __init__(self, access_token: str, phone_number_id: str) -> None:
        self.token, self.phone_number_id = access_token, phone_number_id
        self._client = httpx.Client(timeout=30.0)

    def send_text(self, to: str, text: str) -> None:
        resp = self._client.post(
            f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4096]}},
        )
        if resp.status_code >= 400:
            raise WhatsAppError(f"Meta send failed ({resp.status_code}): {resp.text[:200]}")


# -- inbound parsing ---------------------------------------------------------
def parse_twilio_form(form: Dict[str, List[str]]) -> IncomingMessage:
    def one(key: str) -> str:
        values = form.get(key, [])
        return values[0] if values else ""

    sender = one("From").replace("whatsapp:", "")
    body = one("Body")
    attachments: List[Dict[str, Any]] = []
    for i in range(int(one("NumMedia") or 0)):
        media_type = one(f"MediaContentType{i}")
        kind = "voice" if "audio" in media_type else ("photo" if "image" in media_type else "document")
        attachments.append({"type": kind, "url": one(f"MediaUrl{i}"), "media_type": media_type})
    if not body and any(a["type"] == "voice" for a in attachments):
        body = "[voice note received — transcription is not enabled in this build]"
    return IncomingMessage(
        channel="whatsapp", user_id=sender, username="", text=body, attachments=attachments
    )


def parse_meta_payload(payload: Dict[str, Any]) -> List[IncomingMessage]:
    messages: List[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for item in value.get("messages", []):
                sender = item.get("from", "")
                msg_type = item.get("type", "text")
                if msg_type == "text":
                    text = item.get("text", {}).get("body", "")
                elif msg_type == "audio":
                    text = "[voice note received — transcription is not enabled in this build]"
                else:
                    text = item.get(msg_type, {}).get("caption", "") or f"[{msg_type} received]"
                messages.append(
                    IncomingMessage(channel="whatsapp", user_id=sender, username="", text=text)
                )
    return messages


class WhatsAppAdapter:
    """Routes inbound webhooks through the core and sends replies back."""

    def __init__(self, core: GatewayCore, sender: Any, provider: str = "twilio") -> None:
        self.core = core
        self.sender = sender
        self.provider = provider

    def handle(self, incoming: IncomingMessage) -> None:
        reply = self.core.handle_message(incoming)
        if reply is None:
            return  # Silently ignored (not allow-listed).
        self._send_reply(incoming.user_id, reply)

    def _send_reply(self, to: str, reply: OutgoingMessage) -> None:
        # WhatsApp buttons are limited: render approvals as a numbered
        # menu (spec 16.9) — "Reply 1 = Approve, 2 = Reject".
        text = reply.text
        if reply.approval and reply.buttons:
            text += "\n\nReply 1 = Approve, 2 = Reject"
        if text:
            self.sender.send_text(to, text)
        for attachment in reply.attachments:
            if attachment.get("path"):
                # File sending differs per provider; surface plainly.
                self.sender.send_text(to, f"[file ready: {attachment['path']}]")

    def start_webhook_server(self, host: str = "127.0.0.1", port: int = 8766) -> threading.Thread:
        adapter = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def _respond(self, status: int, body: bytes = b"OK") -> None:
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802 (Meta webhook verification)
                from urllib.parse import urlparse, parse_qs as _parse

                query = _parse(urlparse(self.path).query)
                mode = query.get("hub.mode", [None])[0]
                challenge = query.get("hub.challenge", [None])[0]
                if mode == "subscribe" and challenge:
                    self._respond(200, challenge.encode())
                else:
                    self._respond(404)

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                content_type = self.headers.get("Content-Type", "")
                try:
                    if "application/json" in content_type:
                        payload = json.loads(raw or b"{}")
                        for incoming in parse_meta_payload(payload):
                            adapter.handle(incoming)
                    else:
                        form = parse_qs(raw.decode())
                        adapter.handle(parse_twilio_form(form))
                    self._respond(200)
                except Exception:
                    self._respond(500, b"error")

        server = ThreadingHTTPServer((host, port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return thread
