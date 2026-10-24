"""
ARYx AGENT - Multi-Tier Help System & Guides
Provides CLI tables, interactive slash command references, and step-by-step guides.
"""

from __future__ import annotations

import sys
from aryx.ui.chat import render_table

HELP_SETUP_TEXT = """
================================================================================
                    ARYx AGENT — 30-SECOND SETUP GUIDE
================================================================================

1. GET AN API KEY:
   - Google Gemini (Recommended, Free tier):
     https://aistudio.google.com/apikey
   - Groq (Ultra-fast Llama 3.3, Free tier):
     https://console.groq.com/keys
   - OpenAI (GPT-4o, GPT-4.1-mini):
     https://platform.openai.com/api-keys
   - Anthropic (Claude 3.5 Sonnet / Sonnet 4):
     https://console.anthropic.com/settings/keys
   - Ollama (Local & completely offline, no key required):
     https://ollama.com

2. RUN THE AGENT:
   $ aryx

3. PASTE YOUR KEY:
   ARYx automatically detects your provider from the key prefix:
     • AIza...    -> Google Gemini
     • sk-ant-... -> Anthropic Claude
     • sk-...     -> OpenAI
     • gsk_...    -> Groq
     • sk-or-...  -> OpenRouter

4. START CHATTING:
   Ask any coding, research, or task question immediately!

--------------------------------------------------------------------------------
COMMON PROBLEMS & INSTANT FIXES:
--------------------------------------------------------------------------------
• "Command not found: aryx"
  Fix: Add ~/.local/bin to your PATH:
  $ export PATH="$HOME/.local/bin:$PATH"

• "That key didn't work"
  Fix: Check for extra whitespace or trailing spaces.
  Regenerate the key at your provider console and run `aryx config`.

• "No internet connection"
  Fix: Use Ollama completely offline with `ollama run llama3.2` and `/model use ollama`.

• Still stuck?
  Run: aryx doctor --fix
================================================================================
"""

HELP_PROVIDERS_TEXT = """
================================================================================
                    SUPPORTED PROVIDERS & KEY URLS
================================================================================

| Provider   | Free Tier? | Key Link                            | Default Model       |
|------------|------------|-------------------------------------|---------------------|
| Gemini     | YES        | https://aistudio.google.com/apikey  | gemini-2.5-flash    |
| Groq       | YES        | https://console.groq.com/keys       | llama-3.3-70b       |
| Ollama     | LOCAL/FREE | https://ollama.com                  | llama3.2            |
| OpenAI     | Paid/Trial | https://platform.openai.com/api-keys| gpt-4.1-mini        |
| Anthropic  | Paid       | https://console.anthropic.com       | claude-sonnet-4     |
| OpenRouter | Unified    | https://openrouter.ai/keys          | claude-3.5-sonnet   |

Run `aryx config` to view or switch your active provider.
================================================================================
"""

HELP_TOOLS_TEXT = """
================================================================================
                    ARYx AGENT BUILT-IN TOOLS
================================================================================

READ-ONLY TOOLS (Auto-approved by default):
  • read_file   : Read file contents safely with line limits
  • list_dir    : Inspect directory structure (flat or recursive)
  • glob        : Find files by glob pattern (e.g. '**/*.tsx')
  • grep        : Search file contents for regex or text strings
  • web_fetch   : Scrape and extract readable text from any URL
  • web_search  : Fast real-time technical web search

WRITE TOOLS (Require user confirmation unless --yolo mode):
  • write_file  : Create or overwrite a file (auto-snapshot taken)
  • edit_file   : Surgical string replacement (auto-snapshot taken)
  • bash        : Sandboxed shell execution with 30s timeout
  • python      : Sandboxed Python runner with timeout

RECOVERY & SNAPSHOTS:
  Before any file modification, ARYx saves a timestamped snapshot.
  Type `/revert` in chat anytime to rollback file changes!
================================================================================
"""

HELP_SKILLS_TEXT = """
================================================================================
                    ARYx AGENT SELF-IMPROVING SKILLS
================================================================================

HOW SKILLS WORK:
  1. COMPLEX TASK SUCCESS:
     When an agent finishes a task requiring more than 5 tool steps, it
     synthesizes a verified procedure into ~/.aryx/skills/<name>.md.

  2. QUALITY GATE:
     Each skill tracks its success count, fail count, and success rate.
     Skills with <20% success over 10+ uses are automatically archived.

  3. ADAPTIVE EVOLUTION:
     If a skill encounters an error during execution, the LLM rewrites it
     as <name>.v2.md with corrected steps.

IN-CHAT COMMANDS:
  • /skills            -> List all learned skills and success rates
  • /skills show <name>-> Inspect full Markdown instructions of a skill
================================================================================
"""

HELP_GATEWAY_TEXT = """
================================================================================
                    ARYx AGENT GATEWAY (Section 16)
================================================================================

Control the SAME agent brain from Telegram, WhatsApp, Discord, Slack
or a browser Web UI. Memory and skills are shared across channels:
link a chat to your CLI identity once with `aryx gateway link`,
then a task started on Telegram can continue on the terminal
(and shows up in CLI /history).

QUICK START:
  aryx gateway setup        Interactive wizard (Telegram first)
  aryx gateway start        Start all enabled channels
  aryx gateway status       Show running channels
  aryx gateway link         10-minute code for /link on your channel

CHANNEL COMMANDS (on any channel):
  /whoami  Show your channel user ID (for the allowlist)
  /link CODE  Bind this chat to your CLI identity
  /resume  Reopen your last session
  /new     Fresh session
  /stop    Cancel the current task

SECURITY (default deny):
  Only allow-listed users get replies; strangers get silence.
  Messaging channels are forced into safe approval mode: writes
  and bash ask first, with native Approve/Reject buttons.
  Full guide: docs/GATEWAY.md
================================================================================
"""

IN_CHAT_HELP_TEXT = """
Available in-chat slash commands:
  /help              Show this help menu
  /model             Switch provider or model
  /model use <name>  Switch active provider (e.g. /model use openai)
  /memory            Show what I remember about you (semantic facts)
  /skills            List learned procedural skills & success rates
  /skills show <name>Inspect a specific skill file
  /doctor            Run 9-probe health diagnostic check right now
  /revert            Undo file changes from recent tool steps
  /history <query>   Search past conversation logs with full text search
  /dashboard         View token usage, database size, and session stats
  /clear             Clear conversation context (keeps persistent memory)
  /quit              Exit ARYx AGENT

Gateway turns also appear here: messages from Telegram/Web UI are
mirrored into memory, so /history covers every channel.
"""



HELP_WEB_TEXT = """
================================================================================
                    ARYx AGENT WEB UI (Section 18)
================================================================================
  aryx web                     Launch at http://localhost:8765 (token auth)
  aryx web --port 3000         Custom port
  aryx web --no-browser        Don't auto-open the browser
  aryx web --public            Public URL via cloudflared tunnel (needs token)
  aryx web --auth password     Password login instead of token
  aryx web --auth none --allow-no-auth   No auth (localhost only, loud warning)

  The UI has a sessions sidebar (Today/Yesterday/Earlier), a model
  selector in the header, file upload/download, approval buttons,
  search (Cmd+K), export (Markdown/JSON), and voice input via your
  browser. Install it with: pip install "aryx-agent[web]"
  Full guide: docs/WEB_UI.md
"""

HELP_BROWSER_TEXT = """
================================================================================
                    ARYx AGENT BROWSER (Section 19)
================================================================================
  aryx browser setup           Headed login window + encrypted profile
  aryx browser profile list    Show profiles, logged-in sites, encryption
  aryx browser profile allow <profile> <domain>   Enable a domain
  aryx browser run read <profile> <url>           Read a page as the agent
  aryx browser run recipe <profile> <site> <action>

  The agent NEVER sees your passwords: you log in manually once, ARYx
  reuses the saved cookies. Profiles are AES-256 encrypted at rest.
  Banking, crypto, and admin sites are hardcoded-blocked. Sending,
  posting, buying, and following always need approval.
  Full guide: docs/BROWSER.md
"""

HELP_SCHEDULE_TEXT = """
================================================================================
                    ARYx AGENT SCHEDULER (Section 20)
================================================================================
  aryx schedule add            Interactive wizard (task, when, channel)
  aryx schedule add --cron "0 9 * * *" --prompt "..." --channel telegram
  aryx schedule list | pause | resume | run | logs | edit | remove <id>
  aryx schedule export --to backup.toml | import backup.toml
  aryx daemon start | stop | status | logs | install

  Natural language works too: "every morning at 9am", "weekdays at
  6pm", "every 2 hours". Scheduled writes need per-schedule
  allow_writes; dangerous bash commands stay blocked in every mode.
  From any channel: /schedule list | pause | resume | run | logs <id>
  Full guide: docs/SCHEDULER.md
"""

def show_help(topic: str = "general") -> None:
    """Print the appropriate help guide."""
    topic = topic.lower().strip()
    if topic in ("setup", "install", "quickstart"):
        print(HELP_SETUP_TEXT)
    elif topic in ("providers", "provider", "models"):
        print(HELP_PROVIDERS_TEXT)
    elif topic in ("tools", "tool"):
        print(HELP_TOOLS_TEXT)
    elif topic in ("skills", "skill", "memory"):
        print(HELP_SKILLS_TEXT)
    elif topic in ("gateway", "telegram", "whatsapp", "discord", "slack", "webui"):
        print(HELP_GATEWAY_TEXT)
    elif topic in ("web", "webui-app", "ui"):
        print(HELP_WEB_TEXT)
    elif topic in ("browser", "browsing"):
        print(HELP_BROWSER_TEXT)
    elif topic in ("schedule", "scheduler", "cron", "daemon"):
        print(HELP_SCHEDULE_TEXT)
    else:
        render_table(
            "ARYx AGENT CLI Commands",
            ["Command", "What it does", "Example"],
            [
                ["aryx", "Start interactive chat (first run = 30s setup)", "aryx"],
                ["aryx doctor", "Diagnose and self-heal setup issues", "aryx doctor --fix"],
                ["aryx config", "Open ~/.aryx/config.toml in $EDITOR", "aryx config"],
                ["aryx config show", "Print current config (keys redacted)", "aryx config show"],
                ["aryx update", "Update ARYx AGENT to latest version", "aryx update"],
                ["aryx uninstall", "Remove ARYx configuration and binary", "aryx uninstall"],
                ["aryx help setup", "Step-by-step setup guide & keys", "aryx help setup"],
                ["aryx help providers", "List all supported LLM providers", "aryx help providers"],
                ["aryx help tools", "List built-in tools and safety modes", "aryx help tools"],
                ["aryx help skills", "Explain self-improving skill system", "aryx help skills"],
                ["aryx gateway", "Control ARYx from Telegram, WhatsApp, Discord, Slack, Web UI", "aryx gateway setup"],
                ["aryx provider", "Add/list/test custom API providers (any endpoint, any auth)", "aryx provider add"],
                ["aryx web", "Professional web UI at http://localhost:8765", "aryx web"],
                ["aryx browser", "Secure AI browsing with encrypted profiles", "aryx browser setup"],
                ["aryx schedule", "Cron + natural-language scheduled tasks", "aryx schedule add"],
                ["aryx daemon", "Background scheduler (runs when ARYx is closed)", "aryx daemon start"],
                ["aryx --version", "Print version", "aryx --version"],
            ],
        )
        print("Tip: Run `aryx help setup` for a 30-second walkthrough.")
