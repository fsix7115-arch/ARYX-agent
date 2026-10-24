"""
ARYx AGENT - Doctor Command
Self-diagnostics and auto-repair running 15 functional probes in order
(9 core checks + 6 gateway checks from Section 16.11).
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aryx.http_client import HttpClient
from aryx.config import (
    ARYX_DIR,
    CONFIG_FILE,
    MEMORY_DB,
    SKILLS_DIR,
    ensure_aryx_directories,
    get_active_provider_config,
    load_config,
)
from aryx.providers import get_provider


class DoctorCheck:
    def __init__(
        self,
        name: str,
        status: str,  # "PASS", "WARN", "FAIL"
        details: str,
        fix: Optional[str] = None,
        auto_fix_fn: Optional[Any] = None,
    ) -> None:
        self.name = name
        self.status = status
        self.details = details
        self.fix = fix
        self.auto_fix_fn = auto_fix_fn

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "fix": self.fix,
        }


def check_python_version() -> DoctorCheck:
    major, minor = sys.version_info.major, sys.version_info.minor
    ver_str = f"{major}.{minor}.{sys.version_info.micro}"
    if major > 3 or (major == 3 and minor >= 10):
        return DoctorCheck("Python version >= 3.10", "PASS", f"Python {ver_str}")

    os_type = sys.platform
    fix_cmd = "brew install python@3.11" if os_type == "darwin" else "sudo apt install -y python3 python3-pip"
    return DoctorCheck(
        "Python version >= 3.10",
        "FAIL",
        f"Python {ver_str} is below required 3.10",
        fix=f"Install Python 3.10+: {fix_cmd}",
    )


def check_aryx_on_path() -> DoctorCheck:
    aryx_path = shutil.which("aryx")
    local_bin = str(Path.home() / ".local" / "bin")

    if aryx_path:
        return DoctorCheck("aryx on PATH", "PASS", f"Found at {aryx_path}")

    path_env = os.environ.get("PATH", "")
    fix_line = 'export PATH="$HOME/.local/bin:$PATH"'

    def auto_fix_path() -> bool:
        # Append to shell rc
        shell = os.environ.get("SHELL", "")
        rc = Path.home() / (".zshrc" if "zsh" in shell else ".bashrc")
        try:
            with open(rc, "a", encoding="utf-8") as f:
                f.write(f"\n# ARYx PATH\n{fix_line}\n")
            return True
        except Exception:
            return False

    return DoctorCheck(
        "aryx on PATH",
        "WARN",
        f"aryx binary not found in PATH (searched {local_bin})",
        fix=f"Add ~/.local/bin to PATH: {fix_line}",
        auto_fix_fn=auto_fix_path,
    )


def check_aryx_dir_permissions() -> DoctorCheck:
    def auto_fix_dir() -> bool:
        try:
            ensure_aryx_directories()
            return True
        except Exception:
            return False

    if not ARYX_DIR.exists():
        return DoctorCheck(
            "~/.aryx directory",
            "FAIL",
            "Directory does not exist",
            fix="Run: mkdir -p ~/.aryx && chmod 700 ~/.aryx",
            auto_fix_fn=auto_fix_dir,
        )

    # Test write permissions
    test_file = ARYX_DIR / ".doctor_test"
    try:
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        return DoctorCheck("~/.aryx directory & permissions", "PASS", "Writable (chmod 700)")
    except Exception as e:
        return DoctorCheck(
            "~/.aryx directory & permissions",
            "FAIL",
            f"Directory is not writable: {str(e)}",
            fix="Fix permissions: chmod -R 700 ~/.aryx",
            auto_fix_fn=auto_fix_dir,
        )


def check_config_exists() -> DoctorCheck:
    if not CONFIG_FILE.exists():
        return DoctorCheck(
            "config.toml exists",
            "FAIL",
            "Config file ~/.aryx/config.toml not found",
            fix="Run `aryx` to start 30-second setup, or `aryx config`",
        )

    config = load_config()
    active, p_cfg = get_active_provider_config(config)

    if active != "ollama" and not p_cfg.get("api_key"):
        return DoctorCheck(
            "config.toml active key",
            "FAIL",
            f"No API key configured for active provider '{active}'",
            fix="Run `aryx` to paste your key, or `aryx config` to edit",
        )

    return DoctorCheck("config.toml configuration", "PASS", f"Active provider: {active}")


def check_api_key_validity() -> DoctorCheck:
    config = load_config()
    active, p_cfg = get_active_provider_config(config)

    if not CONFIG_FILE.exists() or (active != "ollama" and not p_cfg.get("api_key")):
        return DoctorCheck(
            "API key validity probe",
            "FAIL",
            "No API key to test",
            fix="Run `aryx` to configure an API key",
        )

    try:
        provider = get_provider(active, config)
        valid, msg = provider.validate_key()
        if valid:
            return DoctorCheck("API key functional probe", "PASS", f"{active}: {msg}")
        else:
            return DoctorCheck(
                "API key functional probe",
                "FAIL",
                f"{active} key failed: {msg}",
                fix="Get a new key or verify no extra spaces, then run: aryx config",
            )
    except Exception as e:
        return DoctorCheck(
            "API key functional probe",
            "FAIL",
            f"Validation probe exception: {str(e)}",
            fix="Run `aryx help setup` or `aryx doctor --fix`",
        )


def check_network_connectivity() -> DoctorCheck:
    # Try reaching DNS / reliable endpoints
    test_urls = [
        "https://generativelanguage.googleapis.com",
        "https://api.openai.com",
        "https://1.1.1.1",
    ]
    reachable = False
    with HttpClient(timeout=4.0) as client:
        for u in test_urls:
            try:
                res = client.get(u)
                if res.status_code < 500:
                    reachable = True
                    break
            except Exception:
                continue

    if reachable:
        return DoctorCheck("Network connectivity", "PASS", "Provider endpoints reachable")
    else:
        return DoctorCheck(
            "Network connectivity",
            "FAIL",
            "Cannot connect to external AI endpoints",
            fix="Check your internet connection, proxy, or VPN. Or switch to Ollama offline.",
        )


def check_sqlite_memory() -> DoctorCheck:
    def auto_fix_db() -> bool:
        try:
            if MEMORY_DB.exists():
                shutil.move(str(MEMORY_DB), str(MEMORY_DB) + ".bak")
            return True
        except Exception:
            return False

    try:
        ensure_aryx_directories()
        conn = sqlite3.connect(str(MEMORY_DB))
        conn.execute("SELECT 1;")
        conn.close()
        return DoctorCheck("SQLite memory database", "PASS", f"OK at {MEMORY_DB}")
    except Exception as e:
        return DoctorCheck(
            "SQLite memory database",
            "FAIL",
            f"Database corrupted or locked: {str(e)}",
            fix="Backup and recreate: mv ~/.aryx/memory.db ~/.aryx/memory.db.bak",
            auto_fix_fn=auto_fix_db,
        )


def check_skills_dir() -> DoctorCheck:
    if not SKILLS_DIR.exists():
        ensure_aryx_directories()

    try:
        count = len(list(SKILLS_DIR.glob("*.md")))
        return DoctorCheck("Skills directory", "PASS", f"Readable ({count} skills installed)")
    except Exception as e:
        return DoctorCheck(
            "Skills directory",
            "WARN",
            f"Skills directory error: {str(e)}",
            fix="Run `mkdir -p ~/.aryx/skills && chmod 700 ~/.aryx/skills`",
        )


def check_disk_space() -> DoctorCheck:
    try:
        stat = shutil.disk_usage(Path.home())
        free_mb = stat.free / (1024 * 1024)
        if free_mb >= 50:
            return DoctorCheck("Disk space > 50 MB", "PASS", f"{free_mb:.1f} MB free")
        else:
            return DoctorCheck(
                "Disk space > 50 MB",
                "WARN",
                f"Only {free_mb:.1f} MB free",
                fix="Free up space in home directory for memory and snapshots.",
            )
    except Exception as e:
        return DoctorCheck("Disk space", "WARN", f"Could not determine disk usage: {str(e)}")


def check_gateway_config() -> DoctorCheck:
    """CHECK 10: gateway.toml parses (Section 16.11)."""
    try:
        from aryx.gateway.config import GATEWAY_FILE, validate_gateway_config

        err = validate_gateway_config()
        if err:
            return DoctorCheck("gateway.toml syntax", "FAIL", f"Parse error: {err}",
                               fix="Print the line number of the error, fix it, then re-run doctor.")
        if not GATEWAY_FILE.exists():
            return DoctorCheck("gateway.toml syntax", "PASS", "No gateway.toml yet (all channels disabled)")
        return DoctorCheck("gateway.toml syntax", "PASS", "Valid TOML")
    except Exception as e:
        return DoctorCheck("gateway.toml syntax", "FAIL", f"Could not read gateway config: {e}")


def check_gateway_credentials() -> DoctorCheck:
    """CHECK 11: every ENABLED channel has its credentials present."""
    try:
        from aryx.gateway.config import CHANNELS, channel_config, enabled_channels, load_gateway_config

        config = load_gateway_config()
        enabled = enabled_channels(config)
        if not enabled:
            return DoctorCheck("gateway channel credentials", "PASS", "No channels enabled (nothing to validate)")
        missing = []
        for channel in enabled:
            cfg = channel_config(config, channel)
            if channel == "telegram" and not cfg.get("bot_token"):
                missing.append("telegram bot_token")
            elif channel == "webui" and not cfg.get("auth_token"):
                missing.append("webui auth_token")
            elif channel == "whatsapp":
                needed = (["account_sid", "auth_token", "from_number"] if cfg.get("provider") == "twilio"
                          else ["access_token", "phone_number_id"])
                missing += [f"whatsapp {k}" for k in needed if not cfg.get(k)]
            elif channel == "discord" and not cfg.get("bot_token"):
                missing.append("discord bot_token")
            elif channel == "slack" and not (cfg.get("bot_token") and cfg.get("app_token")):
                missing.append("slack bot_token/app_token")
        if missing:
            return DoctorCheck("gateway channel credentials", "FAIL", f"Missing: {', '.join(missing)}",
                               fix="Re-run: aryx gateway add <channel>")
        return DoctorCheck("gateway channel credentials", "PASS", f"Credentials present for: {', '.join(enabled)}")
    except Exception as e:
        return DoctorCheck("gateway channel credentials", "FAIL", f"Could not check: {e}")


def check_gateway_webhooks() -> DoctorCheck:
    """CHECK 12: webhook-based channels are reachable (if any)."""
    try:
        from aryx.gateway.config import channel_config, load_gateway_config

        config = load_gateway_config()
        # Only WhatsApp runs webhook-mode in this build; Telegram uses
        # long-polling, Discord uses its gateway, Slack uses Socket Mode,
        # and Web UI is local — none of those need a public URL.
        wa = channel_config(config, "whatsapp")
        url = wa.get("webhook_url", "") if wa.get("enabled") else ""
        if not url:
            return DoctorCheck("gateway webhooks", "PASS", "No webhook-based channels (long-polling/socket mode need no public URL)")
        try:
            client = HttpClient(timeout=5)
            resp = client.get(url)
            if resp.status_code < 500:
                return DoctorCheck("gateway webhooks", "PASS", f"Webhook reachable: {url}")
            return DoctorCheck("gateway webhooks", "FAIL", f"Webhook returned HTTP {resp.status_code}",
                               fix="Your tunnel is down. Run: aryx gateway start")
        except Exception:
            return DoctorCheck("gateway webhooks", "FAIL", f"Webhook unreachable: {url}",
                               fix="Your tunnel is down. Run: aryx gateway start")
    except Exception as e:
        return DoctorCheck("gateway webhooks", "FAIL", f"Could not check: {e}")


def check_gateway_allowlist() -> DoctorCheck:
    """CHECK 13: allowlist non-empty for each enabled channel (WARN)."""
    try:
        from aryx.gateway.config import channel_config, enabled_channels, load_gateway_config

        config = load_gateway_config()
        empty = []
        for channel in enabled_channels(config):
            cfg = channel_config(config, channel)
            if channel == "telegram" and not (cfg.get("allowed_user_ids") or cfg.get("allowed_usernames")):
                empty.append("telegram")
            elif channel == "whatsapp" and not cfg.get("allowed_numbers"):
                empty.append("whatsapp")
            elif channel == "discord" and not cfg.get("allowed_guilds"):
                empty.append("discord")
            elif channel == "slack" and not (cfg.get("allowed_workspaces") or cfg.get("allowed_users")):
                empty.append("slack")
            elif channel == "webui" and not cfg.get("auth_token"):
                empty.append("webui (no auth token)")
        if empty:
            return DoctorCheck("gateway allowlists", "WARN", f"Empty allowlist for: {', '.join(empty)}",
                               fix="Anyone can control your bot! Add user IDs to gateway.toml, then run: aryx gateway reload")
        return DoctorCheck("gateway allowlists", "PASS", "All enabled channels have allowlists")
    except Exception as e:
        return DoctorCheck("gateway allowlists", "FAIL", f"Could not check: {e}")


def check_gateway_log_leaks() -> DoctorCheck:
    """CHECK 14: no API keys visible in gateway.log (leak scan)."""
    import re

    try:
        from aryx.gateway.config import GATEWAY_LOG

        if not GATEWAY_LOG.exists():
            return DoctorCheck("gateway log leak scan", "PASS", "No gateway.log yet")
        text = GATEWAY_LOG.read_text(encoding="utf-8", errors="ignore")
        patterns = [r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b", r"sk-ant-[A-Za-z0-9_-]{10,}",
                    r"AIza[A-Za-z0-9_-]{10,}", r"gsk_[A-Za-z0-9]{10,}", r"sk-[A-Za-z0-9]{10,}"]
        for pattern in patterns:
            if re.search(pattern, text):
                return DoctorCheck("gateway log leak scan", "FAIL", "Possible secret found in gateway.log",
                                   fix="Rotate your key immediately. Purge logs.")
        return DoctorCheck("gateway log leak scan", "PASS", "No secrets found in gateway.log")
    except Exception as e:
        return DoctorCheck("gateway log leak scan", "FAIL", f"Could not scan: {e}")


def check_gateway_running() -> DoctorCheck:
    """CHECK 15: at least one channel running (WARN if none)."""
    import json as _json

    try:
        from aryx.gateway.config import GATEWAY_STATE_FILE

        if GATEWAY_STATE_FILE.exists():
            state = _json.loads(GATEWAY_STATE_FILE.read_text(encoding="utf-8"))
            pid = state.get("pid")
            try:
                os.kill(int(pid), 0)
                channels = ", ".join(state.get("channels", []))
                return DoctorCheck("gateway running", "PASS", f"Gateway running (PID {pid}): {channels}")
            except (OSError, ValueError, TypeError):
                pass
        return DoctorCheck("gateway running", "WARN", "No gateway currently running",
                           fix="Run: aryx gateway start")
    except Exception as e:
        return DoctorCheck("gateway running", "WARN", f"Could not determine gateway state: {e}",
                           fix="Run: aryx gateway start")


def check_custom_providers() -> DoctorCheck:
    """CHECK 16: custom provider entries parse and resolve keys (WARN if broken)."""
    try:
        from aryx.config import get_custom_providers, resolve_custom_key

        entries = get_custom_providers(load_config())
        if not entries:
            return DoctorCheck("custom providers", "PASS", "No custom providers configured")
        broken = []
        for e in entries:
            name = str(e.get("name", ""))
            if not e.get("base_url"):
                broken.append(f"{name}: missing base_url")
            elif e.get("format", "openai") not in ("openai", "anthropic", "gemini", "raw"):
                broken.append(f"{name}: unknown format '{e.get('format')}'")
        if broken:
            return DoctorCheck("custom providers", "WARN", "; ".join(broken),
                               fix="Fix the entry in ~/.aryx/config.toml or run: aryx provider remove <name>")
        return DoctorCheck("custom providers", "PASS", f"{len(entries)} custom provider(s) configured")
    except Exception as e:
        return DoctorCheck("custom providers", "WARN", f"Could not check custom providers: {e}")


def check_web_deps() -> DoctorCheck:
    """CHECK 17: web extra installed for `aryx web` (WARN if missing — optional)."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401

        return DoctorCheck("web UI deps", "PASS", "fastapi + uvicorn installed (aryx web ready)")
    except ImportError:
        return DoctorCheck("web UI deps", "WARN", "fastapi/uvicorn not installed — `aryx web` will ask for them",
                           fix="Run: pip install \"aryx-agent[web]\"")


def check_scheduler() -> DoctorCheck:
    """CHECK 18: schedules file parses, all crons valid (WARN if broken)."""
    try:
        from aryx.scheduler.engine import load_schedules
        from aryx.scheduler.parser import validate_cron

        rows = load_schedules()
        bad = [str(s.get("id")) for s in rows if not validate_cron(str(s.get("cron", "")))]
        if bad:
            return DoctorCheck("scheduler", "WARN", f"Invalid cron in schedules: {', '.join(bad)}",
                               fix="Fix with: aryx schedule edit <id>")
        return DoctorCheck("scheduler", "PASS", f"{len(rows)} schedule(s), all crons valid")
    except Exception as e:
        return DoctorCheck("scheduler", "WARN", f"Could not check schedules: {e}")


def check_browser_profiles() -> DoctorCheck:
    """CHECK 19: browser profiles dir readable; Playwright optional (WARN if missing)."""
    try:
        from aryx.browser.manager import list_profiles

        rows = list_profiles()
        try:
            import playwright  # noqa: F401

            extra = "playwright installed"
        except ImportError:
            extra = "playwright not installed (browser tools need the browser extra)"
        return DoctorCheck("browser profiles", "PASS" if rows else "WARN",
                           f"{len(rows)} profile(s); {extra}",
                           fix="Run: pip install \"aryx-agent[browser]\"" if "not installed" in extra else None)
    except Exception as e:
        return DoctorCheck("browser profiles", "WARN", f"Could not check browser profiles: {e}")


def run_doctor(fix: bool = False, as_json: bool = False) -> int:
    """Run all 19 checks and optionally perform auto-repair."""
    checks = [
        check_python_version(),
        check_aryx_on_path(),
        check_aryx_dir_permissions(),
        check_config_exists(),
        check_api_key_validity(),
        check_network_connectivity(),
        check_sqlite_memory(),
        check_skills_dir(),
        check_disk_space(),
        check_gateway_config(),
        check_gateway_credentials(),
        check_gateway_webhooks(),
        check_gateway_allowlist(),
        check_gateway_log_leaks(),
        check_gateway_running(),
        check_custom_providers(),
        check_web_deps(),
        check_scheduler(),
        check_browser_profiles(),
    ]

    if fix:
        for c in checks:
            if c.status in ("FAIL", "WARN") and c.auto_fix_fn:
                try:
                    c.auto_fix_fn()
                except Exception:
                    pass
        # Re-run after auto-fix
        checks = [
            check_python_version(),
            check_aryx_on_path(),
            check_aryx_dir_permissions(),
            check_config_exists(),
            check_api_key_validity(),
            check_network_connectivity(),
            check_sqlite_memory(),
            check_skills_dir(),
            check_disk_space(),
            check_gateway_config(),
            check_gateway_credentials(),
            check_gateway_webhooks(),
            check_gateway_allowlist(),
            check_gateway_log_leaks(),
            check_gateway_running(),
            check_custom_providers(),
            check_web_deps(),
            check_scheduler(),
            check_browser_profiles(),
        ]

    passed = sum(1 for c in checks if c.status == "PASS")
    warnings = sum(1 for c in checks if c.status == "WARN")
    failed = sum(1 for c in checks if c.status == "FAIL")

    if as_json:
        data = {
            "summary": {"passed": passed, "warning": warnings, "failed": failed},
            "checks": [c.to_dict() for c in checks],
        }
        print(json.dumps(data, indent=2))
        return 1 if failed > 0 else 0

    print("")
    for c in checks:
        if c.status == "PASS":
            print(f"  [PASS] {c.name} — {c.details}")
        elif c.status == "WARN":
            print(f"  \033[1;33m[WARN]\033[0m {c.name} — {c.details}")
            if c.fix:
                print(f"         \033[2mFix: {c.fix}\033[0m")
        else:
            print(f"  \033[1;31m[FAIL]\033[0m {c.name} — {c.details}")
            if c.fix:
                print(f"         Fix: {c.fix}")

    print("  ──────────────────────────────────────────────────")
    print(f"  {passed} passed · {warnings} warning{'s' if warnings != 1 else ''} · {failed} failed")
    print("")

    if failed > 0:
        print("  Run `aryx doctor --fix` to auto-repair common problems.")
        return 1
    return 0
