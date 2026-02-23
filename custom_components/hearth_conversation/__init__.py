"""The Hearth Conversation integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api import OpenClawApiClient, OpenClawAuthError, OpenClawConnectionError, OpenClawTimeoutError
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_TIMEOUT,
    CONF_VERIFY_SSL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CONVERSATION]

type HearthConversationConfigEntry = ConfigEntry[OpenClawApiClient]


async def async_setup_entry(
    hass: HomeAssistant, entry: HearthConversationConfigEntry
) -> bool:
    """Set up Hearth Conversation from a config entry."""
    client = OpenClawApiClient(
        base_url=entry.data[CONF_BASE_URL],
        api_key=entry.data[CONF_API_KEY],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, True),
        timeout=entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
    )

    try:
        await client.validate_connection()
    except OpenClawAuthError as err:
        await client.close()
        raise ConfigEntryAuthFailed("Invalid API key") from err
    except (OpenClawConnectionError, OpenClawTimeoutError) as err:
        await client.close()
        raise ConfigEntryNotReady("Cannot reach OpenClaw gateway") from err

    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: HearthConversationConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.close()
    return unload_ok
