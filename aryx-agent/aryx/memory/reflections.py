"""
ARYx AGENT - Reflection Engine
Provides periodic self-assessment checkpoints every 3-5 tool steps ("are we on track?").
"""

from __future__ import annotations

from typing import Any, Dict, List


def evaluate_progress(
    user_goal: str,
    steps_taken: List[Dict[str, Any]],
    current_step: int,
) -> Dict[str, Any]:
    """
    Evaluates whether the agent is making progress toward the user's goal or looping.
    """
    if current_step < 3:
        return {"on_track": True, "reason": "Initial progress"}

    # Detect tool output repetition or loop
    recent_tools = [s.get("name") for s in steps_taken[-3:]]
    if len(recent_tools) == 3 and recent_tools[0] == recent_tools[1] == recent_tools[2]:
        # Same tool called 3 times in a row
        errors = [s.get("result", {}).get("error") for s in steps_taken[-3:] if isinstance(s.get("result"), dict)]
        if any(errors):
            return {
                "on_track": False,
                "reason": f"Repeating tool '{recent_tools[0]}' with errors. Switching approach recommended.",
            }

    return {
        "on_track": True,
        "reason": f"Completed {current_step} steps toward goal: '{user_goal[:50]}...'",
    }
