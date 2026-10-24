# ARYx AGENT — 30-Second Setup Guide

This guide walks you through getting up and running with ARYx AGENT in under half a minute.

## Step 1: Install with One Command

Run the idempotent installer:

```bash
git clone https://github.com/aryx-agent/aryx-agent
cd aryx-agent
./install.sh
```

The script will:
1. Verify Python 3.10+ exists (or give you the exact command for your OS).
2. Install via isolated `pipx`.
3. Configure `~/.local/bin` on your PATH if needed.

## Step 2: Start the Agent

```bash
aryx
```

## Step 3: Paste Any API Key

When prompted:
```text
Paste your API key (or press Enter to choose a provider):
```

Paste your key directly. ARYx inspects the key prefix:
- `AIza...` → Automatically activates **Google Gemini**
- `sk-ant-...` → Automatically activates **Anthropic Claude**
- `sk-...` → Automatically activates **OpenAI**
- `gsk_...` → Automatically activates **Groq**
- `sk-or-...` → Automatically activates **OpenRouter**
- Pressing Enter or pasting an unlisted format lets you pick from a numbered provider menu or choose **Ollama** for 100% offline usage.

## Step 4: Verification & Secure Storage

ARYx runs an immediate 5-token probe to confirm the key works.
Once verified:
- Saved to `~/.aryx/config.toml` with restricted permissions (`chmod 600`).
- The interactive prompt `aryx > ` opens.

Ask your first question:
```bash
aryx > What files are in this project and how do I run the test suite?
```
