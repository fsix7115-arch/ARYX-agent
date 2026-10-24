"""
ARYx AGENT - Google Gemini Provider
Direct high-performance HTTP client for Gemini API via Google AI Studio.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional, Tuple

from aryx.config import redact_secrets
from aryx.http_client import HttpClient
from aryx.providers.base import LLMProvider

BASE_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    """Google Gemini Provider with tool execution and streaming support."""

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash", **kwargs: Any) -> None:
        super().__init__(api_key=api_key, model=model or "gemini-2.5-flash", **kwargs)

    def validate_key(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "API key is empty. Get a free key at https://aistudio.google.com/apikey"

        url = f"{BASE_ENDPOINT}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": "hi"}]}],
            "generationConfig": {"maxOutputTokens": 3},
        }

        try:
            with HttpClient(timeout=10.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return True, "Gemini connected."
                elif res.status_code in (400, 401, 403):
                    return (
                        False,
                        "That key didn't work. Check for extra spaces or expired keys.\n"
                        "Get a free Gemini key at: https://aistudio.google.com/apikey",
                    )
                else:
                    return False, f"Gemini API returned status {res.status_code}: {res.text[:100]}"
        except Exception as e:
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                return False, "Connection timed out connecting to Google Gemini API. Check your internet connection."
            return False, f"Could not reach Gemini: {redact_secrets(str(e))}"

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        """Send chat messages and parse text or function tool calls."""
        url = f"{BASE_ENDPOINT}/{self.model}:generateContent?key={self.api_key}"

        # Convert messages to Gemini format
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "assistant":
                parts = []
                if content:
                    parts.append({"text": content})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        parts.append({
                            "functionCall": {
                                "name": tc["name"],
                                "args": tc.get("args", {}),
                            }
                        })
                if not parts:
                    parts.append({"text": ""})
                contents.append({"role": "model", "parts": parts})
            elif role == "tool":
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": msg.get("name", "tool"),
                            "response": {"result": content},
                        }
                    }],
                })
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if system_instruction:
            body["systemInstruction"] = system_instruction

        if tools:
            function_declarations = []
            for t in tools:
                function_declarations.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                })
            body["tools"] = [{"functionDeclarations": function_declarations}]

        try:
            with HttpClient(timeout=60.0) as client:
                res = client.post(url, json=body)
                if res.status_code != 200:
                    err_msg = res.json().get("error", {}).get("message", res.text[:200])
                    raise RuntimeError(f"Gemini API error ({res.status_code}): {err_msg}")

                data = res.json()
                candidate = data.get("candidates", [{}])[0]
                content_obj = candidate.get("content", {})
                parts = content_obj.get("parts", [])

                text_parts = []
                tool_calls = []

                for part in parts:
                    if "text" in part:
                        text_parts.append(part["text"])
                    elif "functionCall" in part:
                        fc = part["functionCall"]
                        tool_calls.append({
                            "name": fc.get("name"),
                            "args": fc.get("args", {}),
                        })

                usage_meta = data.get("usageMetadata", {})
                usage = {
                    "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                    "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                    "total_tokens": usage_meta.get("totalTokenCount", 0),
                }

                return {
                    "content": "\n".join(text_parts).strip(),
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
        # For simplicity and robust tool execution, fallback to chat or SSE
        res = self.chat(messages, tools=tools, temperature=temperature)
        if res.get("content"):
            yield res["content"]

    def list_models(self) -> List[str]:
        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
