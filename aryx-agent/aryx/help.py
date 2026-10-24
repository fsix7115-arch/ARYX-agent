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
                ["aryx --version", "Print version", "aryx --version"],
            ],
        )
        print("Tip: Run `aryx help setup` for a 30-second walkthrough.")
