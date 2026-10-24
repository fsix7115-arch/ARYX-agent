"""
ARYx AGENT - Provider Registry & Factory
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from aryx.providers.anthropic import AnthropicProvider
from aryx.providers.base import LLMProvider
from aryx.providers.gemini import GeminiProvider
from aryx.providers.ollama import OllamaProvider
from aryx.providers.openai import OpenAIProvider


def get_provider(provider_name: str, config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to initialize the requested provider instance from config.
    """
    p_name = provider_name.lower().strip()
    p_cfg = config.get("providers", {}).get(p_name, {})
    api_key = p_cfg.get("api_key", "")
    model = p_cfg.get("model", "")
    base_url = p_cfg.get("base_url")

    if p_name == "gemini":
        return GeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")
    elif p_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model or "claude-sonnet-4")
    elif p_name == "ollama":
        return OllamaProvider(model=model or "llama3.2", base_url=base_url or "http://localhost:11434")
    elif p_name in ("openai", "groq", "openrouter", "mistral", "together"):
        # OpenAI compatible providers
        default_base_url = "https://api.openai.com/v1"
        if p_name == "groq":
            default_base_url = "https://api.groq.com/openai/v1"
        elif p_name == "openrouter":
            default_base_url = "https://openrouter.ai/api/v1"

        return OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url=base_url or default_base_url,
        )
    else:
        # Default fallback to OpenAI-compatible or Gemini
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url or "https://api.openai.com/v1")


__all__ = [
    "LLMProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "get_provider",
]
