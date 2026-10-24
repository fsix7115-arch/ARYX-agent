"""
ARYx AGENT - Gateway agent runner (Sections 16.1/16.9).

This is the SAME agent loop the terminal uses — provider.chat with
TOOL_DEFINITIONS, up to 10 turns — minus terminal I/O. The one
difference: on messaging channels a write tool does not ask "y?" on
a keyboard. It PAUSES, and the gateway sends Approve/Reject buttons.
The user's tap resumes the exact same loop via a Continuation.

Approval is forced to "safe" on messaging channels by GatewayCore
(see core.AuthManager.effective_approval_mode); this runner simply
honours the mode it is given.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from aryx.gateway.types import ApprovalRequest

DEFAULT_SYSTEM_PROMPT = (
    "You are ARYx, a helpful terminal AI agent. Answer concisely. "
    "Use tools when they help. Never reveal API keys or tokens."
)

MAX_TURNS = 10


class TurnResult:
    """Outcome of one agent turn: a final reply, or a pause for approval."""

    def __init__(
        self,
        kind: str,
        text: str = "",
        approval: Optional[ApprovalRequest] = None,
        continuation: Any = None,
    ) -> None:
        self.kind = kind  # "reply" | "approval"
        self.text = text
        self.approval = approval
        self.continuation = continuation


def _system_prompt() -> str:
    try:
        from aryx.cli import build_system_prompt  # lazy: avoids import cycles

        return build_system_prompt()
    except Exception:
        return DEFAULT_SYSTEM_PROMPT


def _redact(text: str) -> str:
    try:
        from aryx.config import redact_secrets

        return redact_secrets(text)
    except Exception:
        return text


class Continuation:
    """Paused agent loop, resumable by one approval decision."""

    def __init__(self, runner: "AgentRunner", state: Dict[str, Any]) -> None:
        self.runner = runner
        self.state = state

    def resolve(self, approved: bool) -> TurnResult:
        return self.runner._continue(self.state, approved)


class AgentRunner:
    """Runs agent turns for gateway sessions (stateless between turns)."""

    def start_turn(
        self,
        history: List[Dict[str, str]],
        user_text: str,
        approval_mode: str = "safe",
        stop_flag: Optional[threading.Event] = None,
    ) -> TurnResult:
        try:
            from aryx.config import get_active_provider_config, load_config
            from aryx.providers import get_provider
        except Exception as e:  # noqa: BLE001
            return TurnResult("reply", f"Agent is unavailable: {_redact(str(e))}")
        try:
            config = load_config()
            active_provider, p_cfg = get_active_provider_config(config)
        except Exception as e:  # noqa: BLE001
            return TurnResult("reply", f"Could not load configuration: {_redact(str(e))}")
        if active_provider != "ollama" and not p_cfg.get("api_key"):
            return TurnResult(
                "reply",
                "No provider is configured yet. Run `aryx` once on your "
                "computer to set up a provider, then try again here.",
            )
        try:
            provider = get_provider(active_provider, config)
        except Exception as e:  # noqa: BLE001
            return TurnResult("reply", f"Could not load provider '{active_provider}': {_redact(str(e))}")
        try:
            from aryx.memory import extract_quick_facts

            extract_quick_facts(user_text)
        except Exception:
            pass
        messages: List[Dict[str, Any]] = [{"role": "system", "content": _system_prompt()}]
        messages.extend({"role": h["role"], "content": h["content"]} for h in history)
        messages.append({"role": "user", "content": user_text})
        state: Dict[str, Any] = {
            "messages": messages,
            "provider": provider,
            "config": config,
            "approval_mode": approval_mode,
            "stop_flag": stop_flag,
            "last_text": "",
        }
        return self._loop(state)

    # -- the loop (shared by start and resume) --------------------------
    def _loop(self, state: Dict[str, Any]) -> TurnResult:
        from aryx.tools import TOOL_DEFINITIONS, WRITE_TOOLS, dispatch_tool

        messages = state["messages"]
        provider = state["provider"]
        config = state["config"]
        approval_mode = state["approval_mode"]
        stop_flag = state.get("stop_flag")
        for _ in range(MAX_TURNS):
            if stop_flag is not None and stop_flag.is_set():
                return TurnResult("reply", "Stopped.")
            try:
                response = provider.chat(messages=messages, tools=TOOL_DEFINITIONS)
            except Exception as e:  # noqa: BLE001
                return TurnResult("reply", f"Something went wrong: {_redact(str(e))}\nCheck your network connection or run `aryx doctor`.")
            content = response.get("content", "") or ""
            tool_calls = response.get("tool_calls", []) or []
            if content:
                state["last_text"] = content
            if not tool_calls:
                return TurnResult("reply", content or state["last_text"] or "Done.")
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            for index, tc in enumerate(tool_calls):
                fn_name = tc.get("name", "")
                fn_args = tc.get("args", {}) or {}
                if fn_name in WRITE_TOOLS and approval_mode != "yolo":
                    # PAUSE here. The gateway sends buttons; the tap
                    # resumes via Continuation.resolve().
                    pending_state = dict(state)
                    pending_state["pending_calls"] = tool_calls[index:]
                    pending_state["pending_index"] = 0
                    summary = self._describe_tool(fn_name, fn_args)
                    return TurnResult(
                        "approval",
                        "",
                        approval=ApprovalRequest(
                            tool_name=fn_name, args=fn_args, summary=summary
                        ),
                        continuation=Continuation(self, pending_state),
                    )
                result = self._run_tool(dispatch_tool, fn_name, fn_args, config)
                messages.append(
                    {
                        "role": "tool",
                        "name": fn_name,
                        "tool_call_id": tc.get("id", f"call_{index}"),
                        "content": str(result),
                    }
                )
        return TurnResult("reply", state["last_text"] or "Done.")

    def _continue(self, state: Dict[str, Any], approved: bool) -> TurnResult:
        from aryx.tools import dispatch_tool

        pending_calls = state.get("pending_calls", [])
        index = state.get("pending_index", 0)
        if index >= len(pending_calls):
            return self._loop(state)
        tc = pending_calls[index]
        fn_name = tc.get("name", "")
        fn_args = tc.get("args", {}) or {}
        if approved:
            result = self._run_tool(dispatch_tool, fn_name, fn_args, state["config"])
        else:
            result = {"error": "Action cancelled by user."}
        state["messages"].append(
            {
                "role": "tool",
                "name": fn_name,
                "tool_call_id": tc.get("id", f"call_{index}"),
                "content": str(result),
            }
        )
        # Any remaining calls in this batch go through the loop again,
        # which will pause again if another write needs approval.
        rest = pending_calls[index + 1 :]
        if rest:
            state["pending_calls"] = rest
            state["pending_index"] = 0
            # Re-enter the loop via a synthetic pass: process the rest
            # as if they were a fresh tool batch on the same messages.
            # Simplest correct path: run them through _loop's tool
            # handling by faking a response — instead, execute them
            # inline here (read-only tools run, writes pause again).
            from aryx.tools import WRITE_TOOLS

            for j, next_tc in enumerate(rest):
                n_name = next_tc.get("name", "")
                n_args = next_tc.get("args", {}) or {}
                if n_name in WRITE_TOOLS and state["approval_mode"] != "yolo":
                    new_state = dict(state)
                    new_state["pending_calls"] = rest[j:]
                    new_state["pending_index"] = 0
                    return TurnResult(
                        "approval",
                        "",
                        approval=ApprovalRequest(
                            tool_name=n_name,
                            args=n_args,
                            summary=self._describe_tool(n_name, n_args),
                        ),
                        continuation=Continuation(self, new_state),
                    )
                r = self._run_tool(dispatch_tool, n_name, n_args, state["config"])
                state["messages"].append(
                    {
                        "role": "tool",
                        "name": n_name,
                        "tool_call_id": next_tc.get("id", f"call_{j}"),
                        "content": str(r),
                    }
                )
        state.pop("pending_calls", None)
        state.pop("pending_index", None)
        return self._loop(state)

    @staticmethod
    def _run_tool(dispatch_tool: Any, fn_name: str, fn_args: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            timeout = config.get("general", {}).get("command_timeout", 30)
            return dispatch_tool(fn_name, fn_args, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            return {"error": _redact(str(e))}

    @staticmethod
    def _describe_tool(fn_name: str, fn_args: Dict[str, Any]) -> str:
        """Human summary for an approval prompt. Args are redacted."""
        safe_args = {k: ("***" if "key" in k.lower() or "token" in k.lower() else v) for k, v in fn_args.items()}
        if fn_name == "bash":
            return f"bash: {safe_args.get('command', '')}"
        if fn_name in ("write_file", "edit_file"):
            return f"{fn_name}: {safe_args.get('path', '')}"
        if fn_name == "python":
            return "python: run a script"
        return f"{fn_name}: {safe_args}"
