"""
ARYx AGENT - Slack adapter (Section 16.6).

Needs the optional dependency:  pip install 'aryx-agent[slack]'
(libraries: slack-bolt + slack-sdk). Without them, constructing
this adapter raises a plain-English error, not a traceback.

Behaviour (spec): /aryx slash command, @-mentions, Block Kit
Approve/Reject buttons, Socket Mode (no public URL needed — good
for small teams). Workspace/user allowlists are enforced by the
core; this adapter only routes.
"""

from __future__ import annotations

from typing import Any

from aryx.gateway.core import GatewayCore
from aryx.gateway.types import IncomingMessage, OutgoingMessage


class SlackError(Exception):
    pass


class SlackAdapter:
    def __init__(self, bot_token: str, app_token: str, core: GatewayCore) -> None:
        if not bot_token or not app_token:
            raise SlackError(
                "Slack needs a bot token (xoxb-...) and an app token (xapp-...). "
                "Run `aryx gateway add slack` first."
            )
        try:
            from slack_bolt import App  # type: ignore
            from slack_bolt.adapter.socket_mode import SocketModeHandler  # type: ignore
        except ImportError as e:
            raise SlackError(
                "slack-bolt is not installed. Install it with: pip install 'aryx-agent[slack]'"
            ) from e
        self.core = core
        # token_verification_enabled=False: slack-bolt otherwise calls
        # auth.test during construction and raises for any placeholder
        # token. Construction must succeed so `gateway test/start`
        # can report auth problems cleanly at connect time instead.
        self.app = App(token=bot_token, token_verification_enabled=False)
        self._handler = SocketModeHandler(self.app, app_token)
        self._wire_events()

    def _incoming(self, user_id: str, text: str, team_id: str = "") -> IncomingMessage:
        return IncomingMessage(
            channel="slack", user_id=user_id, username="", text=text, workspace_id=team_id
        )

    def _approval_blocks(self, summary: str) -> list:
        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "action_id": "aryx_approve", "style": "primary"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Reject"}, "action_id": "aryx_reject", "style": "danger"},
                ],
            },
        ]

    def _wire_events(self) -> None:
        app = self.app
        core = self.core

        @app.command("/aryx")
        def handle_slash(ack: Any, body: Any, say: Any) -> None:  # noqa: ANN001
            ack()
            reply = core.handle_message(
                self._incoming(body.get("user_id", ""), body.get("text", ""), body.get("team_id", ""))
            )
            if reply is None:
                return
            if reply.approval:
                say(blocks=self._approval_blocks(f"I want to run: {reply.approval.summary}"))
            else:
                say(reply.text or "…")

        @app.event("app_mention")
        def handle_mention(body: Any, say: Any) -> None:  # noqa: ANN001
            event = body.get("event", {})
            reply = core.handle_message(
                self._incoming(event.get("user", ""), event.get("text", ""), body.get("team_id", ""))
            )
            if reply is None:
                return
            if reply.approval:
                say(blocks=self._approval_blocks(f"I want to run: {reply.approval.summary}"))
            else:
                say(reply.text or "…")

        @app.action("aryx_approve")
        def handle_approve(ack: Any, body: Any, say: Any) -> None:  # noqa: ANN001
            ack()
            reply = core.handle_message(
                IncomingMessage(
                    channel="slack",
                    user_id=body.get("user", {}).get("id", ""),
                    text="",
                    callback_data="approve",
                    workspace_id=body.get("team", {}).get("id", ""),
                )
            )
            say(reply.text if reply else "Nothing is waiting for approval.")

        @app.action("aryx_reject")
        def handle_reject(ack: Any, body: Any, say: Any) -> None:  # noqa: ANN001
            ack()
            reply = core.handle_message(
                IncomingMessage(
                    channel="slack",
                    user_id=body.get("user", {}).get("id", ""),
                    text="",
                    callback_data="reject",
                    workspace_id=body.get("team", {}).get("id", ""),
                )
            )
            say(reply.text if reply else "Nothing is waiting for approval.")

    def run(self) -> None:
        """Blocking Socket Mode loop. Runs in a thread under gateway start."""
        self._handler.start()
