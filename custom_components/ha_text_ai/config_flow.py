"""Config flow for HA text AI integration."""
from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
import openai

from .const import (
    DOMAIN,
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_MAX_TOKENS,
    CONF_API_ENDPOINT,
    CONF_REQUEST_INTERVAL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_API_ENDPOINT,
    DEFAULT_REQUEST_INTERVAL,
)

import logging
_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_API_KEY): str,
    vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): str,
    vol.Optional(
        CONF_TEMPERATURE,
        default=DEFAULT_TEMPERATURE
    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=2)),
    vol.Optional(
        CONF_MAX_TOKENS,
        default=DEFAULT_MAX_TOKENS
    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=4096)),
    vol.Optional(CONF_API_ENDPOINT, default=DEFAULT_API_ENDPOINT): str,
    vol.Optional(
        CONF_REQUEST_INTERVAL,
        default=DEFAULT_REQUEST_INTERVAL
    ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
})

class HATextAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA text AI."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Create OpenAI client
                client = openai.OpenAI(
                    api_key=user_input[CONF_API_KEY],
                    base_url=user_input.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT)
                )

                # Verify API connection and model availability
                models = await self.hass.async_add_executor_job(client.models.list)
                model_ids = [model.id for model in models.data]

                if user_input[CONF_MODEL] not in model_ids:
                    _LOGGER.warning(
                        "Selected model %s not found in available models: %s",
                        user_input[CONF_MODEL],
                        ", ".join(model_ids)
                    )
                    errors["base"] = "invalid_model"
                else:
                    await self.async_set_unique_id(user_input[CONF_API_KEY])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title="HA text AI",
                        data=user_input
                    )

            except openai.AuthenticationError as err:
                _LOGGER.error("Authentication failed: %s", str(err))
                errors["base"] = "invalid_auth"
            except openai.APIError as err:
                _LOGGER.error("API connection failed: %s", str(err))
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error: %s", str(err))
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "default_model": DEFAULT_MODEL,
                "default_endpoint": DEFAULT_API_ENDPOINT,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for HA text AI."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                CONF_TEMPERATURE,
                default=self.config_entry.options.get(
                    CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                ),
                description={"suggested_value": DEFAULT_TEMPERATURE},
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=2)),
            vol.Optional(
                CONF_MAX_TOKENS,
                default=self.config_entry.options.get(
                    CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                ),
                description={"suggested_value": DEFAULT_MAX_TOKENS},
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=4096)),
            vol.Optional(
                CONF_REQUEST_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL
                ),
                description={"suggested_value": DEFAULT_REQUEST_INTERVAL},
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
