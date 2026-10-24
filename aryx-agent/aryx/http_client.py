"""
ARYx AGENT - HTTP Client with Zero-Dependency Fallback
Uses httpx when installed, falls back to standard library urllib.request seamlessly.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


class SimpleResponse:
    def __init__(self, status_code: int, text: str, headers: Optional[Dict[str, str]] = None) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def json(self) -> Any:
        return json.loads(self.text)



def _make_httpx_client(timeout: float, follow_redirects: bool):
    """Build an httpx client that survives malformed proxy env vars.

    Some environments set NO_PROXY entries (e.g. bare "[::1]") that
    httpx cannot parse as URL patterns, so plain httpx.Client() raises
    InvalidURL at construction. That used to break every provider call
    — including local ones (Ollama/vLLM) that must never touch a proxy.
    Fall back to trust_env=False, which also guarantees localhost
    requests go direct.
    """
    try:
        return httpx.Client(timeout=timeout, follow_redirects=follow_redirects)
    except Exception:
        return httpx.Client(timeout=timeout, follow_redirects=follow_redirects, trust_env=False)


class HttpClient:
    """Synchronous HTTP client with timeout and automatic json serialization."""

    def __init__(self, timeout: float = 30.0, follow_redirects: bool = True) -> None:
        self.timeout = timeout
        self.follow_redirects = follow_redirects

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> SimpleResponse:
        if httpx:
            try:
                with _make_httpx_client(self.timeout, self.follow_redirects) as client:
                    r = client.get(url, headers=headers)
                    return SimpleResponse(r.status_code, r.text, dict(r.headers))
            except Exception as e:
                raise RuntimeError(str(e))

        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return SimpleResponse(resp.status, text, dict(resp.headers))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            return SimpleResponse(e.code, text, dict(e.headers))
        except Exception as e:
            raise RuntimeError(str(e))

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> SimpleResponse:
        hdrs = dict(headers or {})
        data_bytes = None

        if json is not None:
            hdrs.setdefault("Content-Type", "application/json")
            data_bytes = json_module.dumps(json).encode("utf-8") if "json_module" in globals() else __import__("json").dumps(json).encode("utf-8")

        if httpx:
            try:
                with _make_httpx_client(self.timeout, self.follow_redirects) as client:
                    r = client.post(url, json=json, headers=headers)
                    return SimpleResponse(r.status_code, r.text, dict(r.headers))
            except Exception as e:
                raise RuntimeError(str(e))

        req = urllib.request.Request(url, data=data_bytes, headers=hdrs, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return SimpleResponse(resp.status, text, dict(resp.headers))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            return SimpleResponse(e.code, text, dict(e.headers))
        except Exception as e:
            raise RuntimeError(str(e))
