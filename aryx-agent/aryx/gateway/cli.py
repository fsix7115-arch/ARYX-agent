"""
ARYx AGENT - `aryx gateway` command dispatch (Section 16.10).

One command, many actions (this keeps both the Typer path and the
argparse fallback in cli.py working identically):

  aryx gateway setup        Interactive setup wizard
  aryx gateway start        Start all enabled channels (foreground)
  aryx gateway start <ch>   Start only one channel
  aryx gateway stop         Stop a running gateway (by PID file)
  aryx gateway status       Show running channels
  aryx gateway reload       Validate + reload gateway.toml
  aryx gateway link         Generate a 10-minute linking code
  aryx gateway add <ch>     Add a channel (runs its setup flow)
  aryx gateway remove <ch>  Disable a channel
  aryx gateway logs         Tail gateway logs (no message text inside)
  aryx gateway test <ch>    Verify a channel's credentials
  aryx gateway help         This help
  aryx gateway whoami       How to find your channel user ID

`start` runs in the foreground (Ctrl+C stops it) and records its
PID in ~/.aryx/gateway.state.json so `stop`/`status` can find it.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aryx.gateway.agent import AgentRunner
from aryx.gateway.config import (
    CHANNELS,
    GATEWAY_LOG,
    GATEWAY_STATE_FILE,
    channel_config,
    enabled_channels,
    is_channel_enabled,
    load_gateway_config,
    save_gateway_config,
)
from aryx.gateway.core import GatewayCore
from aryx.gateway.identity import (
    ensure_cli_identity,
    generate_link_code,
    get_gateway_db_connection,
)

GATEWAY_HELP_TEXT = """ARYx gateway — control the same agent from anywhere.

  aryx gateway setup        Interactive setup wizard
  aryx gateway start        Start all enabled channels
  aryx gateway start <ch>   Start only one channel
  aryx gateway stop         Stop all
  aryx gateway status       Show running channels
  aryx gateway reload       Reload gateway.toml (no restart)
  aryx gateway link         Generate linking code (10 minutes)
  aryx gateway add <ch>     Add a channel (runs its setup)
  aryx gateway remove <ch>  Remove a channel
  aryx gateway logs         Tail gateway logs
  aryx gateway test <ch>    Send a test message to verify setup
  aryx gateway whoami       How to find your channel user ID

Channels: telegram, whatsapp, discord, slack, webui
Docs: docs/GATEWAY.md
"""


def _load_cli_config() -> Dict[str, Any]:
    # A broken gateway.toml must fail with ONE clean line, never a
    # traceback: this is a CLI entry point, and the user needs the
    # file/line error, not a stack trace. Every direct
    # load_gateway_config() call in this module goes through here.
    try:
        return load_gateway_config()
    except Exception as e:  # noqa: BLE001 - surfaced as a clean CLI error
        print(f"gateway.toml has an error: {e}")
        print("Fix it, then retry. (Check: aryx doctor)")
        raise SystemExit(1)


def _build_core() -> GatewayCore:
    return GatewayCore(config=_load_cli_config(), agent_runner=AgentRunner())


def _read_state() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(GATEWAY_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_state(channels: List[str]) -> None:
    GATEWAY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    GATEWAY_STATE_FILE.write_text(
        json.dumps({"pid": os.getpid(), "started_at": time.time(), "channels": channels}),
        encoding="utf-8",
    )


def _clear_state() -> None:
    try:
        GATEWAY_STATE_FILE.unlink()
    except OSError:
        pass


def _state_alive(state: Optional[Dict[str, Any]]) -> bool:
    if not state or not state.get("pid"):
        return False
    try:
        os.kill(int(state["pid"]), 0)
        return True
    except (OSError, ValueError):
        return False


# -- individual actions ----------------------------------------------------
def _cmd_status() -> int:
    config = _load_cli_config()
    state = _read_state()
    running = _state_alive(state)
    running_channels = state.get("channels", []) if running else []
    print("\nARYx gateway status")
    print(f"  Running: {'yes' if running else 'no'}")
    if running:
        print(f"  PID: {state.get('pid')}")
    print(f"  {'Channel':<10} {'Enabled':<8} {'Running':<8} Messages today")
    core = _build_core()
    for channel in CHANNELS:
        enabled = is_channel_enabled(config, channel)
        is_running = channel in running_channels
        today = core.messages_today(channel)
        print(f"  {channel:<10} {'yes' if enabled else 'no':<8} {'yes' if is_running else 'no':<8} {today}")
    if not enabled_channels(config):
        print("\n  No channels enabled yet. Run: aryx gateway setup")
    return 0


def _cmd_link() -> int:
    conn = get_gateway_db_connection()
    identity_id = ensure_cli_identity(conn)
    code = generate_link_code(conn, identity_id)
    print(f"\nYour linking code (valid 10 minutes): {code}")
    print("On Telegram/WhatsApp/etc., send:  /link " + code)
    print("That chat will then share memory, skills and config with this computer.")
    return 0


def _cmd_reload() -> int:
    # Validate BEFORE building the core: reload's whole job is to
    # report a broken file cleanly, and building a core on a broken
    # file is exactly what used to traceback.
    from aryx.gateway.config import validate_gateway_config

    err = validate_gateway_config()
    if err:
        print(f"gateway.toml has an error: {err}")
        print("Fix it, then run `aryx gateway reload` again.")
        return 1
    core = _build_core()
    err = core.reload_config()
    if err:
        print(f"gateway.toml has an error: {err}")
        print("Fix it, then run `aryx gateway reload` again.")
        return 1
    print("gateway.toml is valid and reloaded. Allowlist changes apply to new messages.")
    return 0


def _cmd_logs() -> int:
    if not GATEWAY_LOG.exists():
        print("No gateway logs yet. Start the gateway first: aryx gateway start")
        return 0
    lines = GATEWAY_LOG.read_text(encoding="utf-8").splitlines()
    print(f"Last {min(40, len(lines))} gateway log lines (lengths + hashes only, never message text):")
    for line in lines[-40:]:
        print(f"  {line}")
    return 0


def _cmd_test(channel: str) -> int:
    channel = channel.lower()
    if channel not in CHANNELS:
        print(f"Unknown channel: {channel}. Choose from: {', '.join(CHANNELS)}")
        return 1
    config = _load_cli_config()
    cfg = channel_config(config, channel)
    if channel == "telegram":
        token = cfg.get("bot_token", "")
        if not token:
            print("No Telegram token. Run: aryx gateway add telegram")
            return 1
        from aryx.gateway.channels.telegram import TelegramAdapter

        try:
            info = TelegramAdapter(token, _build_core()).test_connection()
        except Exception as e:  # noqa: BLE001
            print(f"Telegram check failed: {e}")
            return 1
        print(f"Telegram OK: bot {info}")
        return 0
    if channel == "webui":
        if not cfg.get("auth_token"):
            print("No Web UI token. Run: aryx gateway add webui")
            return 1
        print(f"Web UI configured at http://{cfg.get('host')}:{cfg.get('port')}/ (token is set, never printed)")
        return 0
    if channel == "whatsapp":
        provider = cfg.get("provider", "twilio")
        needed = (
            ["account_sid", "auth_token", "from_number"]
            if provider == "twilio"
            else ["access_token", "phone_number_id"]
        )
        missing = [k for k in needed if not cfg.get(k)]
        if missing:
            print(f"WhatsApp ({provider}) is missing: {', '.join(missing)}. Run: aryx gateway add whatsapp")
            return 1
        print(f"WhatsApp ({provider}) credentials are present. Start it with: aryx gateway start whatsapp")
        return 0
    if channel == "discord":
        if not cfg.get("bot_token"):
            print("No Discord token. Run: aryx gateway add discord")
            return 1
        try:
            import discord  # noqa: F401
        except ImportError:
            print("discord.py is not installed. Run: pip install 'aryx-agent[discord]'")
            return 1
        print("Discord token present and discord.py installed.")
        return 0
    if channel == "slack":
        if not (cfg.get("bot_token") and cfg.get("app_token")):
            print("Slack needs both tokens. Run: aryx gateway add slack")
            return 1
        try:
            import slack_bolt  # noqa: F401
        except ImportError:
            print("slack-bolt is not installed. Run: pip install 'aryx-agent[slack]'")
            return 1
        print("Slack tokens present and slack-bolt installed.")
        return 0
    return 1


def _cmd_whoami() -> int:
    print("\nTo find your channel user ID, send /whoami to the bot on that channel.")
    print("The bot replies with your channel + ID. Give that ID to the bot owner,")
    print("who adds it to allowed_user_ids in ~/.aryx/gateway.toml and runs:")
    print("  aryx gateway reload")
    return 0


def _start_adapters(core: GatewayCore, wanted: List[str]) -> List[str]:
    """Build + start adapters in threads. Returns the channels that started."""
    from aryx.gateway.channels.telegram import TelegramAdapter
    from aryx.gateway.channels.webui import WebUIAdapter

    config = core.config
    started: List[str] = []
    stop_event = threading.Event()
    core_stop = getattr(core, "_stop_event", None)
    if core_stop is None:
        core_stop = stop_event
        core._stop_event = stop_event  # type: ignore[attr-defined]

    def _fail(channel: str, error: Exception) -> None:
        print(f"  ! {channel}: could not start ({error})")

    for channel in wanted:
        cfg = channel_config(config, channel)
        try:
            if channel == "telegram":
                adapter = TelegramAdapter(cfg.get("bot_token", ""), core)
                threading.Thread(target=adapter.run_polling, args=(stop_event,), daemon=True).start()
            elif channel == "webui":
                adapter = WebUIAdapter(core, cfg.get("host", "127.0.0.1"), int(cfg.get("port", 8765)), cfg.get("auth_token", ""))
                adapter.start_in_thread()
                print(f"  Web UI: {adapter.url()}")
            elif channel == "whatsapp":
                from aryx.gateway.channels.whatsapp import MetaSender, TwilioSender, WhatsAppAdapter

                if cfg.get("provider") == "meta":
                    sender: Any = MetaSender(cfg.get("access_token", ""), cfg.get("phone_number_id", ""))
                else:
                    sender = TwilioSender(cfg.get("account_sid", ""), cfg.get("auth_token", ""), cfg.get("from_number", ""))
                wa = WhatsAppAdapter(core, sender, cfg.get("provider", "twilio"))
                wa.start_webhook_server(port=8766)
                print("  WhatsApp webhook listening on 127.0.0.1:8766 (put a tunnel in front of it)")
            elif channel == "discord":
                from aryx.gateway.channels.discord import DiscordAdapter

                adapter_d = DiscordAdapter(cfg.get("bot_token", ""), core)
                threading.Thread(target=adapter_d.run, daemon=True).start()
            elif channel == "slack":
                from aryx.gateway.channels.slack import SlackAdapter

                adapter_s = SlackAdapter(cfg.get("bot_token", ""), cfg.get("app_token", ""), core)
                threading.Thread(target=adapter_s.run, daemon=True).start()
            started.append(channel)
            print(f"  ✓ {channel} started")
        except Exception as e:  # noqa: BLE001
            _fail(channel, e)
    return started


def _cmd_start(target: Optional[str]) -> int:
    config = _load_cli_config()
    if target:
        wanted = [target.lower()]
        if wanted[0] not in CHANNELS:
            print(f"Unknown channel: {target}. Choose from: {', '.join(CHANNELS)}")
            return 1
        if not is_channel_enabled(config, wanted[0]):
            print(f"{wanted[0]} is not enabled. Run: aryx gateway add {wanted[0]}")
            return 1
    else:
        wanted = enabled_channels(config)
        if not wanted:
            print("No channels enabled yet. Run: aryx gateway setup")
            return 1
    core = _build_core()
    print("\nStarting ARYx gateway (Ctrl+C stops it)...")
    started = _start_adapters(core, wanted)
    if not started:
        print("Nothing started. Fix the errors above, then try again.")
        return 1
    _write_state(started)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping gateway...")
    finally:
        _clear_state()
    return 0


def _cmd_stop() -> int:
    state = _read_state()
    if not _state_alive(state):
        print("No gateway is currently running (no live PID file).")
        _clear_state()
        return 0
    pid = int(state["pid"])
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped gateway (PID {pid}).")
    except OSError as e:
        print(f"Could not stop PID {pid}: {e}")
        return 1
    _clear_state()
    return 0


# -- dispatch ---------------------------------------------------------------
def run_gateway_command(action: str, target: Optional[str] = None) -> int:
    """Dispatch one `aryx gateway <action> [target]` call. Returns exit code."""
    action = (action or "help").lower()
    if action == "help":
        print(GATEWAY_HELP_TEXT)
        return 0
    if action == "setup":
        from aryx.gateway.setup_wizard import run_setup_wizard

        return run_setup_wizard()
    if action == "start":
        return _cmd_start(target)
    if action == "stop":
        return _cmd_stop()
    if action == "status":
        return _cmd_status()
    if action == "reload":
        return _cmd_reload()
    if action == "link":
        return _cmd_link()
    if action == "add":
        if not target:
            print("Usage: aryx gateway add <channel>")
            return 1
        from aryx.gateway.setup_wizard import add_channel

        config = add_channel(_load_cli_config(), target)
        save_gateway_config(config)
        return 0
    if action == "remove":
        if not target or target.lower() not in CHANNELS:
            print(f"Usage: aryx gateway remove <channel>  (channels: {', '.join(CHANNELS)})")
            return 1
        config = _load_cli_config()
        config[target.lower()]["enabled"] = False
        save_gateway_config(config)
        print(f"{target.lower()} disabled. Credentials stay in gateway.toml until you delete them.")
        return 0
    if action == "logs":
        return _cmd_logs()
    if action == "test":
        if not target:
            print("Usage: aryx gateway test <channel>")
            return 1
        return _cmd_test(target)
    if action == "whoami":
        return _cmd_whoami()
    print(f"Unknown gateway action: {action}\n")
    print(GATEWAY_HELP_TEXT)
    return 1
