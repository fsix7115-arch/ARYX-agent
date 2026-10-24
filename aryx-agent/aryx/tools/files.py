"""
ARYx AGENT - File System Tools & Snapshot System
Handles read_file, list_dir, glob, grep, write_file, edit_file with automatic snapshots for /revert.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aryx.config import SNAPSHOTS_DIR, ensure_aryx_directories


def create_snapshot(filepath: str) -> Optional[str]:
    """
    Creates a timestamped snapshot of a file before modification.
    Returns the backup path.
    """
    ensure_aryx_directories()
    src = Path(filepath).resolve()
    if not src.exists() or not src.is_file():
        return None

    timestamp = int(time.time() * 1000)
    safe_name = src.name.replace("/", "_")
    dest = SNAPSHOTS_DIR / f"{timestamp}_{safe_name}"

    try:
        shutil.copy2(src, dest)
        # Store metadata mapping in ~/.aryx/snapshots/index.log
        index_file = SNAPSHOTS_DIR / "index.log"
        with open(index_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp}|{dest.name}|{src}\n")
        return str(dest)
    except Exception:
        return None


def revert_last_snapshots(count: int = 1) -> List[str]:
    """
    Reverts the last N file modifications from snapshots.
    Returns list of restored file paths.
    """
    index_file = SNAPSHOTS_DIR / "index.log"
    if not index_file.exists():
        return []

    lines = index_file.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return []

    reverted: List[str] = []
    to_revert = lines[-count:]
    remaining = lines[:-count]

    for line in reversed(to_revert):
        parts = line.strip().split("|")
        if len(parts) == 3:
            _, backup_filename, original_path_str = parts
            backup_path = SNAPSHOTS_DIR / backup_filename
            original_path = Path(original_path_str)

            if backup_path.exists():
                try:
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, original_path)
                    reverted.append(str(original_path))
                except Exception:
                    pass

    # Update index file
    index_file.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    return reverted


def read_file(path: str, max_lines: int = 500) -> Dict[str, Any]:
    """Read contents of a file up to max_lines."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Path is not a file: {path}"}

    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines = len(lines)
        clipped = lines[:max_lines]
        content = "\n".join(clipped)
        truncated = total_lines > max_lines

        return {
            "path": str(p),
            "content": content,
            "total_lines": total_lines,
            "truncated": truncated,
        }
    except Exception as e:
        return {"error": f"Failed reading {path}: {str(e)}"}


def list_dir(path: str = ".", recursive: bool = False, max_items: int = 200) -> Dict[str, Any]:
    """List directory entries."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Directory not found: {path}"}
    if not p.is_dir():
        return {"error": f"Path is not a directory: {path}"}

    items = []
    try:
        if recursive:
            for root, dirs, files in os.walk(p):
                # Skip hidden directories like .git
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                rel_root = Path(root).relative_to(p)
                for f in files:
                    if f.startswith("."):
                        continue
                    rel_path = (rel_root / f) if str(rel_root) != "." else Path(f)
                    items.append({"name": str(rel_path), "type": "file"})
                    if len(items) >= max_items:
                        break
                if len(items) >= max_items:
                    break
        else:
            for entry in sorted(p.iterdir()):
                if entry.name.startswith("."):
                    continue
                items.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else None,
                })
                if len(items) >= max_items:
                    break
        return {"directory": str(p), "items": items, "count": len(items)}
    except Exception as e:
        return {"error": f"Failed listing directory {path}: {str(e)}"}


def glob_search(pattern: str, root_dir: str = ".") -> Dict[str, Any]:
    """Search files matching a glob pattern."""
    p = Path(root_dir).resolve()
    matched = []
    try:
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            rel_root = Path(root).relative_to(p)
            for f in files:
                if f.startswith("."):
                    continue
                rel_path = str((rel_root / f) if str(rel_root) != "." else Path(f))
                if fnmatch.fnmatch(rel_path, pattern):
                    matched.append(rel_path)
                if len(matched) >= 100:
                    break
            if len(matched) >= 100:
                break
        return {"pattern": pattern, "matches": matched}
    except Exception as e:
        return {"error": f"Glob error: {str(e)}"}


def grep_search(pattern: str, root_dir: str = ".", file_pattern: str = "*") -> Dict[str, Any]:
    """Search file contents matching regex or text."""
    p = Path(root_dir).resolve()
    matches = []
    try:
        regex = re.compile(pattern, re.IGNORECASE)
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            rel_root = Path(root).relative_to(p)
            for f in files:
                if f.startswith(".") or not fnmatch.fnmatch(f, file_pattern):
                    continue
                filepath = Path(root) / f
                try:
                    for i, line in enumerate(filepath.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                        if regex.search(line):
                            rel_path = str((rel_root / f) if str(rel_root) != "." else Path(f))
                            matches.append({"file": rel_path, "line": i, "content": line.strip()})
                            if len(matches) >= 100:
                                break
                except Exception:
                    continue
                if len(matches) >= 100:
                    break
            if len(matches) >= 100:
                break
        return {"query": pattern, "matches": matches, "count": len(matches)}
    except Exception as e:
        return {"error": f"Grep error: {str(e)}"}


def write_file(path: str, content: str) -> Dict[str, Any]:
    """Write entire content to a file, taking a snapshot first."""
    p = Path(path).resolve()
    snapshot = create_snapshot(str(p))

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "path": str(p),
            "bytes_written": len(content.encode("utf-8")),
            "snapshot_saved": snapshot is not None,
        }
    except Exception as e:
        return {"error": f"Failed writing file {path}: {str(e)}"}


def edit_file(path: str, target_content: str, replacement_content: str) -> Dict[str, Any]:
    """Surgically replace a unique block of text inside a file with snapshotting."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Cannot edit non-existent file: {path}"}

    snapshot = create_snapshot(str(p))

    try:
        current_text = p.read_text(encoding="utf-8")
        if target_content not in current_text:
            return {
                "error": f"Target content not found in {path}. Make sure the search block matches exact whitespace and indentation."
            }

        count = current_text.count(target_content)
        if count > 1:
            return {
                "error": f"Target content occurs {count} times in {path}. Please provide a larger unique surrounding chunk."
            }

        new_text = current_text.replace(target_content, replacement_content, 1)
        p.write_text(new_text, encoding="utf-8")
        return {
            "success": True,
            "path": str(p),
            "replaced_chars": len(replacement_content),
            "snapshot_saved": snapshot is not None,
        }
    except Exception as e:
        return {"error": f"Failed editing {path}: {str(e)}"}
