"""Config flow for HA text AI integration."""
from typing import Any, Dict, Optional, Tuple
import voluptuous as vol
import asyncio
from async_timeout import timeout
import aiohttp
from urllib.parse import urlparse

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from openai import AsyncOpenAI
from openai import OpenAIError, APIError, APIConnectionError, AuthenticationError, RateLimitError

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
    ): vol.All(
        vol.Coerce(float),
        vol.Range(min=0, max=2)
    ),
    vol.Optional(
        CONF_MAX_TOKENS,
        default=DEFAULT_MAX_TOKENS
    ): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=4096)
    ),
    vol.Optional(CONF_API_ENDPOINT, default=DEFAULT_API_ENDPOINT): str,
    vol.Optional(
        CONF_REQUEST_INTERVAL,
        default=DEFAULT_REQUEST_INTERVAL
    ): vol.All(
        vol.Coerce(float),
        vol.Range(min=0.1)
    ),
})

async def async_create_client(
    hass,
    api_key: str,
    endpoint: str,
) -> AsyncOpenAI:
    """Create AsyncOpenAI client with proper session."""
    session = async_get_clientsession(hass)
    return AsyncOpenAI(
        api_key=api_key,
        base_url=endpoint,
        http_client=session
    )

async def validate_api_connection(
    hass,
    api_key: str,
    endpoint: str,
    model: str,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Tuple[bool, str, list]:
    """Validate API connection with retry logic."""
    for attempt in range(retry_count):
        try:
            async with timeout(10):
                client = await async_create_client(hass, api_key, endpoint)
                models = await client.models.list()
                model_ids = [model.id for model in models.data]

                if model not in model_ids:
                    _LOGGER.warning(
                        "Model %s not found in available models: %s",
                        model,
                        ", ".join(model_ids)
                    )
                    return False, "invalid_model", model_ids
                return True, "", model_ids

        except asyncio.TimeoutError:
            _LOGGER.warning(
                "Timeout during API validation (attempt %d/%d)",
                attempt + 1,
                retry_count
            )
            if attempt == retry_count - 1:
                return False, "timeout", []
            await asyncio.sleep(retry_delay)

        except AuthenticationError as err:
            _LOGGER.error("Authentication error: %s", str(err))
            return False, "invalid_auth", []

        except RateLimitError as err:
            _LOGGER.error("Rate limit exceeded: %s", str(err))
            return False, "rate_limit", []

        except APIConnectionError as err:
            _LOGGER.error("API connection error: %s", str(err))
            return False, "cannot_connect", []

        except APIError as err:
            _LOGGER.error("API error: %s", str(err))
            return False, "api_error", []

        except Exception as err:
            _LOGGER.exception("Unexpected error during validation: %s", str(err))
            return False, "unknown", []

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
                # Validate URL format
                endpoint = user_input.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT)
                try:
                    result = urlparse(endpoint)
                    if not all([result.scheme, result.netloc]):
                        errors["base"] = "invalid_url_format"
                        return self.async_show_form(
                            step_id="user",
                            data_schema=STEP_USER_DATA_SCHEMA,
                            errors=errors
                        )
                except Exception as e:
                    _LOGGER.error("URL parsing error: %s", str(e))
                    errors["base"] = "invalid_url_format"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=STEP_USER_DATA_SCHEMA,
                        errors=errors
                    )

                # Validate input data
                user_input = STEP_USER_DATA_SCHEMA(user_input)

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
                        title="HA text AI",
                        data=user_input
                    )

                errors["base"] = error_code
                if error_code == "invalid_model":
                    _LOGGER.warning(
                        "Selected model %s not found in available models: %s",
                        user_input[CONF_MODEL],
                        ", ".join(available_models)
                    )

            except vol.Invalid as err:
                _LOGGER.error("Validation error: %s", str(err))
                errors["base"] = "invalid_input"

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
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=0, max=2)
            ),
            vol.Optional(
                CONF_MAX_TOKENS,
                default=self.config_entry.options.get(
                    CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                ),
                description={"suggested_value": DEFAULT_MAX_TOKENS},
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=1, max=4096)
            ),
            vol.Optional(
                CONF_REQUEST_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL
                ),
                description={"suggested_value": DEFAULT_REQUEST_INTERVAL},
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=0.1)
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
