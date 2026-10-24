"""
ARYx AGENT - Configuration Management
Handles provider key detection, ~/.aryx/config.toml load/save, and secure permissions.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import tomllib  # Python 3.11+ built-in
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # Handled with minimal parser/writer fallback

ARYX_DIR = Path.home() / ".aryx"
CONFIG_FILE = ARYX_DIR / "config.toml"
MEMORY_DB = ARYX_DIR / "memory.db"
SKILLS_DIR = ARYX_DIR / "skills"
SNAPSHOTS_DIR = ARYX_DIR / "snapshots"
LOGS_DIR = ARYX_DIR / "logs"

# Key Detection Rule Table
KEY_DETECTION_RULES = [
    {
        "prefix": "AIza",
        "provider": "gemini",
        "default_model": "gemini-2.5-flash",
        "name": "Google Gemini",
        "key_url": "https://aistudio.google.com/apikey",
    },
    {
        "prefix": "sk-ant-",
        "provider": "anthropic",
        "default_model": "claude-sonnet-4",
        "name": "Anthropic Claude",
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    {
        "prefix": "sk-or-",
        "provider": "openrouter",
        "default_model": "anthropic/claude-3.5-sonnet",
        "name": "OpenRouter",
        "key_url": "https://openrouter.ai/keys",
    },
    {
        "prefix": "gsk_",
        "provider": "groq",
        "default_model": "llama-3.3-70b",
        "name": "Groq",
        "key_url": "https://console.groq.com/keys",
    },
    {
        "prefix": "sk-",
        "provider": "openai",
        "default_model": "gpt-4.1-mini",
        "name": "OpenAI",
        "key_url": "https://platform.openai.com/api-keys",
    },
]

SUPPORTED_PROVIDERS = [
    {"id": "gemini", "name": "Google Gemini (Free tier available)", "default_model": "gemini-2.5-flash", "prefix": "AIza"},
    {"id": "openai", "name": "OpenAI (GPT-4o, GPT-4.1-mini)", "default_model": "gpt-4.1-mini", "prefix": "sk-"},
    {"id": "anthropic", "name": "Anthropic (Claude 3.5 Sonnet / Claude Sonnet 4)", "default_model": "claude-sonnet-4", "prefix": "sk-ant-"},
    {"id": "groq", "name": "Groq (Ultra-fast Llama 3.3)", "default_model": "llama-3.3-70b", "prefix": "gsk_"},
    {"id": "openrouter", "name": "OpenRouter (All models unified)", "default_model": "anthropic/claude-3.5-sonnet", "prefix": "sk-or-"},
    {"id": "ollama", "name": "Ollama (Local / Offline, No API key)", "default_model": "llama3.2", "prefix": ""},
]


def detect_provider_from_key(key: str) -> Optional[Dict[str, str]]:
    """
    Auto-detect provider and default model from key prefix.
    Returns dictionary with provider details or None if unrecognized.
    """
    cleaned_key = key.strip()
    if not cleaned_key:
        return None

    for rule in KEY_DETECTION_RULES:
        if cleaned_key.startswith(rule["prefix"]):
            return {
                "provider": rule["provider"],
                "default_model": rule["default_model"],
                "name": rule["name"],
                "key_url": rule["key_url"],
            }
    return None


def redact_key(key: str) -> str:
    """Safely redact API key for display or logging."""
    if not key or len(key) < 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def redact_secrets(text: str) -> str:
    """Sanitize strings to remove accidental key exposure."""
    # Redact AIza keys
    text = re.sub(r'AIza[0-9A-Za-z-_]{35}', 'AIza...[REDACTED]', text)
    # Redact sk- keys
    text = re.sub(r'sk-[a-zA-Z0-9_-]{20,}', 'sk-...[REDACTED]', text)
    # Redact gsk_ keys
    text = re.sub(r'gsk_[a-zA-Z0-9_-]{20,}', 'gsk_...[REDACTED]', text)
    return text


def ensure_aryx_directories() -> None:
    """Create ~/.aryx and subdirectories with secure permissions (chmod 700)."""
    for folder in (ARYX_DIR, SKILLS_DIR, SNAPSHOTS_DIR, LOGS_DIR):
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(folder, 0o700)
        except OSError:
            pass


def get_default_config() -> Dict[str, Any]:
    """Default configuration dictionary."""
    return {
        "general": {
            "approval_mode": "safe",
            "command_timeout": 30,
            "allow_network": False,
            "verbose": False,
        },
        "provider": {
            "active": "gemini",
        },
        "providers": {
            "gemini": {
                "api_key": "",
                "model": "gemini-2.5-flash",
                "temperature": 0.4,
            },
            "openai": {
                "api_key": "",
                "model": "gpt-4.1-mini",
                "base_url": "https://api.openai.com/v1",
                "temperature": 0.4,
            },
            "anthropic": {
                "api_key": "",
                "model": "claude-sonnet-4",
                "temperature": 0.4,
            },
            "groq": {
                "api_key": "",
                "model": "llama-3.3-70b",
                "base_url": "https://api.groq.com/openai/v1",
            },
            "openrouter": {
                "api_key": "",
                "model": "anthropic/claude-3.5-sonnet",
                "base_url": "https://openrouter.ai/api/v1",
            },
            "ollama": {
                "model": "llama3.2",
                "base_url": "http://localhost:11434",
            },
        },
        "memory": {
            "enabled": True,
            "sqlite_path": str(MEMORY_DB),
            "auto_skill_generation": True,
            "skill_tool_threshold": 5,
        },
        "snapshots": {
            "enabled": True,
            "snapshot_dir": str(SNAPSHOTS_DIR),
            "keep_last": 50,
        },
    }


def _dump_toml_simple(data: Dict[str, Any]) -> str:
    """Simple TOML serializer for ARYx config without third-party dependencies."""
    lines = ["# ARYx AGENT configuration (~/.aryx/config.toml)", ""]

    def format_val(v: Any) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        elif isinstance(v, (int, float)):
            return str(v)
        else:
            escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

    # Top level tables
    for section, sec_data in data.items():
        if isinstance(sec_data, dict):
            # Check if nested tables exist
            has_nested = any(isinstance(v, dict) for v in sec_data.values())
            if not has_nested:
                lines.append(f"[{section}]")
                for k, v in sec_data.items():
                    lines.append(f"{k} = {format_val(v)}")
                lines.append("")
            else:
                for sub, sub_data in sec_data.items():
                    if isinstance(sub_data, dict):
                        lines.append(f"[{section}.{sub}]")
                        for k, v in sub_data.items():
                            lines.append(f"{k} = {format_val(v)}")
                        lines.append("")
                    else:
                        lines.append(f"[{section}]")
                        lines.append(f"{sub} = {format_val(sub_data)}")
                        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _parse_toml_simple(content: str) -> Dict[str, Any]:
    """Fallback simple parser if tomllib is unavailable."""
    result: Dict[str, Any] = {}
    current_sec = ""
    current_sub = ""

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            header = line[1:-1].strip()
            parts = header.split(".")
            if len(parts) == 1:
                current_sec = parts[0]
                current_sub = ""
                result.setdefault(current_sec, {})
            elif len(parts) == 2:
                current_sec = parts[0]
                current_sub = parts[1]
                result.setdefault(current_sec, {}).setdefault(current_sub, {})
            continue

        if "=" in line:
            key, val = [p.strip() for p in line.split("=", 1)]
            # Parse value
            parsed_val: Any = val
            if val.startswith('"') and val.endswith('"'):
                parsed_val = val[1:-1].replace('\\"', '"').replace('\\\\', '\\')
            elif val.lower() == "true":
                parsed_val = True
            elif val.lower() == "false":
                parsed_val = False
            elif val.isdigit():
                parsed_val = int(val)

            if current_sec and current_sub:
                result[current_sec][current_sub][key] = parsed_val
            elif current_sec:
                result[current_sec][key] = parsed_val
            else:
                result[key] = parsed_val
    return result


def load_config() -> Dict[str, Any]:
    """Load configuration from ~/.aryx/config.toml. Returns default dict if not found."""
    if not CONFIG_FILE.exists():
        return get_default_config()

    try:
        content = CONFIG_FILE.read_text(encoding="utf-8")
        if tomllib:
            data = tomllib.loads(content)
        else:
            data = _parse_toml_simple(content)

        merged = get_default_config()
        # Deep merge
        for k, v in data.items():
            if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, dict) and sub_k in merged[k] and isinstance(merged[k][sub_k], dict):
                        merged[k][sub_k].update(sub_v)
                    else:
                        merged[k][sub_k] = sub_v
            else:
                merged[k] = v
        return merged
    except Exception:
        return get_default_config()


def save_config(config_data: Dict[str, Any]) -> None:
    """Save configuration to ~/.aryx/config.toml with chmod 600."""
    ensure_aryx_directories()
    raw_toml = _dump_toml_simple(config_data)
    CONFIG_FILE.write_text(raw_toml, encoding="utf-8")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def get_active_provider_config(config: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """Returns (active_provider_name, provider_settings_dict)."""
    cfg = config or load_config()
    active = cfg.get("provider", {}).get("active", "gemini")
    provider_settings = cfg.get("providers", {}).get(active, {})
    return active, provider_settings
