"""
ARYx AGENT - Chat UI & Formatting
Renders markdown, tool step execution indicators, approval prompts, and tables.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
except ImportError:
    console = None  # type: ignore


def print_message(role: str, text: str) -> None:
    """Print chat message with role styling."""
    if console:
        if role == "assistant":
            console.print(Markdown(text))
        elif role == "system":
            console.print(f"[dim]{text}[/dim]")
        elif role == "tool":
            console.print(f"[yellow]{text}[/yellow]")
        elif role == "error":
            console.print(f"[bold red]{text}[/bold red]")
        else:
            console.print(text)
    else:
        print(text)


def print_tool_call(name: str, args: Dict[str, Any]) -> None:
    """Display an executing tool step."""
    arg_preview = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
    if console:
        console.print(f"  [cyan]⚡ Executing[/cyan] [bold]{name}[/bold]({arg_preview})...")
    else:
        print(f"  ⚡ Executing {name}({arg_preview})...")


def print_tool_result(name: str, success: bool, summary: str) -> None:
    """Display tool result outcome."""
    symbol = "✓" if success else "✗"
    color = "green" if success else "red"
    if console:
        console.print(f"  [{color}]{symbol}[/{color}] [dim]{summary}[/dim]")
    else:
        print(f"  {symbol} {summary}")


def prompt_approval(tool_name: str, args: Dict[str, Any]) -> bool:
    """Prompt user for confirmation before executing write/bash actions."""
    if console:
        console.print(f"\n[bold yellow]! Action Approval Required:[/bold yellow]")
        console.print(f"  Tool: [bold cyan]{tool_name}[/bold cyan]")
        for k, v in args.items():
            console.print(f"  {k}: [dim]{repr(v)[:200]}[/dim]")
    else:
        print(f"\n! Action Approval Required:\n  Tool: {tool_name}\n  Args: {args}")

    while True:
        try:
            choice = input("Approve this action? [Y/n] ").strip().lower()
            if choice in ("", "y", "yes"):
                return True
            elif choice in ("n", "no"):
                return False
        except (KeyboardInterrupt, EOFError):
            return False


def render_table(title: str, headers: List[str], rows: List[List[str]]) -> None:
    """Render a structured terminal table."""
    if console:
        table = Table(title=title, show_header=True, header_style="bold magenta")
        for h in headers:
            table.add_column(h)
        for r in rows:
            table.add_row(*r)
        console.print(table)
    else:
        print(f"\n=== {title} ===")
        print(" | ".join(headers))
        print("-" * 40)
        for r in rows:
            print(" | ".join(r))
        print("")
