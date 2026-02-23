"""Tests for the OpenClaw API client."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# Direct module loading — bypasses __init__.py (which needs homeassistant)
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
_api = _load("api")

OpenClawApiClient = _api.OpenClawApiClient
OpenClawAuthError = _api.OpenClawAuthError
OpenClawConnectionError = _api.OpenClawConnectionError
OpenClawTimeoutError = _api.OpenClawTimeoutError


@pytest.fixture
def client() -> OpenClawApiClient:
    """Return a fresh API client."""
    return OpenClawApiClient(
        base_url="https://test.example.com",
        api_key="test-token",
        verify_ssl=False,
        timeout=5,
    )


def _mock_cm(mock_resp):
    """Create an async context manager returning mock_resp."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestValidateConnection:
    """Tests for validate_connection."""

    @pytest.mark.asyncio
    async def test_success(self, client) -> None:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_cm(mock_resp))

        with patch.object(client, "_get_session", return_value=mock_session):
            assert await client.validate_connection() is True

    @pytest.mark.asyncio
    async def test_auth_error_401(self, client) -> None:
        mock_resp = AsyncMock()
        mock_resp.status = 401

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_cm(mock_resp))

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(OpenClawAuthError):
                await client.validate_connection()

    @pytest.mark.asyncio
    async def test_auth_error_403(self, client) -> None:
        mock_resp = AsyncMock()
        mock_resp.status = 403

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=_mock_cm(mock_resp))

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(OpenClawAuthError):
                await client.validate_connection()

    @pytest.mark.asyncio
    async def test_timeout(self, client) -> None:
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(OpenClawTimeoutError):
                await client.validate_connection()

    @pytest.mark.asyncio
    async def test_connection_error(self, client) -> None:
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("refused"))

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(OpenClawConnectionError):
                await client.validate_connection()


class TestChatCompletion:
    """Tests for chat_completion."""

    @pytest.mark.asyncio
    async def test_success(self, client) -> None:
        response_data = {"choices": [{"message": {"content": "Hello!"}}]}
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(return_value=response_data)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=_mock_cm(mock_resp))

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                agent_id="main",
            )
        assert result == "Hello!"

    @pytest.mark.asyncio
    async def test_auth_error(self, client) -> None:
        mock_resp = AsyncMock()
        mock_resp.status = 403

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=_mock_cm(mock_resp))

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(OpenClawAuthError):
                await client.chat_completion(
                    messages=[{"role": "user", "content": "Hi"}],
                )


class AsyncIteratorMock:
    """Mock for async iterating over response content."""

    def __init__(self, items: list[bytes]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


class TestChatCompletionStream:
    """Tests for SSE streaming."""

    @pytest.mark.asyncio
    async def test_parses_sse_chunks(self, client) -> None:
        sse_lines = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = AsyncIteratorMock(sse_lines)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=_mock_cm(mock_resp))

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.chat_completion_stream(
                messages=[{"role": "user", "content": "Hi"}],
            )
        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_skips_malformed_lines(self, client) -> None:
        sse_lines = [
            b'\n',
            b'event: ping\n',
            b'data: not-json\n',
            b'data: {"choices":[{"delta":{"content":"OK"}}]}\n',
            b'data: [DONE]\n',
        ]
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = AsyncIteratorMock(sse_lines)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=_mock_cm(mock_resp))

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.chat_completion_stream(
                messages=[{"role": "user", "content": "Hi"}],
            )
        assert result == "OK"
