# Provider Integration Guide

ARYx AGENT is completely provider-agnostic. You can switch between cloud providers and local models at any time without restarting the CLI.

## Obtaining API Keys

### 1. Google Gemini (Recommended — Generous Free Tier)
- **URL**: https://aistudio.google.com/apikey
- **Prefix**: `AIza...`
- **Default Model**: `gemini-2.5-flash`
- **Notes**: High rate limits, excellent tool-use performance, multi-modal context.

### 2. Groq (Ultra-Fast Llama 3.3 — Free Tier Available)
- **URL**: https://console.groq.com/keys
- **Prefix**: `gsk_...`
- **Default Model**: `llama-3.3-70b`
- **Notes**: Sub-second token response times.

### 3. OpenAI (GPT-4o, GPT-4.1-mini)
- **URL**: https://platform.openai.com/api-keys
- **Prefix**: `sk-...`
- **Default Model**: `gpt-4.1-mini`

### 4. Anthropic (Claude 3.5 Sonnet / Claude Sonnet 4)
- **URL**: https://console.anthropic.com/settings/keys
- **Prefix**: `sk-ant-...`
- **Default Model**: `claude-sonnet-4`

### 5. OpenRouter (Unified API for 200+ Models)
- **URL**: https://openrouter.ai/keys
- **Prefix**: `sk-or-...`
- **Default Model**: `anthropic/claude-3.5-sonnet`

### 6. Ollama (Local & 100% Offline — No API Key Required)
- **URL**: https://ollama.com
- **Setup**:
  ```bash
  ollama run llama3.2
  ```
- **In ARYx**:
  ```text
  /model use ollama
  ```

## Switching Providers at Runtime

Inside your active ARYx terminal session:
```text
/model                  # Shows current active provider & model
/model use openai       # Switch to OpenAI
/model use gemini       # Switch to Gemini
/model use ollama       # Switch to local Ollama
/model add              # Add or update an API key with auto-detection
```
