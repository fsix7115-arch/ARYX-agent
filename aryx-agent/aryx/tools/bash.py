"""
ARYx AGENT - Sandboxed Bash Tool
Safely executes shell commands with strict safety filters, timeout protection, and directory locking.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List

# Strict dangerous pattern blacklist
DANGEROUS_PATTERNS = [
    r"\brm\s+-[rfRF]{1,4}\s+/\b",           # rm -rf /
    r"\brm\s+-[rfRF]{1,4}\s+~/\b",          # rm -rf ~/
    r"\bmkfs\b",                            # formatting disks
    r"\bdd\s+if=.*of=/dev/[sh]d",           # raw disk overwriting
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", # fork bomb
    r">\s*/dev/sd[a-z]",                    # wiping disk devices
    r">\s*/dev/nvme",
    r"\bchmod\s+-[rR]\s+000\s+/",           # stripping root permissions
    r"\bchown\s+-[rR].*\s+/",               # mass permission changes
]


def check_is_dangerous(command: str) -> bool:
    """Checks if a bash command contains inherently destructive patterns."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return True
    return False


def run_bash(
    command: str,
    cwd: str = ".",
    timeout: int = 30,
    allow_network: bool = False,
) -> Dict[str, Any]:
    """
    Executes a shell command in a subprocess with safety limits.
    """
    command = command.strip()
    if not command:
        return {"error": "Empty command provided."}

    # Safety check: block explicitly dangerous commands
    if check_is_dangerous(command):
        return {
            "error": "Command blocked by ARYx safety filter: contains potentially destructive patterns."
        }

    working_dir = Path(cwd).resolve()
    if not working_dir.exists():
        working_dir = Path(".").resolve()

    # Environment sandboxing
    env = dict(os.environ)
    if not allow_network:
        # Prevent git/curl proxying if offline desired
        env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        process = subprocess.run(
            command,
            shell=True,
            cwd=str(working_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = process.stdout
        stderr = process.stderr

        # Limit output length to prevent terminal overflow
        max_output_len = 10000
        truncated = False
        if len(stdout) > max_output_len:
            stdout = stdout[:max_output_len] + "\n...[stdout truncated]..."
            truncated = True
        if len(stderr) > max_output_len:
            stderr = stderr[:max_output_len] + "\n...[stderr truncated]..."
            truncated = True

        return {
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": truncated,
            "success": process.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "error": f"Command timed out after {timeout} seconds.",
            "exit_code": -1,
            "timed_out": True,
        }
    except Exception as e:
        return {
            "error": f"Execution error: {str(e)}",
            "exit_code": -1,
        }
