"""
ARYx AGENT - Gateway agent-runner tests (Section 16.9).

The LLM is faked, so these tests prove the loop itself: plain
replies pass through, read-only tools run immediately, and write
tools PAUSE for approval and only run after an explicit approve.
"""

import threading

from aryx.gateway.agent import AgentRunner


class FakeProvider:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def chat(self, messages, tools=None, temperature=0.4):
        self.calls += 1
        return self.script.pop(0)


def _runner(monkeypatch, provider, dispatched):
    monkeypatch.setattr(
        "aryx.config.load_config",
        lambda: {"provider": {"active": "openai"}, "providers": {"openai": {"api_key": "sk-test", "model": "gpt-x"}}, "general": {"command_timeout": 30}},
    )
    monkeypatch.setattr(
        "aryx.config.get_active_provider_config",
        lambda cfg=None: ("openai", {"api_key": "sk-test", "model": "gpt-x"}),
    )
    monkeypatch.setattr("aryx.providers.get_provider", lambda name, cfg: provider)
    monkeypatch.setattr("aryx.tools.dispatch_tool", lambda name, args, timeout=30: dispatched.append((name, args)) or {"ok": True})
    return AgentRunner()


def test_plain_reply(monkeypatch):
    provider = FakeProvider([{"content": "hello back", "tool_calls": []}])
    dispatched = []
    runner = _runner(monkeypatch, provider, dispatched)
    result = runner.start_turn(history=[], user_text="hi", approval_mode="safe")
    assert result.kind == "reply" and result.text == "hello back"
    assert dispatched == []


def test_read_only_tool_runs_immediately(monkeypatch):
    provider = FakeProvider([
        {"content": "", "tool_calls": [{"name": "read_file", "args": {"path": "/tmp/a.txt"}, "id": "c1"}]},
        {"content": "the file says hi", "tool_calls": []},
    ])
    dispatched = []
    runner = _runner(monkeypatch, provider, dispatched)
    result = runner.start_turn(history=[], user_text="read it", approval_mode="safe")
    assert result.kind == "reply" and result.text == "the file says hi"
    assert dispatched == [("read_file", {"path": "/tmp/a.txt"})]


def test_write_tool_pauses_until_approved(monkeypatch):
    provider = FakeProvider([
        {"content": "", "tool_calls": [{"name": "write_file", "args": {"path": "/tmp/x.txt"}, "id": "c1"}]},
        {"content": "written", "tool_calls": []},
    ])
    dispatched = []
    runner = _runner(monkeypatch, provider, dispatched)
    paused = runner.start_turn(history=[], user_text="write it", approval_mode="safe")
    assert paused.kind == "approval"
    assert paused.approval.tool_name == "write_file"
    assert dispatched == []  # Nothing ran before approval.
    done = paused.continuation.resolve(True)
    assert done.kind == "reply" and done.text == "written"
    assert dispatched == [("write_file", {"path": "/tmp/x.txt"})]


def test_write_tool_cancelled_on_reject(monkeypatch):
    provider = FakeProvider([
        {"content": "", "tool_calls": [{"name": "write_file", "args": {"path": "/tmp/x.txt"}, "id": "c1"}]},
        {"content": "ok, skipped it", "tool_calls": []},
    ])
    dispatched = []
    runner = _runner(monkeypatch, provider, dispatched)
    paused = runner.start_turn(history=[], user_text="write it", approval_mode="safe")
    done = paused.continuation.resolve(False)
    assert done.kind == "reply"
    assert dispatched == []  # Rejected = never executed.
