"""Tests for conversation message building.

Tests _build_messages logic with fake ChatLog objects,
avoiding homeassistant dependency entirely.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import pytest

_COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "hearth_conversation"


def _load(name: str) -> ModuleType:
    full_name = f"custom_components.hearth_conversation.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(full_name, _COMPONENT_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


_const = _load("const")
DEFAULT_SYSTEM_PROMPT = _const.DEFAULT_SYSTEM_PROMPT


@dataclass
class FakeChatContent:
    role: str
    content: str | None = None


@dataclass
class FakeChatLog:
    content: list[FakeChatContent] = field(default_factory=list)


def _build_messages(chat_log, system_prompt: str, max_history: int):
    """Mirror of HearthConversationEntity._build_messages logic."""
    messages = [{"role": "system", "content": system_prompt}]
    history = []
    for entry in chat_log.content:
        if entry.role == "user":
            history.append({"role": "user", "content": entry.content})
        elif entry.role == "assistant" and entry.content:
            history.append({"role": "assistant", "content": entry.content})
    if max_history > 0:
        history = history[-max_history:]
    messages.extend(history)
    return messages


class TestBuildMessages:

    def test_empty_log(self) -> None:
        messages = _build_messages(FakeChatLog(), DEFAULT_SYSTEM_PROMPT, 10)
        assert len(messages) == 1
        assert messages[0]["role"] == "system"

    def test_single_user_message(self) -> None:
        chat_log = FakeChatLog(content=[
            FakeChatContent(role="system", content=""),
            FakeChatContent(role="user", content="What's the weather?"),
        ])
        messages = _build_messages(chat_log, "Be brief.", 10)
        assert len(messages) == 2
        assert messages[1] == {"role": "user", "content": "What's the weather?"}

    def test_multi_turn(self) -> None:
        chat_log = FakeChatLog(content=[
            FakeChatContent(role="system", content=""),
            FakeChatContent(role="user", content="Hello"),
            FakeChatContent(role="assistant", content="Hi there!"),
            FakeChatContent(role="user", content="How are you?"),
        ])
        messages = _build_messages(chat_log, "System.", 10)
        assert len(messages) == 4
        assert messages[1]["content"] == "Hello"
        assert messages[2]["content"] == "Hi there!"
        assert messages[3]["content"] == "How are you?"

    def test_truncation(self) -> None:
        entries = [FakeChatContent(role="system", content="")]
        for i in range(20):
            entries.append(FakeChatContent(role="user", content=f"Msg {i}"))
            entries.append(FakeChatContent(role="assistant", content=f"Reply {i}"))

        messages = _build_messages(FakeChatLog(content=entries), "Sys.", 4)
        # 1 system + 4 truncated history
        assert len(messages) == 5
        assert messages[-1]["content"] == "Reply 19"

    def test_zero_history_keeps_all(self) -> None:
        chat_log = FakeChatLog(content=[
            FakeChatContent(role="user", content="Hello"),
            FakeChatContent(role="assistant", content="Hi"),
        ])
        messages = _build_messages(chat_log, "Sys.", 0)
        assert len(messages) == 3

    def test_skips_tool_and_system(self) -> None:
        chat_log = FakeChatLog(content=[
            FakeChatContent(role="system", content="Original"),
            FakeChatContent(role="user", content="Do something"),
            FakeChatContent(role="tool_result", content="tool output"),
            FakeChatContent(role="assistant", content="Done!"),
        ])
        messages = _build_messages(chat_log, "My system.", 10)
        assert len(messages) == 3
        assert messages[1]["content"] == "Do something"
        assert messages[2]["content"] == "Done!"

    def test_skips_assistant_without_content(self) -> None:
        chat_log = FakeChatLog(content=[
            FakeChatContent(role="user", content="Hi"),
            FakeChatContent(role="assistant", content=None),
            FakeChatContent(role="assistant", content="Hello!"),
        ])
        messages = _build_messages(chat_log, "Sys.", 10)
        assert len(messages) == 3
        assert messages[2]["content"] == "Hello!"
