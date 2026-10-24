"""
ARYx AGENT - Main CLI Entry Point & Agent Execution Loop
Zero-friction, self-healing, multi-provider terminal AI agent.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import typer
except ImportError:
    typer = None  # Handled below with standard library argparse fallback

from aryx import __version__
from aryx.config import (
    ARYX_DIR,
    CONFIG_FILE,
    MEMORY_DB,
    SKILLS_DIR,
    SNAPSHOTS_DIR,
    SUPPORTED_PROVIDERS,
    detect_provider_from_key,
    ensure_aryx_directories,
    get_active_provider_config,
    load_config,
    redact_key,
    redact_secrets,
    save_config,
)
from aryx.doctor import run_doctor
from aryx.help import IN_CHAT_HELP_TEXT, show_help
from aryx.memory import (
    add_semantic_fact,
    evaluate_progress,
    extract_quick_facts,
    generate_skill_from_run,
    get_semantic_facts,
    list_skills,
    read_skill,
    record_skill_outcome,
    save_message,
    search_history,
)
from aryx.providers import get_provider
from aryx.tools import READ_ONLY_TOOLS, TOOL_DEFINITIONS, WRITE_TOOLS, dispatch_tool, revert_last_snapshots
from aryx.ui import (
    print_banner,
    print_message,
    print_status_line,
    print_tool_call,
    print_tool_result,
    prompt_approval,
    render_table,
)

HAS_REAL_TYPER = typer is not None

if typer:
    app = typer.Typer(
        help="ARYx AGENT — Zero-friction, self-healing, multi-provider terminal AI agent.",
        add_completion=False,
    )
else:
    class FakeTyper:
        def command(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def callback(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def Option(self, default=None, *args, **kwargs):
            return default

        def Argument(self, default=None, *args, **kwargs):
            return default

    typer = FakeTyper()  # type: ignore
    app = typer


def first_run_setup() -> bool:
    """
    30-second setup experience:
    - Asks ONE question: paste key
    - Auto-detects provider from prefix
    - Runs 5-token validation probe
    - Saves config with chmod 600
    """
    # Clear screen if possible
    os.system("clear" if os.name == "posix" else "cls")
    print_banner()

    print("  Welcome! Let's set you up in 30 seconds.\n")
    max_tries = 3

    for attempt in range(1, max_tries + 1):
        try:
            user_input = input("  Paste your API key (or press Enter to choose a provider): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            return False

        detected = None
        if user_input:
            detected = detect_provider_from_key(user_input)

        if not detected:
            if not user_input:
                print("\n  Available Providers:")
            else:
                # Never print any part of the pasted key.
                print("\n  That key prefix wasn't recognized.")
                print("  Please select your provider from the list:")

            for i, p in enumerate(SUPPORTED_PROVIDERS, 1):
                print(f"    [{i}] {p['name']}")
            print("")

            try:
                choice_str = input("  Choose provider [1-6]: ").strip()
                choice_idx = int(choice_str) - 1
                if 0 <= choice_idx < len(SUPPORTED_PROVIDERS):
                    selected = SUPPORTED_PROVIDERS[choice_idx]
                    p_id = selected["id"]
                    if p_id == "ollama":
                        # Ollama needs no key
                        config = load_config()
                        config["provider"]["active"] = "ollama"
                        save_config(config)
                        print("  ✓ Configured Ollama (local / offline).")
                        return True

                    key_input = input(f"  Enter your {selected['name']} API key: ").strip()
                    detected = {
                        "provider": p_id,
                        "default_model": selected["default_model"],
                        "name": selected["name"],
                        "key_url": "https://aistudio.google.com/apikey" if p_id == "gemini" else "",
                    }
                    user_input = key_input
                else:
                    print("  Invalid selection. Let's try again.")
                    continue
            except (ValueError, KeyboardInterrupt, EOFError):
                print("  Invalid selection.")
                continue

        # Validate with test call
        p_name = detected["provider"]
        model = detected["default_model"]
        print(f"  Testing connection to {detected['name']}...")

        # Construct temporary provider config
        test_config = load_config()
        test_config["provider"]["active"] = p_name
        test_config["providers"][p_name]["api_key"] = user_input
        test_config["providers"][p_name]["model"] = model

        try:
            prov = get_provider(p_name, test_config)
            valid, msg = prov.validate_key()
            if valid:
                save_config(test_config)
                print(f"  ✓ {detected['name']} connected successfully!\n")
                return True
            else:
                print(f"\n  ✗ That key didn't work. Check for extra spaces or typos.")
                if detected.get("key_url"):
                    print(f"    Get a free key at: {detected['key_url']}")
                print(f"    Details: {msg}\n")
        except Exception as e:
            print(f"\n  ✗ Connection error: {redact_secrets(str(e))}")
            print(f"    Still stuck? Run: aryx doctor\n")

        if attempt == max_tries:
            print("  Setup could not complete. Run `aryx help setup` for a complete walkthrough.")
            return False

    return False


def build_system_prompt() -> str:
    """Build dynamic agent system prompt with memory context."""
    facts = get_semantic_facts(limit=10)
    facts_block = ""
    if facts:
        facts_lines = [f"- {f['fact']}" for f in facts]
        facts_block = "\n## Learned User Preferences & Context:\n" + "\n".join(facts_lines)

    skills = list_skills()
    skills_block = ""
    if skills:
        skills_lines = [f"- {s['name']} (success rate: {s['success_rate']}%)" for s in skills[:5]]
        skills_block = "\n## Active Learned Skills:\n" + "\n".join(skills_lines)

    return f"""You are ARYx AGENT, a zero-friction, production-grade terminal AI assistant.
You possess native tools for filesystem operations, code editing, sandboxed bash execution, and web research.

Always aim for exact, reliable actions:
1. PERCEIVE: Inspect current files and project state before modifying.
2. PLAN: Outline concise steps before performing complex changes.
3. ACT: Use surgical edit_file or write_file instead of vague instructions.
4. OBSERVE: Confirm tool outputs before reporting back.
{facts_block}
{skills_block}
"""


def start_chat_session(yolo: bool = False, verbose: bool = False) -> None:
    """Main interactive chat loop."""
    config = load_config()
    active_provider, p_cfg = get_active_provider_config(config)

    # First run check
    if not CONFIG_FILE.exists() or (active_provider != "ollama" and not p_cfg.get("api_key")):
        success = first_run_setup()
        if not success:
            return
        config = load_config()
        active_provider, p_cfg = get_active_provider_config(config)

    session_id = f"session_{uuid.uuid4().hex[:8]}"
    model_name = p_cfg.get("model", "default")
    approval_mode = "yolo" if yolo else config.get("general", {}).get("approval_mode", "safe")

    print_banner()
    print("  You're all set. Ask me anything, or type /help.\n")

    history: List[Dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt()}
    ]

    session_tokens = 0
    active_skill = "none"

    while True:
        try:
            user_input = input("aryx > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # In-chat slash commands
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=2)
            cmd = parts[0].lower()

            if cmd in ("/quit", "/exit", "/q"):
                print("Session saved. See you next time!")
                break
            elif cmd in ("/help", "/h"):
                print(IN_CHAT_HELP_TEXT)
                continue
            elif cmd == "/clear":
                history = [{"role": "system", "content": build_system_prompt()}]
                print("  ✓ Conversation history cleared (persistent memory preserved).")
                continue
            elif cmd == "/doctor":
                print("\nRunning ARYx Doctor functional probes...")
                run_doctor(fix=False)
                continue
            elif cmd == "/memory":
                facts = get_semantic_facts(limit=20)
                if not facts:
                    print("  No semantic facts recorded yet. Chat normally and ARYx will learn.")
                else:
                    render_table(
                        "Learned Semantic Memory",
                        ["ID", "Category", "Learned Fact"],
                        [[str(f["id"]), f["category"], f["fact"]] for f in facts],
                    )
                continue
            elif cmd == "/skills":
                if len(parts) >= 3 and parts[1].lower() == "show":
                    skill_name = parts[2]
                    content = read_skill(skill_name)
                    if content:
                        print(f"\n--- Skill: {skill_name} ---\n{content}\n")
                    else:
                        print(f"  Skill '{skill_name}' not found. Run `/skills` to view list.")
                else:
                    skills = list_skills()
                    if not skills:
                        print("  No skills created yet. Complex successful tasks automatically generate skills.")
                    else:
                        render_table(
                            "Procedural Skills Engine",
                            ["Skill Name", "Version", "Success Rate", "Uses"],
                            [
                                [
                                    s["name"],
                                    f"v{s['version']}",
                                    f"{s['success_rate']}%",
                                    str(s["success_count"] + s["fail_count"]),
                                ]
                                for s in skills
                            ],
                        )
                continue
            elif cmd == "/revert":
                count = 1
                if len(parts) >= 2 and parts[1].isdigit():
                    count = int(parts[1])
                reverted = revert_last_snapshots(count)
                if reverted:
                    print(f"  ✓ Reverted {len(reverted)} file(s):")
                    for r in reverted:
                        print(f"    • {r}")
                else:
                    print("  No recent file snapshots to revert.")
                continue
            elif cmd == "/history":
                query = parts[1] if len(parts) > 1 else ""
                results = search_history(query, limit=5)
                if results:
                    render_table(
                        f"Search History for '{query}'",
                        ["Session", "Role", "Snippet"],
                        [[r["session_id"], r["role"], r["content"][:60]] for r in results],
                    )
                else:
                    print("  No matching conversation logs found.")
                continue
            elif cmd == "/model":
                if len(parts) >= 3 and parts[1].lower() == "use":
                    target_p = parts[2].lower()
                    config["provider"]["active"] = target_p
                    save_config(config)
                    active_provider, p_cfg = get_active_provider_config(config)
                    model_name = p_cfg.get("model", "default")
                    print(f"  ✓ Switched active provider to: {target_p} ({model_name})")
                elif len(parts) >= 2 and parts[1].lower() == "add":
                    first_run_setup()
                    config = load_config()
                    active_provider, p_cfg = get_active_provider_config(config)
                    model_name = p_cfg.get("model", "default")
                else:
                    print(f"\n  Active Provider: [bold cyan]{active_provider}[/bold cyan] ({model_name})")
                    print("  To switch: `/model use <name>` (e.g. `/model use openai`)")
                    print("  To add or update keys: `/model add`\n")
                continue
            elif cmd == "/dashboard":
                disk_stat = shutil.disk_usage(Path.home())
                free_mb = disk_stat.free / (1024 * 1024)
                print("\n=== ARYx AGENT Dashboard ===")
                print(f"  Active Model:       {active_provider} ({model_name})")
                print(f"  Tokens This Session:{session_tokens}")
                print(f"  Memory DB Path:     {MEMORY_DB}")
                print(f"  Free Disk Space:    {free_mb:.1f} MB")
                print(f"  Approval Mode:      {approval_mode}")
                print("============================\n")
                continue
            else:
                print(f"  Unknown command: {cmd}. Type `/help` for available options.")
                continue

        # Extract semantic preferences and save message
        extract_quick_facts(user_input)
        save_message(session_id, "user", user_input)
        history.append({"role": "user", "content": user_input})

        # Agent Reasoning Loop
        tool_call_history: List[Dict[str, Any]] = []
        max_turns = 10
        turn_count = 0

        try:
            provider = get_provider(active_provider, config)
        except Exception as e:
            print(f"\n  ✗ Error loading provider '{active_provider}': {str(e)}")
            print("    Run `aryx doctor` for diagnostics.\n")
            continue

        while turn_count < max_turns:
            turn_count += 1
            try:
                # LLM call
                response = provider.chat(
                    messages=history,
                    tools=TOOL_DEFINITIONS,
                )

                usage = response.get("usage", {})
                turn_tokens = usage.get("total_tokens", 0)
                session_tokens += turn_tokens

                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])

                if content:
                    print_message("assistant", content)
                    save_message(session_id, "assistant", content)

                if not tool_calls:
                    # Final assistant turn done
                    history.append({"role": "assistant", "content": content})
                    break

                # Assistant requested tool calls
                history.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                })

                # Execute requested tools
                for tc in tool_calls:
                    fn_name = tc.get("name", "")
                    fn_args = tc.get("args", {})

                    print_tool_call(fn_name, fn_args)

                    # Approval Check for WRITE tools
                    approved = True
                    if fn_name in WRITE_TOOLS and approval_mode != "yolo":
                        approved = prompt_approval(fn_name, fn_args)

                    if not approved:
                        result = {"error": "Action cancelled by user."}
                        print_tool_result(fn_name, False, "Cancelled by user.")
                    else:
                        try:
                            result = dispatch_tool(
                                fn_name,
                                fn_args,
                                timeout=config.get("general", {}).get("command_timeout", 30),
                            )
                            is_success = "error" not in result and result.get("exit_code", 0) == 0
                            summary_str = f"Done (exit: {result.get('exit_code', 0)})" if "exit_code" in result else "Success"
                            if "error" in result:
                                summary_str = str(result["error"])[:60]

                            print_tool_result(fn_name, is_success, summary_str)
                            tool_call_history.append({"name": fn_name, "args": fn_args, "result": result})
                        except KeyboardInterrupt:
                            print("\n  ! Tool execution interrupted by user (Ctrl+C). Session continues.")
                            result = {"error": "Interrupted by user"}

                    # Append tool result to history
                    history.append({
                        "role": "tool",
                        "name": fn_name,
                        "tool_call_id": tc.get("id", f"call_{uuid.uuid4().hex[:6]}"),
                        "content": str(result),
                    })

                # Reflection checkpoint every 3 steps
                if len(tool_call_history) >= 3 and len(tool_call_history) % 3 == 0:
                    reflection = evaluate_progress(user_input, tool_call_history, len(tool_call_history))
                    if not reflection.get("on_track"):
                        print(f"  [yellow]! Reflection: {reflection.get('reason')}[/yellow]")

            except Exception as e:
                err_text = redact_secrets(str(e))
                print(f"\n  ✗ Something went wrong: {err_text}")
                print("    What to do: Check your network connection or verify configuration.")
                print("    Still stuck? Run: aryx doctor\n")
                break

        # Check for auto-skill generation if task had >5 tools
        if len(tool_call_history) >= 5:
            new_skill = generate_skill_from_run(user_input, tool_call_history)
            if new_skill:
                active_skill = Path(new_skill).stem
                print(f"  [cyan]✓ Auto-generated new procedural skill:[/cyan] {active_skill}")

        # Show status line
        print_status_line(
            model=model_name,
            total_tokens=session_tokens,
            skill_name=active_skill,
        )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context = None,  # type: ignore[assignment]
    yolo: bool = typer.Option(False, "--yolo", help="Run without interactive confirmation for writes and bash"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    banner: bool = typer.Option(False, "--banner", help="Print ARYx banner and exit"),
    version: bool = typer.Option(False, "--version", "-V", help="Print version and exit"),
) -> None:
    """Start interactive ARYx AGENT session (default when no subcommand is given)."""
    # When a subcommand (doctor, config, help, ...) was invoked, the
    # callback still runs first under Typer — hand control to it.
    if ctx is not None and getattr(ctx, "invoked_subcommand", None) is not None:
        return
    if banner:
        print_banner()
        return
    if version:
        print(f"ARYx AGENT v{__version__}")
        return

    start_chat_session(yolo=yolo, verbose=verbose)


@app.command(name="doctor")
def cli_doctor(
    fix: bool = typer.Option(False, "--fix", help="Attempt safe automatic repairs"),
    as_json: bool = typer.Option(False, "--json", help="Output machine-readable JSON for CI"),
) -> None:
    """Diagnose and auto-repair setup and provider issues."""
    exit_code = run_doctor(fix=fix, as_json=as_json)
    if exit_code != 0:
        sys.exit(exit_code)


@app.command(name="config")
def cli_config(
    subcommand: Optional[str] = typer.Argument(None, help="Subcommand (e.g. 'show')"),
) -> None:
    """Manage ARYx configuration (~/.aryx/config.toml)."""
    ensure_aryx_directories()
    if subcommand == "show":
        if not CONFIG_FILE.exists():
            print("Config file not found. Run `aryx` to set up.")
            return

        cfg = load_config()
        # Redact keys before showing
        display_cfg = dict(cfg)
        for p, data in display_cfg.get("providers", {}).items():
            if isinstance(data, dict) and "api_key" in data and data["api_key"]:
                data["api_key"] = redact_key(data["api_key"])

        import pprint
        print("\n--- ~/.aryx/config.toml (Redacted) ---")
        pprint.pprint(display_cfg)
        print("")
        return

    editor = os.environ.get("EDITOR", "nano")
    if not CONFIG_FILE.exists():
        save_config(load_config())

    print(f"Opening {CONFIG_FILE} in {editor}...")
    try:
        subprocess.run([editor, str(CONFIG_FILE)])
    except Exception:
        print(f"Could not open editor. Config file is located at: {CONFIG_FILE}")


@app.command(name="help")
def cli_help(
    topic: str = typer.Argument("general", help="Topic: setup, providers, tools, skills"),
) -> None:
    """Display interactive guides, setup instructions, and reference manuals."""
    show_help(topic)


@app.command(name="update")
def cli_update() -> None:
    """Update ARYx AGENT to the latest release."""
    print("Checking for updates...")
    if shutil.which("pipx"):
        res = subprocess.run(["pipx", "upgrade", "aryx-agent"])
        if res.returncode == 0:
            print("✓ ARYx AGENT updated successfully.")
        else:
            print("Update failed. Run `pipx install --force \"git+https://github.com/fsix7115-arch/ARYX-agent#subdirectory=aryx-agent\"`")
    else:
        print("Run: pip install --upgrade --user aryx-agent")


@app.command(name="uninstall")
def cli_uninstall() -> None:
    """Remove ARYx configuration and binary."""
    confirm = input("Are you sure you want to uninstall ARYx AGENT? [y/N]: ").strip().lower()
    if confirm in ("y", "yes"):
        if shutil.which("pipx"):
            subprocess.run(["pipx", "uninstall", "aryx-agent"])
        print("To delete all memory and skills, remove ~/.aryx: rm -rf ~/.aryx")
        print("✓ ARYx uninstalled.")


def run_cli() -> None:
    """Entry point dispatching either via Typer or built-in argparse."""
    if HAS_REAL_TYPER:
        app()
    else:
        import argparse
        parser = argparse.ArgumentParser(
            prog="aryx",
            description="ARYx AGENT — Zero-friction, self-healing, multi-provider terminal AI agent.",
        )
        parser.add_argument("--yolo", action="store_true", help="Run without confirmations")
        parser.add_argument("--verbose", "-v", action="store_true", help="Verbose mode")
        parser.add_argument("--banner", action="store_true", help="Print banner and exit")
        parser.add_argument("--version", "-V", action="store_true", help="Print version and exit")

        subparsers = parser.add_subparsers(dest="command")

        # doctor
        doc_p = subparsers.add_parser("doctor", help="Run health diagnostics")
        doc_p.add_argument("--fix", action="store_true", help="Auto-repair issues")
        doc_p.add_argument("--json", action="store_true", help="Output JSON")

        # config
        cfg_p = subparsers.add_parser("config", help="Manage config")
        cfg_p.add_argument("subcommand", nargs="?", default=None, help="e.g. 'show'")

        # help
        hlp_p = subparsers.add_parser("help", help="Show guides")
        hlp_p.add_argument("topic", nargs="?", default="general", help="Topic name")

        # update / uninstall
        subparsers.add_parser("update", help="Update ARYx")
        subparsers.add_parser("uninstall", help="Uninstall ARYx")

        args = parser.parse_args()

        if args.banner:
            print_banner()
            return
        if args.version:
            print(f"ARYx AGENT v{__version__}")
            return

        if args.command == "doctor":
            code = run_doctor(fix=args.fix, as_json=args.json)
            if code != 0:
                sys.exit(code)
        elif args.command == "config":
            cli_config(subcommand=args.subcommand)
        elif args.command == "help":
            cli_help(topic=args.topic)
        elif args.command == "update":
            cli_update()
        elif args.command == "uninstall":
            cli_uninstall()
        else:
            main(yolo=args.yolo, verbose=args.verbose, banner=False, version=False)


if __name__ == "__main__":
    run_cli()
