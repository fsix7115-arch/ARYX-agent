"""
ARYx AGENT - Doctor Command
Self-diagnostics and auto-repair running 9 functional probes in order.
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


def run_doctor(fix: bool = False, as_json: bool = False) -> int:
    """Run all 9 checks and optionally perform auto-repair."""
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
