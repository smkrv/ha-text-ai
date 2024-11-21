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

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): cv.string,
        vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
            vol.Coerce(float),
            vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
        ),
        vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
        ),
        vol.Optional(CONF_API_ENDPOINT, default=DEFAULT_API_ENDPOINT): vol.All(
            cv.string,
            vol.Match(r'^https?://.+', msg="Must be a valid HTTP(S) URL")
        ),
        vol.Optional(CONF_REQUEST_INTERVAL, default=DEFAULT_REQUEST_INTERVAL): vol.All(
            vol.Coerce(float),
            vol.Range(min=MIN_REQUEST_INTERVAL)
        )
    }
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
    session = async_get_clientsession(hass)

    # Determine API type and configure headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Configure endpoint and headers based on service type
    if "vsegpt" in endpoint.lower():
        headers["Authorization"] = f"Bearer {api_key}"
        base_url = endpoint.rstrip('/')
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        models_url = f"{base_url}/models"  # Using the correct v1/models endpoint
        _LOGGER.debug("Using VSE GPT endpoint: %s", models_url)

        # For VSE GPT, we might want to validate the model differently
        supported_models = [
            "anthropic/claude-3-5-haiku",
            "anthropic/claude-3.5-sonnet",
            # Add other supported VSE GPT models here
        ]

        if model in supported_models:
            return True, "", supported_models

    elif any(m in model.lower() for m in ["claude", "anthropic"]):
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        base_url = endpoint.rstrip('/')
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        models_url = f"{base_url}/models"
        _LOGGER.debug("Using Anthropic endpoint: %s", models_url)
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        base_url = endpoint.rstrip('/')
        if not base_url.endswith(f"/{API_VERSION}"):
            base_url = f"{base_url}/{API_VERSION}"
        models_url = f"{base_url}/{API_MODELS_PATH}"
        _LOGGER.debug("Using OpenAI endpoint: %s", models_url)

    for attempt in range(retry_count):
        try:
            async with timeout(10):
                # For VSE GPT, we'll skip the actual models endpoint check
                if "vsegpt" in endpoint.lower():
                    # Instead, let's verify the API key with a simple request
                    test_url = f"{base_url}/models"
                    async with session.get(test_url, headers=headers) as response:
                        if response.status == 404:
                            # This is actually expected for VSE GPT
                            if model.startswith("anthropic/"):
                                return True, "", [model]
                        elif response.status == 401:
                            return False, ERROR_INVALID_API_KEY, []
                        elif response.status == 429:
                            return False, ERROR_RATE_LIMIT, []
                    return True, "", [model]

                # For other APIs, proceed with normal validation
                async with session.get(models_url, headers=headers) as response:
                    _LOGGER.debug("API response status: %s", response.status)

                    if response.status == 200:
                        data = await response.json()

                        if any(m in model.lower() for m in ["claude", "anthropic"]):
                            model_ids = [m["id"] for m in data.get("models", [])]
                            if model.startswith("anthropic/"):
                                model = model.split("/")[1]
                            if model in model_ids or any(m.endswith(model) for m in model_ids):
                                return True, "", model_ids
                        else:  # OpenAI format
                            model_ids = [m["id"] for m in data.get("data", [])]
                            if model in model_ids:
                                return True, "", model_ids

                        _LOGGER.warning(
                            "Model %s not found in available models: %s",
                            model,
                            ", ".join(model_ids)
                        )
                        return False, ERROR_INVALID_MODEL, model_ids

                    elif response.status == 401:
                        _LOGGER.error("Authentication failed")
                        return False, ERROR_INVALID_API_KEY, []

                    elif response.status == 429:
                        _LOGGER.error("Rate limit exceeded")
                        if attempt < retry_count - 1:
                            await asyncio.sleep(retry_delay * (2 ** attempt))
                            continue
                        return False, ERROR_RATE_LIMIT, []

                    else:
                        response_text = await response.text()
                        _LOGGER.error(
                            "API error: %s - %s",
                            response.status,
                            response_text
                        )
                        if attempt < retry_count - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        return False, ERROR_API_ERROR, []

        except asyncio.TimeoutError:
            _LOGGER.warning(
                "Timeout during API validation (attempt %d/%d)",
                attempt + 1,
                retry_count
            )
            if attempt < retry_count - 1:
                await asyncio.sleep(retry_delay)
                continue
            return False, ERROR_TIMEOUT, []

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error: %s", str(err))
            return False, ERROR_CANNOT_CONNECT, []

        except Exception as err:
            _LOGGER.exception("Unexpected error during validation: %s", str(err))
            return False, ERROR_UNKNOWN, []

    return False, ERROR_UNKNOWN, []

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

                validated_input = STEP_USER_DATA_SCHEMA(user_input)

                is_valid, error_code, available_models = await validate_api_connection(
                    self.hass,
                    validated_input[CONF_API_KEY],
                    endpoint,
                    validated_input[CONF_MODEL]
                )

                if is_valid:
                    await self.async_set_unique_id(validated_input[CONF_API_KEY])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title="HA Text AI",
                        data=validated_input
                    )

                errors["base"] = error_code
                if error_code == ERROR_INVALID_MODEL:
                    _LOGGER.warning(
                        "Selected model %s not found in available models: %s",
                        validated_input[CONF_MODEL],
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
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                CONF_TEMPERATURE,
                default=self.config_entry.options.get(
                    CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                ),
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
            ),
            vol.Optional(
                CONF_MAX_TOKENS,
                default=self.config_entry.options.get(
                    CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
            ),
            vol.Optional(
                CONF_REQUEST_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL
                ),
            ): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_REQUEST_INTERVAL)
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
