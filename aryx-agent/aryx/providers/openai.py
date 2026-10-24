"""
ARYx AGENT - OpenAI-Compatible Provider
Universal adapter for OpenAI, Groq, OpenRouter, Mistral, Together, and DeepSeek.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional, Tuple

from aryx.config import redact_secrets
from aryx.http_client import HttpClient
from aryx.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Universal OpenAI-compatible chat completion provider."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4.1-mini",
        base_url: str = "https://api.openai.com/v1",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, model=model or "gpt-4.1-mini", **kwargs)
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def validate_key(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "API key is empty."

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }

        try:
            with HttpClient(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    return True, "Provider connected successfully."
                elif res.status_code in (401, 403):
                    return (
                        False,
                        f"Authentication failed (status {res.status_code}). Check your API key for typos or extra whitespace.",
                    )
                else:
                    return False, f"Provider error ({res.status_code}): {res.text[:120]}"
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                return False, f"Connection timed out reaching {self.base_url}. Check your internet connection or VPN."
            return False, f"Could not reach endpoint: {redact_secrets(str(e))}"

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Format messages
        formatted_messages = []
        for m in messages:
            msg: Dict[str, Any] = {"role": m["role"], "content": m.get("content", "")}
            if m.get("tool_calls"):
                msg["tool_calls"] = [
                    {
                        "id": tc.get("id", f"call_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc.get("args", {})),
                        },
                    }
                    for i, tc in enumerate(m["tool_calls"])
                ]
            if m.get("tool_call_id"):
                msg["tool_call_id"] = m["tool_call_id"]
            if m.get("name"):
                msg["name"] = m["name"]
            formatted_messages.append(msg)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
        }

        if tools:
            formatted_tools = []
            for t in tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                    },
                })
            payload["tools"] = formatted_tools

        try:
            with HttpClient(timeout=60.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    err_txt = res.text[:200]
                    raise RuntimeError(f"OpenAI-compatible API error ({res.status_code}): {err_txt}")

                data = res.json()
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})

                content = message.get("content") or ""
                raw_tool_calls = message.get("tool_calls", [])
                parsed_calls = []

                for tc in raw_tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = {}
                    try:
                        fn_args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        pass
                    parsed_calls.append({
                        "name": fn_name,
                        "args": fn_args,
                        "id": tc.get("id"),
                    })

                usage_raw = data.get("usage", {})
                usage = {
                    "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                    "completion_tokens": usage_raw.get("completion_tokens", 0),
                    "total_tokens": usage_raw.get("total_tokens", 0),
                }

                return {
                    "content": content.strip(),
                    "tool_calls": parsed_calls,
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
        if "groq" in self.base_url:
            return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
        elif "openrouter" in self.base_url:
            return [
                "anthropic/claude-3.5-sonnet",
                "google/gemini-2.0-flash-exp",
                "meta-llama/llama-3.3-70b-instruct",
            ]
        return ["gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o3-mini"]
