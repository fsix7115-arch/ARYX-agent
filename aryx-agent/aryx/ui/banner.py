"""
ARYx AGENT - Terminal Banner & Branding
Pure ASCII logo rendering with graceful color degradation.
"""

from __future__ import annotations

import os
import sys

ASCII_LOGO = r"""
    █████╗ ██████╗ ██╗   ██╗██╗  ██╗
   ██╔══██╗██╔══██╗╚██╗ ██╔╝╚██╗██╔╝
   ███████║██████╔╝ ╚████╔╝  ╚███╔╝ 
   ██╔══██║██╔══██╗  ╚██╔╝   ██╔██╗ 
   ██║  ██║██║  ██║   ██║   ██╔╝ ██╗
   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝
       A G E N T  ·  v0.1.0
"""

TAGLINE = "Zero-friction, self-healing, multi-provider terminal AI agent"


def print_banner(color: bool = True) -> None:
    """Print the official ARYx Agent ASCII banner."""
    no_color = os.getenv("NO_COLOR") is not None or not sys.stdout.isatty() or not color

    if no_color:
        print(ASCII_LOGO)
        print(f"       {TAGLINE}\n")
        return

    try:
        from rich.console import Console
        from rich.text import Text

        console = Console()
        text = Text(ASCII_LOGO, style="bold cyan")
        console.print(text)
        console.print(f"[dim]{TAGLINE}[/dim]\n")
    except Exception:
        # Graceful plain fallback
        print(ASCII_LOGO)
        print(f"       {TAGLINE}\n")
