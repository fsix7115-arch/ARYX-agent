"""
ARYx AGENT - Configuration Management
Handles provider key detection, ~/.aryx/config.toml load/save, and secure permissions.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
            # Section 17: user-defined providers ([[providers.custom]] in TOML).
            # Each entry: name, base_url, api_key, model, format, headers,
            # query_params, context_window, supports_tools, supports_streaming.
            "custom": [],
        },
        # Section 17.4: smart routing (opt-in). When smart_routing is true,
        # the router picks a provider per task type and falls back down the
        # chain when the active provider fails.
        "routing": {
            "smart_routing": False,
            "fallback_chain": [],
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


def _format_toml_value(v: Any) -> str:
    """Format one value as TOML (scalar, inline table, or array)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        inner = ", ".join(f'"{k}" = {_format_toml_value(val)}' for k, val in v.items())
        return "{ " + inner + " }"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_format_toml_value(item) for item in v) + "]"
    escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _dump_toml_simple(data: Dict[str, Any]) -> str:
    """Simple TOML serializer for ARYx config without third-party dependencies.

    Supports plain tables, nested tables, arrays, inline tables, and
    arrays of tables ([[section.sub]] — used by providers.custom).
    """
    lines = ["# ARYx AGENT configuration (~/.aryx/config.toml)", ""]

    def dump_table(header: str, table: Dict[str, Any]) -> None:
        scalars: Dict[str, Any] = {}
        nested: Dict[str, Any] = {}
        for k, v in table.items():
            if isinstance(v, dict) or (isinstance(v, list) and v and isinstance(v[0], dict)):
                nested[k] = v
            else:
                scalars[k] = v
        if scalars or not nested:
            lines.append(f"[{header}]")
            for k, v in scalars.items():
                lines.append(f"{k} = {_format_toml_value(v)}")
            lines.append("")
        for sub, sub_data in nested.items():
            if isinstance(sub_data, list):
                for entry in sub_data:
                    lines.append(f"[[{header}.{sub}]]")
                    for k, v in entry.items():
                        lines.append(f"{k} = {_format_toml_value(v)}")
                    lines.append("")
            else:
                dump_table(f"{header}.{sub}", sub_data)

    # Top-level scalar/list values MUST come before any [table] header:
    # the simple parser assigns bare key = value lines to the most recent
    # section, so emitting them after a header would nest them wrongly
    # (this bit the schedules file: "schedules = [...]" after [settings]).
    for section, sec_data in data.items():
        if not isinstance(sec_data, dict):
            lines.append(f"{section} = {_format_toml_value(sec_data)}")
    if any(not isinstance(v, dict) for v in data.values()):
        lines.append("")
    for section, sec_data in data.items():
        if isinstance(sec_data, dict):
            dump_table(section, sec_data)
    return "\n".join(lines).strip() + "\n"


def _split_toml_array(inner: str) -> List[str]:
    """Split the inside of a TOML array on top-level commas (quotes aware)."""
    parts: List[str] = []
    depth = 0
    in_str: Optional[str] = None
    cur: List[str] = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if in_str:
            cur.append(ch)
            if ch == in_str and (i == 0 or inner[i - 1] != "\\"):
                in_str = None
        elif ch in ('"', "'"):
            in_str = ch
            cur.append(ch)
        elif ch in "[{":
            depth += 1
            cur.append(ch)
        elif ch in "]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    if cur or parts:
        parts.append("".join(cur).strip())
    return [p for p in parts if p != ""]


def _parse_toml_value(val: str) -> Any:
    """Parse one TOML value: string, bool, number, array, or inline table."""
    val = val.strip()
    if val.startswith('"') and val.endswith('"') and len(val) >= 2:
        return val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if val.startswith("'") and val.endswith("'") and len(val) >= 2:
        return val[1:-1]
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.startswith("[") and val.endswith("]"):
        return [_parse_toml_value(p) for p in _split_toml_array(val[1:-1])]
    if val.startswith("{") and val.endswith("}"):
        out: Dict[str, Any] = {}
        for part in _split_toml_array(val[1:-1]):
            if "=" in part:
                k, v = [p.strip() for p in part.split("=", 1)]
                out[k.strip('"').strip("'")] = _parse_toml_value(v)
        return out
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def _parse_toml_simple(content: str) -> Dict[str, Any]:
    """Fallback simple parser if tomllib is unavailable.

    Supports [table], [[array.of.tables]], dotted keys, strings, bools,
    numbers, arrays, and inline tables — enough for providers.custom,
    [routing], and schedules written by ARYx itself.
    """
    result: Dict[str, Any] = {}
    current: Any = result  # dict currently receiving key = value lines

    def navigate(parts: List[str], array_table: bool) -> Any:
        node: Any = result
        for part in parts[:-1]:
            nxt = node.get(part)
            if isinstance(nxt, list):
                nxt = nxt[-1] if nxt else None
            if not isinstance(nxt, dict):
                nxt = {}
                node[part] = nxt
            node = nxt
        last = parts[-1]
        if array_table:
            node.setdefault(last, [])
            entry: Dict[str, Any] = {}
            node[last].append(entry)
            return entry
        return node.setdefault(last, {})

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[[") and line.endswith("]]"):
            header = line[2:-2].strip()
            current = navigate(header.split("."), array_table=True)
            continue
        if line.startswith("[") and line.endswith("]"):
            header = line[1:-1].strip()
            parts = header.split(".")
            if len(parts) == 1:
                current = result.setdefault(parts[0], {})
            else:
                current = navigate(parts, array_table=False)
            continue
        if "=" in line:
            key, val = [p.strip() for p in line.split("=", 1)]
            if isinstance(current, dict):
                current[key] = _parse_toml_value(val)
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
    """Returns (active_provider_name, provider_settings_dict).

    Section 17: if the active name matches a [[providers.custom]] entry,
    that entry is returned with its api_key already resolved (env var,
    secrets file, or inline value) so existing "is a key configured?"
    checks keep working for custom providers.
    """
    cfg = config or load_config()
    active = cfg.get("provider", {}).get("active", "gemini")
    for entry in get_custom_providers(cfg):
        if str(entry.get("name", "")).lower() == str(active).lower():
            resolved = dict(entry)
            resolved["api_key"] = resolve_custom_key(entry)
            return active, resolved
    provider_settings = cfg.get("providers", {}).get(active, {})
    return active, provider_settings


# ---------------------------------------------------------------------------
# Section 17.3 — custom provider key resolution (env vars & secret files)
# Priority: ${VAR} expansion in the configured value, then
# ARYX_KEY_<PROVIDER>, then ~/.aryx/secrets/<provider>.key (chmod 600),
# then the provider-native env var (known names only), then inline value.
# ---------------------------------------------------------------------------

_NATIVE_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "together": "TOGETHER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def get_custom_providers(config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """All [[providers.custom]] entries from config (dicts only)."""
    cfg = config or load_config()
    raw = cfg.get("providers", {}).get("custom", [])
    if isinstance(raw, dict):
        return [raw]
    return [e for e in (raw or []) if isinstance(e, dict)]


def _sanitize_env_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", str(name).upper())


def resolve_custom_key(entry: Dict[str, Any]) -> str:
    """Resolve a custom provider's API key from env/file/inline sources."""
    name = str(entry.get("name", ""))
    raw = str(entry.get("api_key", "") or "")

    # 1. ${VAR} expansion inside the configured value (commit-safe configs).
    if "${" in raw:
        expanded = re.sub(
            r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
            lambda m: os.environ.get(m.group(1), ""),
            raw,
        )
        if expanded and "${" not in expanded:
            return expanded.strip()

    # 2. ARYX_KEY_<PROVIDER_NAME_UPPER>
    env_key = os.environ.get(f"ARYX_KEY_{_sanitize_env_name(name)}", "")
    if env_key:
        return env_key.strip()

    # 3. ~/.aryx/secrets/<provider>.key (must be chmod 600; warn if not)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    secret_file = ARYX_DIR / "secrets" / f"{safe_name}.key"
    try:
        if secret_file.exists():
            value = secret_file.read_text(encoding="utf-8").strip()
            if value:
                return value
    except OSError:
        pass

    # 4. Provider-native env var (only for well-known provider names).
    native = _NATIVE_ENV_VARS.get(name.lower())
    if native and os.environ.get(native):
        return str(os.environ[native]).strip()

    # 5. Inline value from config.toml (lowest priority, easiest to use).
    return raw.strip()


def save_custom_key_file(provider_name: str, api_key: str) -> str:
    """Store a key in ~/.aryx/secrets/<provider>.key with chmod 600.

    Returns the file path. Used by `aryx provider add` when the user
    chooses file-based key storage instead of inline config.
    """
    secrets_dir = ARYX_DIR / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", provider_name)
    path = secrets_dir / f"{safe_name}.key"
    path.write_text(api_key.strip() + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return str(path)
