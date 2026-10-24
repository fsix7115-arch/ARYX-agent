"""
ARYx AGENT - Tool Definitions, Schemas & Dispatcher
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from aryx.tools.bash import run_bash
from aryx.tools.files import (
    edit_file,
    glob_search,
    grep_search,
    list_dir,
    read_file,
    revert_last_snapshots,
    write_file,
)
from aryx.tools.python import run_python
from aryx.tools.web import web_fetch, web_search

# Tools grouped by classification
READ_ONLY_TOOLS = {"read_file", "list_dir", "glob", "grep", "web_fetch", "web_search"}
WRITE_TOOLS = {"write_file", "edit_file", "bash", "python"}

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read contents of a file on disk.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read."},
                "max_lines": {"type": "integer", "description": "Maximum number of lines to return (default 500)."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files and folders in a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (defaults to current dir)."},
                "recursive": {"type": "boolean", "description": "Whether to list subdirectories recursively."},
            },
        },
    },
    {
        "name": "glob",
        "description": "Find files matching a glob pattern (e.g. '**/*.py').",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern."},
                "root_dir": {"type": "string", "description": "Directory to start searching from."},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "grep",
        "description": "Search file contents for regex or text string.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regular expression or text to match."},
                "root_dir": {"type": "string", "description": "Root directory to search inside."},
                "file_pattern": {"type": "string", "description": "File name glob pattern like '*.py'."},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file with given content. Automatic snapshot taken before writing.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination file path."},
                "content": {"type": "string", "description": "The exact full file content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Surgically replace an exact block of code inside a file. Automatic snapshot taken before editing.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to edit."},
                "target_content": {"type": "string", "description": "The exact unique lines of code to replace."},
                "replacement_content": {"type": "string", "description": "The new replacement code lines."},
            },
            "required": ["path", "target_content", "replacement_content"],
        },
    },
    {
        "name": "bash",
        "description": "Execute a safe shell command in the project directory. Dangerous operations are blocked.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command line to run."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "python",
        "description": "Execute a Python script with timeout.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code to execute."},
            },
            "required": ["code"],
        },
    },
    {
        "name": "web_fetch",
        "description": "Fetch and extract text content from a public web page.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for up-to-date documentation or technical answers.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query keywords."},
            },
            "required": ["query"],
        },
    },
]


def dispatch_tool(name: str, args: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """Execute tool by name with arguments."""
    try:
        if name == "read_file":
            return read_file(path=args.get("path", ""), max_lines=args.get("max_lines", 500))
        elif name == "list_dir":
            return list_dir(path=args.get("path", "."), recursive=args.get("recursive", False))
        elif name == "glob":
            return glob_search(pattern=args.get("pattern", "*"), root_dir=args.get("root_dir", "."))
        elif name == "grep":
            return grep_search(
                pattern=args.get("pattern", ""),
                root_dir=args.get("root_dir", "."),
                file_pattern=args.get("file_pattern", "*"),
            )
        elif name == "write_file":
            return write_file(path=args.get("path", ""), content=args.get("content", ""))
        elif name == "edit_file":
            return edit_file(
                path=args.get("path", ""),
                target_content=args.get("target_content", ""),
                replacement_content=args.get("replacement_content", ""),
            )
        elif name == "bash":
            return run_bash(command=args.get("command", ""), timeout=timeout)
        elif name == "python":
            return run_python(code=args.get("code", ""), timeout=timeout)
        elif name == "web_fetch":
            return web_fetch(url=args.get("url", ""))
        elif name == "web_search":
            return web_search(query=args.get("query", ""))
        else:
            return {"error": f"Unknown tool: '{name}'"}
    except Exception as e:
        return {"error": f"Tool execution failure in '{name}': {str(e)}"}


__all__ = [
    "READ_ONLY_TOOLS",
    "WRITE_TOOLS",
    "TOOL_DEFINITIONS",
    "dispatch_tool",
    "revert_last_snapshots",
]
