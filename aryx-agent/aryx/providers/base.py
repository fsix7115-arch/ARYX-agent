"""
ARYx AGENT - Base LLM Provider
Common interface for all LLM providers (Gemini, OpenAI, Anthropic, Ollama, Groq, OpenRouter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional, Tuple


class LLMProvider(ABC):
    """Abstract base class for all LLM providers in ARYx."""

    def __init__(self, api_key: str = "", model: str = "", **kwargs: Any) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.extra_config = kwargs

    @abstractmethod
    def validate_key(self) -> Tuple[bool, str]:
        """
        Validate the API key with a minimal 5-token call.
        Returns (True, "Success message") or (False, "Human readable error").
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Execute a chat turn.
        Returns dict:
        {
            "content": str,
            "tool_calls": List[{"name": str, "args": dict}],
            "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
        }
        """
        pass

    @abstractmethod
    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> Generator[str, None, None]:
        """Stream chunks of response text."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models for this provider."""
        pass
