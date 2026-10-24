"""
ARYx AGENT - Anthropic Claude Provider
Direct HTTP client for Anthropic Claude Messages API.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional, Tuple

from aryx.config import redact_secrets
from aryx.http_client import HttpClient
from aryx.providers.base import LLMProvider

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude Provider supporting tools & system prompts."""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4", **kwargs: Any) -> None:
        super().__init__(api_key=api_key, model=model or "claude-sonnet-4", **kwargs)

    def validate_key(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "Anthropic API key is empty. Get one at https://console.anthropic.com"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 5,
            "messages": [{"role": "user", "content": "hi"}],
        }

        try:
            with HttpClient(timeout=10.0) as client:
                res = client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
                if res.status_code == 200:
                    return True, "Anthropic connected successfully."
                elif res.status_code in (401, 403):
                    return (
                        False,
                        "Anthropic rejected this key. Check for missing characters or check console.anthropic.com",
                    )
                else:
                    return False, f"Anthropic error ({res.status_code}): {res.text[:120]}"
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                return False, "Connection timed out reaching Anthropic API. Check internet/VPN."
            return False, f"Could not reach Anthropic: {redact_secrets(str(e))}"

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        system_prompt = ""
        claude_messages = []

        for m in messages:
            role = m["role"]
            content = m.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "tool":
                claude_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.get("tool_call_id", "call_0"),
                            "content": content,
                        }
                    ],
                })
            elif role == "assistant" and m.get("tool_calls"):
                content_blocks: List[Dict[str, Any]] = []
                if content:
                    content_blocks.append({"type": "text", "text": content})
                for tc in m["tool_calls"]:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", "call_0"),
                        "name": tc["name"],
                        "input": tc.get("args", {}),
                    })
                claude_messages.append({"role": "assistant", "content": content_blocks})
            else:
                claude_messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": claude_messages,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
                }
                for t in tools
            ]

        try:
            with HttpClient(timeout=60.0) as client:
                res = client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
                if res.status_code != 200:
                    raise RuntimeError(f"Anthropic error ({res.status_code}): {res.text[:200]}")

                data = res.json()
                text_parts = []
                tool_calls = []

                for block in data.get("content", []):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block.get("id"),
                            "name": block.get("name"),
                            "args": block.get("input", {}),
                        })

                usage_data = data.get("usage", {})
                usage = {
                    "prompt_tokens": usage_data.get("input_tokens", 0),
                    "completion_tokens": usage_data.get("output_tokens", 0),
                    "total_tokens": usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
                }

                return {
                    "content": "".join(text_parts).strip(),
                    "tool_calls": tool_calls,
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
        return [
            "claude-sonnet-4",
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ]
