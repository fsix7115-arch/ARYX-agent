"""
ARYx AGENT - Gateway layer (Section 16).

Control the SAME agent brain from Telegram, WhatsApp, Discord,
Slack or a browser Web UI. Memory and skills are shared across
channels via one identity per human (see identity.py).

Base install covers Telegram (Bot API over httpx) and the Web UI
(stdlib server) with zero new dependencies. Discord and Slack need
their optional extras: pip install 'aryx-agent[discord]' / '[slack]'.
"""

from aryx.gateway.agent import AgentRunner
from aryx.gateway.core import GatewayCore
from aryx.gateway.types import IncomingMessage, OutgoingMessage

__all__ = ["AgentRunner", "GatewayCore", "IncomingMessage", "OutgoingMessage"]
