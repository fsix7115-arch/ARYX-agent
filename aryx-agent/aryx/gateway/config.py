"""
ARYx AGENT - Gateway configuration (Section 16.3).

Lives in ~/.aryx/gateway.toml, separate from the main config so a
user can share/rotate channel credentials without touching provider
keys. Tokens are NEVER printed: every display path redacts them.

TOML parsing reuses the stdlib tomllib (3.11+) with the tomli
fallback, exactly like aryx.config. Writing uses a small serializer
for the value types this file actually holds (str, int, bool,
lists of str/int) so no new dependency is needed.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+ built-in
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

from aryx.config import ARYX_DIR, LOGS_DIR

GATEWAY_FILE = ARYX_DIR / "gateway.toml"
GATEWAY_DB = ARYX_DIR / "gateway.db"
GATEWAY_LOG = LOGS_DIR / "gateway.log"
GATEWAY_STATE_FILE = ARYX_DIR / "gateway.state.json"

DEFAULTS: Dict[str, Dict[str, Any]] = {
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "allowed_user_ids": [],
        "allowed_usernames": [],
        "default_approval_mode": "safe",
        "allow_yolo_users": [],
    },
    "whatsapp": {
        "enabled": False,
        "provider": "twilio",  # or "meta"
        "allowed_numbers": [],
    },
    "discord": {
        "enabled": False,
        "allowed_guilds": [],
        "allowed_roles": [],
    },
    "slack": {
        "enabled": False,
        "allowed_workspaces": [],
        "allowed_users": [],
    },
    "webui": {
        "enabled": False,
        "host": "127.0.0.1",  # NEVER 0.0.0.0 by default
        "port": 8765,
        "auth_token": "",
    },
    "rate_limits": {
        "messages_per_minute": 20,
        "messages_per_day": 500,
    },
}

CHANNELS = ["telegram", "whatsapp", "discord", "slack", "webui"]


def _merge_defaults(raw: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for section, defaults in DEFAULTS.items():
        section_raw = raw.get(section, {}) if isinstance(raw.get(section), dict) else {}
        merged[section] = {**defaults, **section_raw}
    # Preserve any unknown top-level keys untouched.
    for key, value in raw.items():
        if key not in merged:
            merged[key] = value
    return merged


def load_gateway_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load gateway.toml (merged over defaults). Missing file = defaults."""
    target = Path(path) if path else GATEWAY_FILE
    if not target.exists() or tomllib is None:
        return _merge_defaults({})
    try:
        with open(target, "rb") as f:
            raw = tomllib.load(f)
    except Exception:
        # A broken file must surface loudly to the caller, not silently
        # fall back to defaults (which would disable every channel and
        # hide the real problem). Callers that need the raw error use
        # validate_gateway_config() instead.
        raise
    if not isinstance(raw, dict):
        return _merge_defaults({})
    return _merge_defaults(raw)


def validate_gateway_config(path: Optional[Path] = None) -> Optional[str]:
    """Return None when gateway.toml parses, else a human error string."""
    target = Path(path) if path else GATEWAY_FILE
    if not target.exists():
        return None  # Missing file is fine: all channels disabled.
    if tomllib is None:
        return "No TOML parser available (need Python 3.11+ or tomli)."
    try:
        with open(target, "rb") as f:
            tomllib.load(f)
    except Exception as e:  # noqa: BLE001 - surfaced to the user/doctor
        return str(e)
    return None


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    raise TypeError(f"Cannot serialise {type(value).__name__} to gateway.toml")


def save_gateway_config(config: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Write gateway.toml with 0600 permissions (it holds bot tokens)."""
    target = Path(path) if path else GATEWAY_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "# ARYx gateway configuration. Tokens live here — keep this file private.",
        "# See gateway.example.toml for a commented example.",
        "",
    ]
    for section in CHANNELS + ["rate_limits"]:
        if section not in config:
            continue
        lines.append(f"[{section}]")
        for key, value in config[section].items():
            try:
                lines.append(f"{key} = {_toml_value(value)}")
            except TypeError:
                continue  # Never write a value we cannot round-trip.
        lines.append("")
    # Unknown top-level sections are preserved verbatim by the caller;
    # this writer only manages the known sections.
    with open(target, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass


def channel_config(config: Dict[str, Any], channel: str) -> Dict[str, Any]:
    return config.get(channel, DEFAULTS.get(channel, {}))


def is_channel_enabled(config: Dict[str, Any], channel: str) -> bool:
    return bool(channel_config(config, channel).get("enabled", False))


def enabled_channels(config: Dict[str, Any]) -> List[str]:
    return [c for c in CHANNELS if is_channel_enabled(config, c)]


def redact_gateway_text(text: str, config: Optional[Dict[str, Any]] = None) -> str:
    """Scrub bot tokens / auth tokens out of any string before logging."""
    if not text:
        return text
    redacted = text
    tokens: List[str] = []
    if config:
        for section in CHANNELS:
            for key in ("bot_token", "auth_token"):
                value = channel_config(config, section).get(key, "")
                if value:
                    tokens.append(str(value))
    for token in tokens:
        if len(token) >= 8:
            redacted = redacted.replace(token, "***REDACTED***")
    # Telegram bot tokens look like 123456:ABC-DEF...; scrub that shape
    # even when the config that holds it is not at hand.
    redacted = re.sub(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b", "***REDACTED***", redacted)
    return redacted
