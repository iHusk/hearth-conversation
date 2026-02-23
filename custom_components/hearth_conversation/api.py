"""HTTP client for the OpenClaw gateway API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class OpenClawAuthError(Exception):
    """Raised on 401/403 from the gateway."""


class OpenClawConnectionError(Exception):
    """Raised when the gateway is unreachable."""


class OpenClawTimeoutError(Exception):
    """Raised when the gateway doesn't respond in time."""


class OpenClawApiClient:
    """Async client for the OpenClaw OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        verify_ssl: bool = True,
        timeout: int = 30,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = session
        self._owned_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._verify_ssl)
            self._session = aiohttp.ClientSession(
                connector=connector, timeout=self._timeout
            )
            self._owned_session = True
        return self._session

    async def close(self) -> None:
        """Close the underlying session if we own it."""
        if self._owned_session and self._session and not self._session.closed:
            await self._session.close()

    async def validate_connection(self) -> bool:
        """Check connectivity by hitting GET /v1/models."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._base_url}/v1/models", headers=self._headers
            ) as resp:
                if resp.status in (401, 403):
                    raise OpenClawAuthError("Invalid API key or token")
                resp.raise_for_status()
                return True
        except OpenClawAuthError:
            raise
        except asyncio.TimeoutError as err:
            raise OpenClawTimeoutError("Connection timed out") from err
        except aiohttp.ClientError as err:
            raise OpenClawConnectionError(f"Cannot reach gateway: {err}") from err

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        agent_id: str = "main",
    ) -> str:
        """Send a chat completion request and return the assistant message."""
        session = await self._get_session()
        payload: dict[str, Any] = {
            "model": agent_id,
            "messages": messages,
            "stream": False,
        }
        try:
            async with session.post(
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
            ) as resp:
                if resp.status in (401, 403):
                    raise OpenClawAuthError("Invalid API key or token")
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
        except OpenClawAuthError:
            raise
        except asyncio.TimeoutError as err:
            raise OpenClawTimeoutError("Request timed out") from err
        except aiohttp.ClientError as err:
            raise OpenClawConnectionError(f"Gateway error: {err}") from err

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        agent_id: str = "main",
    ) -> str:
        """Send a streaming chat completion and collect the full response."""
        session = await self._get_session()
        payload: dict[str, Any] = {
            "model": agent_id,
            "messages": messages,
            "stream": True,
        }
        try:
            async with session.post(
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
            ) as resp:
                if resp.status in (401, 403):
                    raise OpenClawAuthError("Invalid API key or token")
                resp.raise_for_status()
                chunks: list[str] = []
                async for line in resp.content:
                    decoded = line.decode("utf-8").strip()
                    if not decoded.startswith("data: "):
                        continue
                    data_str = decoded[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if content := delta.get("content"):
                            chunks.append(content)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                return "".join(chunks)
        except OpenClawAuthError:
            raise
        except asyncio.TimeoutError as err:
            raise OpenClawTimeoutError("Stream timed out") from err
        except aiohttp.ClientError as err:
            raise OpenClawConnectionError(f"Stream error: {err}") from err
