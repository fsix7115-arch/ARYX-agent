# ARYx AGENT
Your terminal AI agent. One command to install. Any API key.

```
    █████╗ ██████╗ ██╗   ██╗██╗  ██╗
   ██╔══██╗██╔══██╗╚██╗ ██╔╝╚██╗██╔╝
   ███████║██████╔╝ ╚████╔╝  ╚███╔╝ 
   ██╔══██║██╔══██╗  ╚██╔╝   ██╔██╗ 
   ██║  ██║██║  ██║   ██║   ██╔╝ ██╗
   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝
       A G E N T  ·  v0.1.0
```

> **Zero Friction Promise:** Clone repo, run ONE command, paste ANY key, and chat within 30 seconds. No confusing steps. No silent failures. Self-healing diagnostics.

---

## Quickstart (30 seconds)

```bash
git clone https://github.com/fsix7115-arch/ARYX-agent
cd ARYX-agent/aryx-agent
./install.sh
aryx
```

Paste your API key when asked. That's it. ARYx auto-detects the provider from the key prefix, validates it with a tiny 5-token probe, and drops you straight into the chat.

---

## See it in action

Real run of this build — `aryx doctor`, `aryx --help`, `aryx --banner`,
and the 30-second first-run setup (the Ollama path needs no API key):

![ARYx AGENT demo](docs/demo.gif)

Screenshots:

![aryx doctor](docs/screenshots/doctor.png)
![aryx --help](docs/screenshots/help.png)
![aryx --banner](docs/screenshots/banner.png)
![First-run setup](docs/screenshots/setup.png)

Note: the doctor screenshot was taken in a sandbox without external network
access, so the network check fails there — on a normal machine it passes.
Each failure carries its exact fix, which is the point of `aryx doctor`.

---

## Gateway: control ARYx from anywhere

The same agent brain answers on Telegram, WhatsApp, Discord, Slack,
or a browser Web UI — with memory and skills shared across channels.
Start a task on Telegram, continue it on the terminal.

```bash
aryx gateway setup        # interactive wizard (<5 min per channel)
aryx gateway start        # start all enabled channels
aryx gateway link         # 10-minute code, then /link CODE on your channel
```

Telegram (Bot API) and the Web UI need no extra install. Discord and
Slack need `pip install 'aryx-agent[discord]'` / `'aryx-agent[slack]'`.
Security default is deny: only allow-listed users get replies, and
messaging channels are forced into safe approval mode with native
Approve/Reject buttons. Full guide: [docs/GATEWAY.md](docs/GATEWAY.md).

---

## Product Promise

1. **ONE-COMMAND INSTALL** — `./install.sh` handles OS detection (macOS, Linux, WSL), Python 3.10+ verification, isolated `pipx` installation, and PATH configuration.
2. **ONE-QUESTION SETUP** — Paste your key, ARYx auto-detects Google Gemini, OpenAI, Anthropic, Groq, or OpenRouter automatically.
3. **ANY PROVIDER** — Gemini, OpenAI, Anthropic, Groq, OpenRouter, Mistral, Together, or local Ollama.
4. **NEVER STUCK** — `aryx doctor` runs 9 functional probes and `--fix` heals 90% of configuration issues automatically.
5. **ALWAYS HELP** — Comprehensive CLI tables (`aryx --help`), in-chat `/help`, and step-by-step guides (`aryx help setup`).
6. **SELF-IMPROVING** — Procedural skills are generated automatically when complex tasks succeed (>5 tool calls), tested through a quality gate, and versioned.
7. **STICKY MEMORY** — SQLite memory at `~/.aryx/memory.db` with episodic history, FTS5 full-text search, and semantic fact extraction.

---

## Supported Providers

| Provider | Free tier? | Key link | Default Model | Prefix |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini** | **Yes (Generous)** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `gemini-2.5-flash` | `AIza...` |
| **Groq** | **Yes** | [console.groq.com](https://console.groq.com/keys) | `llama-3.3-70b` | `gsk_...` |
| **Ollama** | **Local / Free** | [ollama.com](https://ollama.com) | `llama3.2` | (no key needed) |
| **OpenAI** | Trial / Paid | [platform.openai.com](https://platform.openai.com/api-keys) | `gpt-4.1-mini` | `sk-...` |
| **Anthropic**| Paid | [console.anthropic.com](https://console.anthropic.com) | `claude-sonnet-4` | `sk-ant-...` |
| **OpenRouter**| Unified | [openrouter.ai](https://openrouter.ai/keys) | `claude-3.5-sonnet`| `sk-or-...` |

---

## Built-in Tools

- **Read-Only (Auto-approved):** `read_file`, `list_dir`, `glob`, `grep`, `web_fetch`, `web_search`.
- **Write Actions (Confirmation required unless `--yolo`):** `write_file`, `edit_file` (surgical text replacement), `bash` (sandboxed subprocess with 30s timeout and safety blocklist), `python` (sandboxed snippet execution).
- **Safety Snapshots:** Before any file modification, a snapshot is saved to `~/.aryx/snapshots/`. Undo edits anytime with `/revert`.

---

## In-Chat Commands

```
/help              Show in-chat slash command help
/model             Show active model or switch providers (/model use openai)
/memory            Show learned semantic facts about you and your preferences
/skills            List learned procedural skills & success rates
/skills show <n>   View full Markdown procedure of a learned skill
/doctor            Run 9-probe health diagnostic check right now
/revert [N]        Undo file changes from the last N modifications
/history <query>   Full-text search through past conversation transcripts
/dashboard         View token metrics, active model, and memory size
/clear             Clear current session context while keeping persistent memory
/quit              Exit ARYx AGENT
```

---

## Doctor Self-Diagnostics & Auto-Repair

Run `aryx doctor` anytime to perform 9 live functional checks:
1. Python version >= 3.10
2. `aryx` binary present on PATH
3. `~/.aryx/` directory permissions (chmod 700)
4. `config.toml` exists and active key is configured
5. API key functional probe (live 5-token call)
6. Network connectivity to AI endpoints
7. SQLite memory database health
8. Skills directory readability
9. Free disk space (> 50 MB)

```bash
# Auto-repair safe issues automatically:
aryx doctor --fix

# Machine-readable JSON output for CI pipelines:
aryx doctor --json
```

---

## Troubleshooting

- `command not found: aryx` -> Add `~/.local/bin` to your PATH:
  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  ```
- Key rejected -> Check for extra spaces, or run:
  ```bash
  aryx doctor --fix
  ```
- Anything else -> Run:
  ```bash
  aryx doctor
  ```

---

## License

MIT © ARYx Open Source Team
