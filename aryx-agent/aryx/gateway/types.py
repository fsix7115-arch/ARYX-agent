"""
ARYx AGENT - Gateway message types (Section 16.1).

The agent core NEVER knows which channel a message came from. Every
adapter translates its platform event into an IncomingMessage and
translates the agent's OutgoingMessage back. Adding a new channel
means writing one adapter that speaks these two dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IncomingMessage:
    """One user message, normalised from any channel."""

    channel: str  # "telegram" | "whatsapp" | "discord" | "slack" | "webui" | "cli"
    user_id: str  # channel-specific unique ID (never a display name)
    username: str = ""  # display name, best effort
    text: str = ""
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    reply_to: Optional[str] = None  # message/thread id this replies to
    raw: Dict[str, Any] = field(default_factory=dict)
    # Set for button/interaction callbacks (approve/reject, etc.).
    callback_id: Optional[str] = None
    callback_data: Optional[str] = None
    # Discord/Slack scoping, filled by those adapters.
    guild_id: Optional[str] = None
    workspace_id: Optional[str] = None
    role_ids: List[str] = field(default_factory=list)


@dataclass
class ApprovalRequest:
    """A paused tool call waiting on a human decision."""

    tool_name: str
    args: Dict[str, Any]
    summary: str  # human-readable, no secrets (args are redacted first)
    timeout_seconds: int = 300


@dataclass
class OutgoingMessage:
    """One agent reply, rendered natively by each channel adapter."""

    text: str = ""
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[Dict[str, str]] = field(default_factory=list)
    # Buttons are {"label": str, "data": str} pairs; adapters render
    # them as inline keyboards, Block Kit buttons, or numbered menus.
    reply_to: Optional[str] = None
    # When set, the adapter must NOT send plain text alone: it must
    # render an approval prompt with Approve/Reject buttons and wait
    # for the user's choice (which arrives as a callback message).
    approval: Optional[ApprovalRequest] = None
    # True when the agent is still working and this is a progress note.
    is_progress: bool = False
