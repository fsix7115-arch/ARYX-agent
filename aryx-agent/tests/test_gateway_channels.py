"""
ARYx AGENT - Gateway channel-helper tests (Section 16.4/16.5).

Pure functions only: Telegram chunking and webhook signature
verification. No network, no tokens, no platform libraries.
"""

import base64
import hashlib
import hmac

from aryx.gateway.channels.telegram import split_message
from aryx.gateway.channels.whatsapp import (
    parse_meta_payload,
    parse_twilio_form,
    verify_meta_signature,
    verify_twilio_signature,
)


def test_telegram_chunking_respects_4096():
    text = "hello world\n" * 1000  # 12,000 chars over many lines
    chunks = split_message(text)
    assert all(len(c) <= 4096 for c in chunks)
    assert "".join(chunks) == text
    assert split_message("short") == ["short"]


def test_meta_signature_verification():
    secret = "app-secret"
    body = b'{"entry":[]}'
    good = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_meta_signature(secret, body, good) is True
    assert verify_meta_signature("wrong-secret", body, good) is False
    assert verify_meta_signature(secret, body, "sha256=deadbeef") is False


def test_twilio_signature_verification():
    token = "twilio-auth-token"
    url = "https://example.com/webhook/whatsapp"
    params = {"From": "whatsapp:+919999999999", "Body": "hi"}
    data = url + "".join(k + v for k, v in sorted(params.items()))
    good = base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    assert verify_twilio_signature(token, url, params, good) is True
    assert verify_twilio_signature(token, url, {"From": "x", "Body": "hi"}, good) is False


def test_twilio_form_parsing():
    form = {"From": ["whatsapp:+919999999999"], "Body": ["list my files"], "NumMedia": ["0"]}
    msg = parse_twilio_form(form)
    assert msg.channel == "whatsapp" and msg.user_id == "+919999999999"
    assert msg.text == "list my files"


def test_meta_payload_parsing():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{"from": "919999999999", "type": "text", "text": {"body": "hello"}}]
                }
            }]
        }]
    }
    messages = parse_meta_payload(payload)
    assert len(messages) == 1 and messages[0].text == "hello"
