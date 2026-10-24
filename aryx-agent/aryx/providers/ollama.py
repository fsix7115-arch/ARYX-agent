"""
ARYx AGENT - Ollama Local Provider
Runs local LLMs (llama3.2, mistral, deepseek-r1, qwen2.5) completely offline without API keys.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional, Tuple

from aryx.config import redact_secrets
from aryx.http_client import HttpClient
from aryx.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Local Ollama client for completely offline operations."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key="", model=model or "llama3.2", **kwargs)
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def validate_key(self) -> Tuple[bool, str]:
        # Ollama requires no key, but check if local server is alive
        url = f"{self.base_url}/api/tags"
        try:
            with HttpClient(timeout=4.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    if self.model in models or any(self.model in m for m in models):
                        return True, f"Ollama is running locally (model '{self.model}' ready)."
                    return (
                        True,
                        f"Ollama is running, but model '{self.model}' might need pulling: `ollama run {self.model}`.",
                    )
                return False, f"Ollama responded with status {res.status_code}."
        except Exception as e:
            if "refused" in str(e).lower() or "connect" in str(e).lower():
                return (
                    False,
                    "Could not connect to Ollama at http://localhost:11434.\n"
                    "Make sure Ollama is installed and running: run `ollama serve` or visit https://ollama.com",
                )
            return False, f"Ollama connection error: {redact_secrets(str(e))}"

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"

        formatted_messages = []
        for m in messages:
            msg: Dict[str, Any] = {"role": m["role"], "content": m.get("content", "")}
            if m.get("tool_calls"):
                msg["tool_calls"] = [
                    {
                        "function": {
                            "name": tc["name"],
                            "arguments": tc.get("args", {}),
                        }
                    }
                    for tc in m["tool_calls"]
                ]
            formatted_messages.append(msg)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                    },
                }
                for t in tools
            ]

        try:
            with HttpClient(timeout=120.0) as client:
                res = client.post(url, json=payload)
                if res.status_code != 200:
                    raise RuntimeError(f"Ollama error ({res.status_code}): {res.text[:200]}")

                data = res.json()
                msg = data.get("message", {})
                content = msg.get("content") or ""

                parsed_tools = []
                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", {})
                    parsed_tools.append({
                        "name": fn.get("name"),
                        "args": fn.get("arguments", {}),
                    })

                usage = {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                }

                return {
                    "content": content.strip(),
                    "tool_calls": parsed_tools,
                    "usage": usage,
                }
        except Exception as e:
            raise RuntimeError(redact_secrets(str(e)))

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> Generator[str, None, None]:
        res = self.chat(messages, tools=tools, temperature=temperature)
        if res.get("content"):
            yield res["content"]

    def list_models(self) -> List[str]:
        try:
            with HttpClient(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    return [m.get("name") for m in res.json().get("models", [])]
        except Exception:
            pass
        return ["llama3.2", "qwen2.5:coder", "mistral", "deepseek-r1:8b"]
