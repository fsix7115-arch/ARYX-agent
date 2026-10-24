"""
ARYx AGENT - Sandboxed Python Tool
Executes standalone Python code snippets with timeout and isolation.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


def run_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code in a child process."""
    if not code.strip():
        return {"error": "No Python code provided."}

    # Write code to a secure temporary file
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        process = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = process.stdout
        stderr = process.stderr
        max_len = 10000

        if len(stdout) > max_len:
            stdout = stdout[:max_len] + "\n...[stdout truncated]..."
        if len(stderr) > max_len:
            stderr = stderr[:max_len] + "\n...[stderr truncated]..."

        return {
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "success": process.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Python execution timed out after {timeout} seconds.", "timed_out": True}
    except Exception as e:
        return {"error": f"Failed running Python: {str(e)}"}
    finally:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
