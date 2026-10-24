"""
ARYx AGENT - Status Line & Metrics
Outputs clean, dim status lines after each turn:
`gemini-2.5-flash · 1.2k tokens · skill: none`
"""

from __future__ import annotations

import sys


def format_tokens(num: int) -> str:
    """Format token count (e.g. 1200 -> 1.2k)."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}k"
    return str(num)


def print_status_line(
    model: str = "gemini-2.5-flash",
    total_tokens: int = 0,
    skill_name: str = "none",
) -> None:
    """Prints standard dim status line after response."""
    tok_str = format_tokens(total_tokens)
    status_str = f"{model} · {tok_str} tokens · skill: {skill_name}"

    try:
        from rich.console import Console
        console = Console()
        console.print(f"[dim]{status_str}[/dim]\n")
    except Exception:
        print(f"  [{status_str}]\n")
