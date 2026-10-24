"""
ARYx AGENT - Discord adapter (Section 16.6).

Needs the optional dependency:  pip install 'aryx-agent[discord]'
(library: discord.py). Without it, constructing this adapter raises
a plain-English error instead of an ImportError traceback.

Behaviour (spec): slash command /aryx, @-mention replies, one thread
per task, approval buttons, only allow-listed guilds/channels (the
core enforces guild/role allowlists; this adapter only routes).
"""

from __future__ import annotations

from typing import Any

from aryx.gateway.core import GatewayCore
from aryx.gateway.types import IncomingMessage, OutgoingMessage


class DiscordError(Exception):
    pass


class DiscordAdapter:
    def __init__(self, token: str, core: GatewayCore) -> None:
        if not token:
            raise DiscordError("No Discord bot token configured. Run `aryx gateway add discord` first.")
        try:
            import discord  # type: ignore
            from discord.ext import commands  # type: ignore
        except ImportError as e:
            raise DiscordError(
                "discord.py is not installed. Install it with: pip install 'aryx-agent[discord]'"
            ) from e
        self.token = token
        self.core = core
        self.discord = discord
        self.bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        self.bot.intents.message_content = True
        self._wire_events()

    # -- approval buttons ----------------------------------------------------
    def _approval_view(self, core: GatewayCore) -> Any:
        discord = self.discord

        class ApprovalView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

            @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
            async def approve(self, interaction: Any, button: Any) -> None:  # noqa: ANN001
                await self._resolve(interaction, "approve")

            @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
            async def reject(self, interaction: Any, button: Any) -> None:  # noqa: ANN001
                await self._resolve(interaction, "reject")

            async def _resolve(self, interaction: Any, data: str) -> None:  # noqa: ANN001
                incoming = IncomingMessage(
                    channel="discord",
                    user_id=str(interaction.user.id),
                    username=getattr(interaction.user, "name", ""),
                    text="",
                    callback_data=data,
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    role_ids=[str(r.id) for r in getattr(interaction.user, "roles", [])],
                )
                reply = core.handle_message(incoming)
                await interaction.response.send_message(
                    reply.text if reply else "Nothing is waiting for approval.", ephemeral=True
                )

        return ApprovalView()

    def _send_reply(self, destination: Any, reply: OutgoingMessage) -> Any:
        async def _send() -> None:
            kwargs: Dict[str, Any] = {}
            if reply.approval:
                kwargs["view"] = self._approval_view(self.core)
            if len(reply.text) > 2000:  # Discord message cap
                for i in range(0, len(reply.text), 2000):
                    await destination.send(reply.text[i : i + 2000], **(kwargs if i == 0 else {}))
            else:
                await destination.send(reply.text or "…", **kwargs)

        return _send()

    def _wire_events(self) -> None:
        bot = self.bot
        core = self.core

        @bot.event
        async def on_ready() -> None:  # noqa: F811
            try:
                await bot.tree.sync()
            except Exception:
                pass

        @bot.tree.command(name="aryx", description="Ask ARYx something")
        async def aryx_command(interaction: Any, prompt: str) -> None:  # noqa: F811
            incoming = IncomingMessage(
                channel="discord",
                user_id=str(interaction.user.id),
                username=getattr(interaction.user, "name", ""),
                text=prompt,
                guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                role_ids=[str(r.id) for r in getattr(interaction.user, "roles", [])],
            )
            reply = core.handle_message(incoming)
            if reply is None:
                await interaction.response.send_message("…", ephemeral=True)
                return
            thread = None
            try:
                thread = await interaction.channel.create_thread(
                    name=f"aryx: {prompt[:40]}", auto_archive_duration=60
                )
            except Exception:
                thread = None
            dest = thread or interaction.channel
            await interaction.response.defer(ephemeral=False)
            await dest.send(reply.text or "…")

        @bot.event
        async def on_message(message: Any) -> None:  # noqa: F811
            if message.author.bot:
                return
            if bot.user not in message.mentions:
                await bot.process_commands(message)
                return
            text = message.content.replace(f"<@{bot.user.id}>", "").strip()
            incoming = IncomingMessage(
                channel="discord",
                user_id=str(message.author.id),
                username=getattr(message.author, "name", ""),
                text=text,
                guild_id=str(message.guild.id) if message.guild else None,
                role_ids=[str(r.id) for r in getattr(message.author, "roles", [])],
            )
            reply = core.handle_message(incoming)
            if reply is None:
                return
            await self._send_reply(message.channel, reply)

    def run(self) -> None:
        """Blocking. `aryx gateway start` runs this in a thread."""
        self.bot.run(self.token)
