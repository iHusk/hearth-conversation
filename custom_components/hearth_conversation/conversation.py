"""Conversation agent for Hearth (OpenClaw gateway)."""

from __future__ import annotations

import logging
from typing import Literal

from homeassistant.components.conversation import (
    ChatLog,
    ConversationEntity,
    ConversationResult,
)
from homeassistant.components.conversation.chat_log import AssistantContent
from homeassistant.components.conversation.models import ConversationInput
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HearthConversationConfigEntry
from .api import OpenClawApiClient, OpenClawAuthError, OpenClawConnectionError, OpenClawTimeoutError
from .const import (
    CONF_AGENT_ID,
    CONF_MAX_HISTORY,
    CONF_MODEL_OVERRIDE,
    CONF_SYSTEM_PROMPT,
    DEFAULT_AGENT_ID,
    DEFAULT_MAX_HISTORY,
    DEFAULT_SYSTEM_PROMPT,
    DOMAIN,
    ERROR_AUTH,
    ERROR_TIMEOUT,
    ERROR_UNKNOWN,
    ERROR_UNREACHABLE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HearthConversationConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the conversation entity."""
    async_add_entities([HearthConversationEntity(entry)])


class HearthConversationEntity(ConversationEntity):
    """Conversation agent that talks to OpenClaw."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: HearthConversationConfigEntry) -> None:
        """Initialize the entity."""
        self._entry = entry
        self._client: OpenClawApiClient = entry.runtime_data
        agent_id = entry.data.get(CONF_AGENT_ID, DEFAULT_AGENT_ID)
        self._attr_unique_id = f"{entry.entry_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"OpenClaw ({agent_id})",
            "manufacturer": "Hearth",
            "model": "OpenClaw Gateway",
        }

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
        chat_log: ChatLog,
    ) -> ConversationResult:
        """Process a message through OpenClaw."""
        system_prompt = self._entry.options.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
        max_history = self._entry.options.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY)
        model_override = self._entry.options.get(CONF_MODEL_OVERRIDE, "")
        agent_id = self._entry.data.get(CONF_AGENT_ID, DEFAULT_AGENT_ID)
        model = self._resolve_model(model_override, agent_id)

        messages = self._build_messages(chat_log, system_prompt, max_history)

        try:
            response_text = await self._client.chat_completion(
                messages=messages,
                agent_id=model,
            )
        except OpenClawAuthError:
            _LOGGER.error("Authentication failed with OpenClaw gateway")
            response_text = ERROR_AUTH
        except OpenClawConnectionError:
            _LOGGER.error("Cannot reach OpenClaw gateway")
            response_text = ERROR_UNREACHABLE
        except OpenClawTimeoutError:
            _LOGGER.warning("OpenClaw gateway timed out")
            response_text = ERROR_TIMEOUT
        except Exception:
            _LOGGER.exception("Unexpected error from OpenClaw")
            response_text = ERROR_UNKNOWN

        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=response_text)
        )

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(response_text)

        return ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )

    @staticmethod
    def _resolve_model(model_override: str, agent_id: str) -> str:
        """Resolve the model string for the OpenClaw API.

        OpenClaw's chatCompletions endpoint uses the model field to route:
        - Agent names need "agent:" prefix (e.g. "voice" → "agent:voice")
        - Full model refs like "openai-codex/gpt-5.2-codex" pass through as-is
        - The default agent_id also gets the "agent:" prefix
        """
        raw = model_override.strip() if model_override else ""
        if not raw:
            return f"agent:{agent_id}"
        # Already has a routing prefix or looks like a provider/model ref
        if "/" in raw or raw.startswith("agent:") or raw.startswith("openclaw/"):
            return raw
        # Bare name — treat as agent ID
        return f"agent:{raw}"

    @staticmethod
    def _build_messages(
        chat_log: ChatLog,
        system_prompt: str,
        max_history: int,
    ) -> list[dict[str, str]]:
        """Convert ChatLog to OpenAI-format messages with truncation."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Extract user and assistant messages from the chat log
        history: list[dict[str, str]] = []
        for entry in chat_log.content:
            if entry.role == "user":
                history.append({"role": "user", "content": entry.content})
            elif entry.role == "assistant" and entry.content:
                history.append({"role": "assistant", "content": entry.content})

        # Keep only the last N messages
        if max_history > 0:
            history = history[-max_history:]

        messages.extend(history)
        return messages
