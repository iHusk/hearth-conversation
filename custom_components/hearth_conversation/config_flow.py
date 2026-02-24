"""Config flow for Hearth Conversation."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .api import OpenClawApiClient, OpenClawAuthError, OpenClawConnectionError, OpenClawTimeoutError
from .const import (
    CONF_AGENT_ID,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MAX_HISTORY,
    CONF_MODEL_OVERRIDE,
    CONF_SYSTEM_PROMPT,
    CONF_TIMEOUT,
    CONF_VERIFY_SSL,
    DEFAULT_AGENT_ID,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_HISTORY,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
        vol.Optional(CONF_AGENT_ID, default=DEFAULT_AGENT_ID): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SYSTEM_PROMPT, default=DEFAULT_SYSTEM_PROMPT): str,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            int, vol.Range(min=5, max=120)
        ),
        vol.Optional(CONF_MAX_HISTORY, default=DEFAULT_MAX_HISTORY): vol.All(
            int, vol.Range(min=0, max=50)
        ),
    }
)


class HearthConversationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hearth Conversation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = OpenClawApiClient(
                base_url=user_input[CONF_BASE_URL],
                api_key=user_input[CONF_API_KEY],
                verify_ssl=user_input.get(CONF_VERIFY_SSL, True),
            )
            try:
                await client.validate_connection()
            except OpenClawAuthError:
                errors["base"] = "invalid_auth"
            except OpenClawConnectionError:
                errors["base"] = "cannot_connect"
            except OpenClawTimeoutError:
                errors["base"] = "timeout"
            except Exception:
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_BASE_URL]}_{user_input[CONF_AGENT_ID]}"
                )
                self._abort_if_unique_id_configured()
                agent_id = user_input.get(CONF_AGENT_ID, DEFAULT_AGENT_ID)
                return self.async_create_entry(
                    title=f"OpenClaw ({agent_id})",
                    data=user_input,
                )
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow."""
        return HearthOptionsFlow()


class HearthOptionsFlow(OptionsFlow):
    """Handle options for Hearth Conversation."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MODEL_OVERRIDE,
                        default=self.config_entry.options.get(
                            CONF_MODEL_OVERRIDE, ""
                        ),
                    ): str,
                    vol.Optional(
                        CONF_SYSTEM_PROMPT,
                        default=self.config_entry.options.get(
                            CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT
                        ),
                    ): str,
                    vol.Optional(
                        CONF_TIMEOUT,
                        default=self.config_entry.options.get(
                            CONF_TIMEOUT, DEFAULT_TIMEOUT
                        ),
                    ): vol.All(int, vol.Range(min=5, max=120)),
                    vol.Optional(
                        CONF_MAX_HISTORY,
                        default=self.config_entry.options.get(
                            CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY
                        ),
                    ): vol.All(int, vol.Range(min=0, max=50)),
                }
            ),
        )
