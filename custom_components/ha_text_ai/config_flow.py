"""Config flow for HA text AI integration."""
from typing import Any, Dict, Optional, Tuple
import voluptuous as vol
import asyncio
import aiohttp
from async_timeout import timeout
from urllib.parse import urlparse, urljoin

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
    MIN_REQUEST_INTERVAL,
    API_VERSION,
    API_MODELS_PATH,
    ERROR_INVALID_API_KEY,
    ERROR_CANNOT_CONNECT,
    ERROR_UNKNOWN,
    ERROR_INVALID_MODEL,
    ERROR_RATE_LIMIT,
    ERROR_API_ERROR,
    ERROR_TIMEOUT,
)

import logging
_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_API_KEY): str,
    vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): str,
    vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): float,
    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): int,
    vol.Optional(CONF_API_ENDPOINT, default=DEFAULT_API_ENDPOINT): str,
    vol.Optional(CONF_REQUEST_INTERVAL, default=DEFAULT_REQUEST_INTERVAL): float,
})

# Функция validate_api_connection остается без изменений

class HATextAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA text AI."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Валидация значений
                if not MIN_TEMPERATURE <= user_input[CONF_TEMPERATURE] <= MAX_TEMPERATURE:
                    errors["base"] = "invalid_temperature"
                elif not MIN_MAX_TOKENS <= user_input[CONF_MAX_TOKENS] <= MAX_MAX_TOKENS:
                    errors["base"] = "invalid_max_tokens"
                elif user_input[CONF_REQUEST_INTERVAL] < MIN_REQUEST_INTERVAL:
                    errors["base"] = "invalid_request_interval"
                else:
                    endpoint = user_input[CONF_API_ENDPOINT]
                    try:
                        result = urlparse(endpoint)
                        if not all([result.scheme, result.netloc]):
                            errors["base"] = "invalid_url_format"
                        else:
                            is_valid, error_code, available_models = await validate_api_connection(
                                self.hass,
                                user_input[CONF_API_KEY],
                                endpoint,
                                user_input[CONF_MODEL]
                            )

                            if is_valid:
                                await self.async_set_unique_id(user_input[CONF_API_KEY])
                                self._abort_if_unique_id_configured()
                                return self.async_create_entry(
                                    title="HA Text AI",
                                    data=user_input
                                )
                            errors["base"] = error_code
                            if error_code == ERROR_INVALID_MODEL:
                                _LOGGER.warning(
                                    "Selected model %s not found in available models: %s",
                                    user_input[CONF_MODEL],
                                    ", ".join(available_models)
                                )
                    except Exception as e:
                        _LOGGER.error("URL parsing error: %s", str(e))
                        errors["base"] = "invalid_url_format"

            except Exception as err:
                _LOGGER.error("Validation error: %s", str(err))
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
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            # Validate options values
            errors: Dict[str, str] = {}
            try:
                if not MIN_TEMPERATURE <= user_input[CONF_TEMPERATURE] <= MAX_TEMPERATURE:
                    errors["base"] = "invalid_temperature"
                elif not MIN_MAX_TOKENS <= user_input[CONF_MAX_TOKENS] <= MAX_MAX_TOKENS:
                    errors["base"] = "invalid_max_tokens"
                elif user_input[CONF_REQUEST_INTERVAL] < MIN_REQUEST_INTERVAL:
                    errors["base"] = "invalid_request_interval"
                else:
                    return self.async_create_entry(title="", data=user_input)
            except Exception as err:
                _LOGGER.error("Options validation error: %s", str(err))
                errors["base"] = "unknown"

            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_options_schema(),
                    errors=errors
                )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
        )

    def _get_options_schema(self) -> vol.Schema:
        """Get options schema."""
        return vol.Schema({
            vol.Optional(
                CONF_TEMPERATURE,
                default=self.config_entry.options.get(
                    CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                )
            ): float,
            vol.Optional(
                CONF_MAX_TOKENS,
                default=self.config_entry.options.get(
                    CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                )
            ): int,
            vol.Optional(
                CONF_REQUEST_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL
                )
            ): float
        })
