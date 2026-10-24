# ARYx Gateway — control the same agent from anywhere (Section 16)

Without a gateway, ARYx lives in the terminal. With one, the **same
agent brain** answers on Telegram, WhatsApp, Discord, Slack, or a
browser Web UI — and memory + skills are **shared** across channels.
Start a task on Telegram, continue it on the CLI.

```
┌─────────────────────────────────────────────────────────┐
│  CHANNELS (adapters)                                    │
│  ├── telegram.py   (Bot API over httpx, long-polling)   │
│  ├── whatsapp.py   (Twilio / Meta Cloud API webhooks)   │
│  ├── discord.py    (discord.py, optional extra)         │
│  ├── slack.py      (slack-bolt, Socket Mode)            │
│  └── webui.py      (stdlib server + single HTML page)   │
└────────────────────┬────────────────────────────────────┘
                     │  all adapters emit IncomingMessage
                     ▼
┌─────────────────────────────────────────────────────────┐
│  GATEWAY CORE (aryx/gateway/core.py)                    │
│  AuthManager · SessionRouter · RateLimiter · Queue      │
└────────────────────┬────────────────────────────────────┘
                     │  routes to
                     ▼
┌─────────────────────────────────────────────────────────┐
│  AGENT CORE (providers + tools + memory + skills)       │
│  Same loop as the terminal (aryx/gateway/agent.py)      │
└─────────────────────────────────────────────────────────┘
```

## Quick start

```bash
aryx gateway setup        # interactive wizard (<5 min per channel)
aryx gateway start        # start all enabled channels
aryx gateway status       # which channels are running
aryx gateway link         # 10-minute code, then /link CODE on your channel
aryx gateway stop         # stop all
```

## Telegram (recommended, free)

```bash
aryx gateway add telegram
```

1. Message `@BotFather` on Telegram, send `/newbot`, copy the token.
2. Paste it when asked (it never echoes, never prints back).
3. Message `@BotFather` again, `/setcommands`, paste the command list
   the wizard prints (`start`, `help`, `whoami`, `link`, `resume`,
   `new`, `stop`).
4. Send `/whoami` to your bot, add that ID to `allowed_user_ids` in
   `~/.aryx/gateway.toml`, then `aryx gateway reload`.

Long-polling is the default: no public IP, no server, no webhook.

## WhatsApp

```bash
aryx gateway add whatsapp
```

Pick Twilio (easier, paid) or Meta Cloud API (free tier, needs a
Meta app + verified business). The wizard prints the exact webhook
URL to paste. Put a tunnel in front of the local webhook server
(`cloudflared tunnel --url http://127.0.0.1:8766`).
Note the 24-hour session window: outside it, business-initiated
messages need pre-approved templates.

## Discord / Slack

```bash
pip install 'aryx-agent[discord]'   # or 'aryx-agent[slack]'
aryx gateway add discord            # or: aryx gateway add slack
```

Discord: slash `/aryx`, @-mentions, one thread per task, approval
buttons. Slack: `/aryx` slash command, @-mentions, Block Kit buttons,
Socket Mode (no public URL needed).

## Web UI

```bash
aryx gateway add webui
aryx gateway start webui
# -> http://127.0.0.1:8765/?token=XYZ
```

A single dark-mode HTML page, no build step, mobile-responsive.
Auth is the token in the URL — keep that link private. Default bind
is `127.0.0.1` (this computer only) on purpose.

## Shared identity: `/link`

```bash
aryx gateway link          # prints a 6-character code, valid 10 minutes
```

On any channel, send `/link A7K9P2`. That chat is now bound to your
CLI identity: same memory, same skills, same config. Gateway turns
are also mirrored into CLI memory, so terminal `/history` shows what
happened on Telegram/Web UI. `/resume` reopens your last session on
any channel; `/new` starts fresh.

## Security (read this before going public)

- **Default deny.** Only allow-listed users get replies. Anyone else
  gets *silence* — the bot never confirms it exists to strangers.
  Every rejected attempt is logged to `~/.aryx/logs/gateway.log`.
- **Safe mode is forced** on Telegram/WhatsApp/Discord/Slack. Writes
  and bash ask first via native Approve/Reject buttons. `yolo` on a
  messaging channel needs an explicit per-user exemption in
  `gateway.toml` (`allow_yolo_users`).
- **Approvals time out** after 5 minutes (auto-reject).
- **Logs never contain message text or secrets** — lengths and hashes
  only. `aryx doctor` check 14 scans `gateway.log` for leaked keys.
- **Web UI**: token auth, localhost-only default. If you expose it
  publicly (tunnel), the token in the URL is the only thing standing
  between the internet and an agent that can run bash. Keep it secret.

## Approvals on each channel

| Channel  | Approval UI |
|----------|-------------|
| Telegram | Inline keyboard: Approve / Reject |
| WhatsApp | Numbered menu: reply `1` = Approve, `2` = Reject |
| Discord  | Ephemeral buttons |
| Slack    | Block Kit buttons |
| Web UI   | HTML buttons |

## Doctor coverage (checks 10–15)

`aryx doctor` now also checks: gateway.toml syntax, enabled-channel
credentials, webhook reachability (webhook-mode channels only),
non-empty allowlists, gateway.log leak scan, and whether a gateway
is running.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Bot silent on Telegram | You are not allow-listed yet. `/whoami` → add ID → `aryx gateway reload`. |
| Bot replies to strangers | Allowlist misconfigured — check `aryx doctor` check 13. |
| Webhook not received (WhatsApp) | Tunnel down, or wrong webhook URL pasted. `aryx doctor` check 12. |
| `yolo` ignored on Telegram | By design: messaging channels force safe mode unless you are in `allow_yolo_users`. |
| Gateway starts but a channel fails | See the printed error; `aryx gateway test <channel>` checks credentials. |
| Old code rejected | Link codes last 10 minutes; device codes are single-attempt. Get a fresh one. |

## FAQ

**Can I use the same bot on Telegram and WhatsApp?**
Yes — link both with `aryx gateway link`. One identity, one memory.

**Do I need a server?**
No for Telegram (long-polling), Slack (Socket Mode) and Web UI
(localhost). WhatsApp webhooks need a public URL — use a tunnel.

**Does the gateway work without an API key?**
Like the CLI, it needs a configured provider (or local Ollama).
Without one it replies with setup instructions instead of crashing.

## Known v1 limitations (honest list)

- Web UI uses request/response polling, not WebSocket streaming.
  Streaming is a future enhancement; replies are identical.
- Voice notes are accepted but **not transcribed** in this build
  (no Whisper/Gemini-audio wiring yet) — the bot says so plainly.
- Discord/Slack need their optional extras installed.
- `aryx gateway start` runs in the foreground; background/service
  management (systemd/launchd units) is not auto-installed yet —
  run it in tmux/screen, or start it on login yourself.
- WhatsApp file sending is provider-dependent; text + approvals
  are fully supported, file delivery notes the local path.
