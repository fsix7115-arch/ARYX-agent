"""
ARYx AGENT - Provider Tests
Tests key auto-detection prefix rules, secret redaction, and provider instantiation.
"""

from aryx.config import detect_provider_from_key, redact_key, redact_secrets
from aryx.providers import get_provider
from aryx.providers.gemini import GeminiProvider
from aryx.providers.openai import OpenAIProvider
from aryx.providers.anthropic import AnthropicProvider
from aryx.providers.ollama import OllamaProvider


def test_provider_key_detection():
    # Gemini AIza prefix
    gemini_match = detect_provider_from_key("AIzaSyB1234567890abcdef1234567890abcdef")
    assert gemini_match is not None
    assert gemini_match["provider"] == "gemini"
    assert gemini_match["default_model"] == "gemini-2.5-flash"

    # Anthropic sk-ant- prefix
    anthropic_match = detect_provider_from_key("sk-ant-api03-1234567890abcdef")
    assert anthropic_match is not None
    assert anthropic_match["provider"] == "anthropic"

    # OpenAI sk- prefix
    openai_match = detect_provider_from_key("sk-proj-1234567890abcdef")
    assert openai_match is not None
    assert openai_match["provider"] == "openai"

    # Groq gsk_ prefix
    groq_match = detect_provider_from_key("gsk_1234567890abcdef")
    assert groq_match is not None
    assert groq_match["provider"] == "groq"

    # OpenRouter sk-or- prefix
    or_match = detect_provider_from_key("sk-or-v1-1234567890abcdef")
    assert or_match is not None
    assert or_match["provider"] == "openrouter"


def test_secret_redaction():
    raw_key = "AIzaSyB_1234567890abcdef1234567890abcdef"
    redacted = redact_key(raw_key)
    assert redacted.startswith("AIza")
    assert redacted.endswith("cdef")
    assert "..." in redacted

    log_entry = f"Error communicating with Gemini using key {raw_key} at endpoint."
    sanitized = redact_secrets(log_entry)
    assert raw_key not in sanitized
    assert "[REDACTED]" in sanitized


def test_provider_instantiation():
    cfg = {
        "providers": {
            "gemini": {"api_key": "dummy", "model": "gemini-2.5-flash"},
            "ollama": {"model": "llama3.2", "base_url": "http://localhost:11434"},
        }
    }
    p_gemini = get_provider("gemini", cfg)
    assert isinstance(p_gemini, GeminiProvider)

    p_ollama = get_provider("ollama", cfg)
    assert isinstance(p_ollama, OllamaProvider)


if __name__ == "__main__":
    test_provider_key_detection()
    test_secret_redaction()
    test_provider_instantiation()
    print("✓ All provider tests passed successfully!")
