"""
ARYx AGENT - Gateway setup wizard (Section 16.10).

Interactive, <5 minutes per channel, exact copy-paste steps. Tokens
are read with getpass (no echo) and never printed back — not even
partially. A token printed anywhere is a leaked token.
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, Optional

from aryx.gateway.config import (
    CHANNELS,
    channel_config,
    load_gateway_config,
    save_gateway_config,
)
from aryx.gateway.types import IncomingMessage  # noqa: F401  (re-exported for adapters)


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{text}{suffix}: ").strip()
    return answer or default


def _prompt_secret(text: str) -> str:
    try:
        import getpass

        return getpass.getpass(f"{text}: ").strip()
    except Exception:
        return input(f"{text}: ").strip()


def setup_telegram(config: Dict[str, Any]) -> Dict[str, Any]:
    print("\n--- Telegram setup (recommended, free) ---")
    print("1. Open Telegram, message @BotFather, send /newbot and follow it.")
    print("2. BotFather gives you a bot token. Paste it below (it will not echo).")
    token = _prompt_secret("Bot token")
    if not token:
        print("No token entered — Telegram not enabled.")
        return config
    cfg = channel_config(config, "telegram")
    cfg["bot_token"] = token
    cfg["enabled"] = True
    print("\n3. Message @BotFather again, send /setcommands and paste this:")
    from aryx.gateway.channels.telegram import BOT_COMMANDS_TEXT

    print(BOT_COMMANDS_TEXT)
    print("4. Send /whoami to your bot to get your Telegram ID, add it to")
    print("   allowed_user_ids in ~/.aryx/gateway.toml, then run `aryx gateway reload`.")
    print("   Until then, the bot stays silent for everyone (default deny).")
    return config


def setup_webui(config: Dict[str, Any]) -> Dict[str, Any]:
    print("\n--- Web UI setup (browser access) ---")
    cfg = channel_config(config, "webui")
    token = secrets.token_hex(16)
    cfg["auth_token"] = token
    cfg["enabled"] = True
    host = _prompt("Bind host (127.0.0.1 = this computer only)", cfg.get("host", "127.0.0.1"))
    port = _prompt("Port", str(cfg.get("port", 8765)))
    cfg["host"] = host
    try:
        cfg["port"] = int(port)
    except ValueError:
        cfg["port"] = 8765
    print(f"\nWeb UI enabled. Start it with: aryx gateway start webui")
    print("Your private URL (keep it secret — the token is the password):")
    print(f"  http://{cfg['host']}:{cfg['port']}/?token={token}")
    return config


def setup_whatsapp(config: Dict[str, Any]) -> Dict[str, Any]:
    print("\n--- WhatsApp setup ---")
    print("Twilio is easier (no business verification for testing) but costs money.")
    print("Meta Cloud API is free for 1000 conversations/month but needs a Meta app")
    print("and a verified business.")
    choice = _prompt("Twilio or Meta Cloud? (1 = Twilio, 2 = Meta)", "1")
    cfg = channel_config(config, "whatsapp")
    if choice == "2":
        cfg["provider"] = "meta"
        cfg["access_token"] = _prompt_secret("Meta permanent access token")
        cfg["phone_number_id"] = _prompt("Meta phone number ID")
        cfg["app_secret"] = _prompt_secret("Meta app secret (for webhook verification)")
        print("\nWebhook URL to paste into your Meta app (after starting a tunnel):")
        print("  https://<your-tunnel-domain>/webhook/whatsapp")
    else:
        cfg["provider"] = "twilio"
        cfg["account_sid"] = _prompt("Twilio account SID")
        cfg["auth_token"] = _prompt_secret("Twilio auth token")
        cfg["from_number"] = _prompt("Twilio WhatsApp sender number (e.g. +14155238886)")
        print("\nWebhook URL to paste into your Twilio WhatsApp sender:")
        print("  https://<your-tunnel-domain>/webhook/whatsapp")
        print("Tip: `cloudflared tunnel --url http://127.0.0.1:8766` gives you a public URL.")
    cfg["enabled"] = True
    print("Then add your own number to allowed_numbers in ~/.aryx/gateway.toml")
    print("and run `aryx gateway reload`.")
    return config


def setup_discord(config: Dict[str, Any]) -> Dict[str, Any]:
    print("\n--- Discord setup ---")
    print("1. Create an application at https://discord.com/developers/applications")
    print("2. Add a Bot, copy its token, enable MESSAGE CONTENT INTENT.")
    print("3. Invite it with: applications.commands + bot scopes.")
    token = _prompt_secret("Discord bot token")
    if not token:
        print("No token entered — Discord not enabled.")
        return config
    cfg = channel_config(config, "discord")
    cfg["bot_token"] = token
    cfg["enabled"] = True
    print("Also install the library: pip install 'aryx-agent[discord]'")
    print("Then add your guild ID to allowed_guilds in ~/.aryx/gateway.toml.")
    return config


def setup_slack(config: Dict[str, Any]) -> Dict[str, Any]:
    print("\n--- Slack setup ---")
    print("1. Create an app at https://api.slack.com/apps, enable Socket Mode.")
    print("2. Add scopes: app_mentions:read, chat:write, commands.")
    print("3. Install it to your workspace and copy both tokens.")
    bot_token = _prompt_secret("Slack bot token (xoxb-...)")
    app_token = _prompt_secret("Slack app token (xapp-...)")
    if not bot_token or not app_token:
        print("Both tokens are needed — Slack not enabled.")
        return config
    cfg = channel_config(config, "slack")
    cfg["bot_token"] = bot_token
    cfg["app_token"] = app_token
    cfg["enabled"] = True
    print("Also install the library: pip install 'aryx-agent[slack]'")
    print("Then add your workspace ID to allowed_workspaces in ~/.aryx/gateway.toml.")
    return config


_SETUP_FNS = {
    "telegram": setup_telegram,
    "webui": setup_webui,
    "whatsapp": setup_whatsapp,
    "discord": setup_discord,
    "slack": setup_slack,
}


def add_channel(config: Dict[str, Any], channel: str) -> Dict[str, Any]:
    channel = channel.lower()
    if channel not in _SETUP_FNS:
        print(f"Unknown channel: {channel}. Choose from: {', '.join(CHANNELS)}")
        return config
    return _SETUP_FNS[channel](config)


def run_setup_wizard() -> int:
    """Step 1: pick channels. Step 2: each channel's flow. Step 3: next steps."""
    config = load_gateway_config()
    print("\n=== ARYx gateway setup ===")
    print("Which channels do you want to enable? (comma-separated numbers)")
    for i, channel in enumerate(CHANNELS, 1):
        hint = "recommended, free" if channel == "telegram" else ""
        print(f"  {i}. {channel} {hint}")
    picked = _prompt("Your choice (e.g. 1,5)", "1")
    chosen: list = []
    for part in picked.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(CHANNELS):
            chosen.append(CHANNELS[int(part) - 1])
        elif part.lower() in CHANNELS:
            chosen.append(part.lower())
    if not chosen:
        print("Nothing selected. Run `aryx gateway setup` again when ready.")
        return 1
    for channel in chosen:
        config = add_channel(config, channel)
    save_gateway_config(config)
    print("\nAll set! Start your gateway with:  aryx gateway start")
    print("View status anytime with:  aryx gateway status")
    print("Link channels to one identity with:  aryx gateway link")
    return 0
