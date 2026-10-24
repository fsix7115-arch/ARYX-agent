"""Channel adapters: telegram, whatsapp, discord, slack, webui."""

from aryx.gateway.channels.telegram import TelegramAdapter, TelegramError
from aryx.gateway.channels.webui import WebUIAdapter
from aryx.gateway.channels.whatsapp import WhatsAppAdapter, WhatsAppError

__all__ = [
    "TelegramAdapter",
    "TelegramError",
    "WebUIAdapter",
    "WhatsAppAdapter",
    "WhatsAppError",
]
