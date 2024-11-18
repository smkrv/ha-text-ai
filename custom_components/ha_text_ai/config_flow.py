"""Config flow for HA text AI integration."""
import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback

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

class HATextAIConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for HA text AI."""

    VERSION = 1
    DOMAIN = DOMAIN  # Define the domain as a class variable

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="HA text AI", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
                vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): str,
                vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.Coerce(float),
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.Coerce(int),
                vol.Optional(CONF_API_ENDPOINT, default=DEFAULT_API_ENDPOINT): str,
                vol.Optional(CONF_REQUEST_INTERVAL, default=DEFAULT_REQUEST_INTERVAL): vol.Coerce(float),
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for HA text AI."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=self.config_entry.options.get(
                        CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_MAX_TOKENS,
                    default=self.config_entry.options.get(
                        CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_REQUEST_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL
                    ),
                ): vol.Coerce(float),
            }),
        )
