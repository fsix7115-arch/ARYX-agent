"""
ARYx AGENT - Procedural Skill Engine
Learns and refines skills after complex tasks (>5 tool calls) with quality gates and versioning.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aryx.config import SKILLS_DIR, ensure_aryx_directories
from aryx.memory.db import get_db_connection


def list_skills() -> List[Dict[str, Any]]:
    """List all available skills with their metadata and success rate."""
    ensure_aryx_directories()
    results = []

    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM skills_meta WHERE archived = 0")
            meta_map = {row["name"]: dict(row) for row in cur.fetchall()}
    except Exception:
        meta_map = {}

    for file in SKILLS_DIR.glob("*.md"):
        name = file.stem
        meta = meta_map.get(name, {
            "name": name,
            "version": 1,
            "success_count": 1,
            "fail_count": 0,
            "last_used": file.stat().st_mtime,
            "archived": 0,
        })
        successes = meta.get("success_count", 0)
        fails = meta.get("fail_count", 0)
        total = successes + fails
        rate = (successes / total * 100) if total > 0 else 100.0

        results.append({
            "name": name,
            "path": str(file),
            "version": meta.get("version", 1),
            "success_count": successes,
            "fail_count": fails,
            "success_rate": round(rate, 1),
            "size": file.stat().st_size,
        })
    return sorted(results, key=lambda x: x["name"])


def read_skill(name: str) -> Optional[str]:
    """Read the content of a skill markdown file."""
    ensure_aryx_directories()
    # Handle both with or without .md
    clean_name = name.removesuffix(".md")
    path = SKILLS_DIR / f"{clean_name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def save_skill(name: str, content: str, version: int = 1) -> str:
    """Save or update a procedural skill markdown file."""
    ensure_aryx_directories()
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower().strip())
    path = SKILLS_DIR / f"{safe_name}.md"
    path.write_text(content, encoding="utf-8")

    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO skills_meta (name, version, success_count, fail_count, last_used, archived)
                VALUES (?, ?, 1, 0, ?, 0)
                ON CONFLICT(name) DO UPDATE SET
                    version = ?,
                    last_used = ?
                """,
                (safe_name, version, time.time(), version, time.time()),
            )
            conn.commit()
    except Exception:
        pass

    return str(path)


def record_skill_outcome(name: str, success: bool) -> None:
    """Record a skill execution success or failure (Quality Gate)."""
    clean_name = name.removesuffix(".md")
    try:
        with get_db_connection() as conn:
            if success:
                conn.execute(
                    "UPDATE skills_meta SET success_count = success_count + 1, last_used = ? WHERE name = ?",
                    (time.time(), clean_name),
                )
            else:
                conn.execute(
                    "UPDATE skills_meta SET fail_count = fail_count + 1, last_used = ? WHERE name = ?",
                    (time.time(), clean_name),
                )
            conn.commit()
            _evaluate_quality_gate(conn, clean_name)
    except Exception:
        pass


def _evaluate_quality_gate(conn: Any, name: str) -> None:
    """Archive skill if <20% success over 10+ uses."""
    cur = conn.execute("SELECT success_count, fail_count FROM skills_meta WHERE name = ?", (name,))
    row = cur.fetchone()
    if not row:
        return

    successes = row["success_count"]
    fails = row["fail_count"]
    total = successes + fails
    if total >= 10:
        rate = successes / total
        if rate < 0.20:
            conn.execute("UPDATE skills_meta SET archived = 1 WHERE name = ?", (name,))
            conn.commit()


def generate_skill_from_run(task_description: str, tool_history: List[Dict[str, Any]]) -> Optional[str]:
    """
    Creates a new skill when a complex task (>5 tool calls) succeeds.
    """
    if len(tool_history) < 5:
        return None

    # Derive a clean skill title
    words = re.findall(r"\b[a-zA-Z]{3,}\b", task_description.lower())
    title_words = [w for w in words if w not in {"the", "and", "for", "with", "this", "that"}][:4]
    skill_name = "-".join(title_words) or f"task_{int(time.time())}"

    steps_md = []
    for i, step in enumerate(tool_history, 1):
        tool_name = step.get("name", "unknown")
        args_summary = str(step.get("args", {}))[:100]
        steps_md.append(f"{i}. Execute `{tool_name}`: {args_summary}")

    content = f"""# Skill: {skill_name.replace('-', ' ').title()}

## Objective
{task_description}

## Verified Procedure
{chr(10).join(steps_md)}

## Learned Rules
- Auto-generated by ARYx Agent Quality Engine after {len(tool_history)} successful tool executions.
- Verified on {time.strftime('%Y-%m-%d %H:%M:%S')}.
"""
    saved_path = save_skill(skill_name, content, version=1)
    return saved_path
