"""
Config flow for HA text AI integration.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_MAX_TOKENS,
    CONF_API_ENDPOINT,
    CONF_REQUEST_INTERVAL,
    CONF_API_PROVIDER,
    CONF_CONTEXT_MESSAGES,
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_DEEPSEEK,
    API_PROVIDER_GEMINI,
    API_PROVIDERS,
    DEFAULT_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_OPENAI_ENDPOINT,
    DEFAULT_ANTHROPIC_ENDPOINT,
    DEFAULT_DEEPSEEK_ENDPOINT,
    DEFAULT_GEMINI_ENDPOINT,
    DEFAULT_CONTEXT_MESSAGES,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
    MIN_REQUEST_INTERVAL,
    DEFAULT_NAME_PREFIX,
    DEFAULT_MAX_HISTORY,
    CONF_MAX_HISTORY_SIZE,
)

_LOGGER = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize name to conform to HA naming convention using underscores."""
    normalized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
    normalized = '_'.join(filter(None, normalized.split('_')))
    return normalized.lower()


class HATextAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA text AI."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._errors = {}
        self._data = {}
        self._provider = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_API_PROVIDER): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=API_PROVIDERS,
                            translation_key="api_provider"
                        )
                    ),
                })
            )

        self._provider = user_input[CONF_API_PROVIDER]
        return await self.async_step_provider()

    async def async_step_provider(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle provider configuration step."""
        self._errors = {}

        if user_input is None:
            # Selecting an endpoint by provider
            default_endpoint = {
                API_PROVIDER_OPENAI: DEFAULT_OPENAI_ENDPOINT,
                API_PROVIDER_ANTHROPIC: DEFAULT_ANTHROPIC_ENDPOINT,
                API_PROVIDER_DEEPSEEK: DEFAULT_DEEPSEEK_ENDPOINT,
                API_PROVIDER_GEMINI: DEFAULT_GEMINI_ENDPOINT,
            }.get(self._provider, DEFAULT_OPENAI_ENDPOINT)

            # Selecting the default model by provider
            default_model = (
                DEFAULT_DEEPSEEK_MODEL if self._provider == API_PROVIDER_DEEPSEEK else
                DEFAULT_GEMINI_MODEL if self._provider == API_PROVIDER_GEMINI else
                DEFAULT_MODEL
            )

            return self.async_show_form(
                step_id="provider",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME, default="my_assistant"): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_MODEL, default=default_model): str,
                    vol.Required(CONF_API_ENDPOINT, default=default_endpoint): str,
                    vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
                    ),
                    vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
                    ),
                    vol.Optional(CONF_REQUEST_INTERVAL, default=DEFAULT_REQUEST_INTERVAL): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=MIN_REQUEST_INTERVAL)
                    ),
                    vol.Optional(
                        CONF_CONTEXT_MESSAGES,
                        default=DEFAULT_CONTEXT_MESSAGES
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=1, max=20)
                    ),
                    vol.Optional(
                        CONF_MAX_HISTORY_SIZE,
                        default=DEFAULT_MAX_HISTORY
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=1, max=100)
                    ),
                })
            )

        # Debug log to identify what's in the input
        _LOGGER.debug(f"Provider step input data: {user_input}")

        input_copy = user_input.copy()

        # Check if CONF_NAME exists in input_copy and ensure it's not empty
        if CONF_NAME not in input_copy or not input_copy[CONF_NAME]:
            _LOGGER.warning(f"Missing name in configuration input: {input_copy}")
            input_copy[CONF_NAME] = f"gemini_assistant_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            _LOGGER.info(f"Auto-generated name: {input_copy[CONF_NAME]}")

        # Ensure API key is present
        if CONF_API_KEY not in input_copy or not input_copy[CONF_API_KEY]:
            self._errors["base"] = "invalid_auth"
            _LOGGER.error("API validation error: 'api_key'")
            return self.async_show_form(
                step_id="provider",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME, default=input_copy.get(CONF_NAME, "my_assistant")): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_MODEL, default=input_copy.get(CONF_MODEL, DEFAULT_GEMINI_MODEL if self._provider == API_PROVIDER_GEMINI else DEFAULT_MODEL)): str,
                    vol.Required(CONF_API_ENDPOINT, default=input_copy.get(CONF_API_ENDPOINT, DEFAULT_GEMINI_ENDPOINT if self._provider == API_PROVIDER_GEMINI else DEFAULT_OPENAI_ENDPOINT)): str,
                    vol.Optional(CONF_TEMPERATURE, default=input_copy.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
                    ),
                    vol.Optional(CONF_MAX_TOKENS, default=input_copy.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
                    ),
                    vol.Optional(CONF_REQUEST_INTERVAL, default=input_copy.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=MIN_REQUEST_INTERVAL)
                    ),
                    vol.Optional(
                        CONF_CONTEXT_MESSAGES,
                        default=input_copy.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES)
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=1, max=20)
                    ),
                    vol.Optional(
                        CONF_MAX_HISTORY_SIZE,
                        default=input_copy.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY)
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=1, max=100)
                    ),
                }),
                errors=self._errors
            )

        try:
            # Validate and normalize the name
            normalized_name = self._validate_and_normalize_name(input_copy[CONF_NAME])
            input_copy[CONF_NAME] = normalized_name
        except ValueError as e:
            return self.async_show_form(
                step_id="provider",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME, default=input_copy.get(CONF_NAME, "my_assistant")): str,
                    vol.Required(CONF_API_KEY, default=input_copy.get(CONF_API_KEY, "")): str,
                    vol.Required(CONF_MODEL, default=input_copy.get(CONF_MODEL, DEFAULT_GEMINI_MODEL if self._provider == API_PROVIDER_GEMINI else DEFAULT_MODEL)): str,
                    vol.Required(CONF_API_ENDPOINT, default=input_copy.get(CONF_API_ENDPOINT, DEFAULT_GEMINI_ENDPOINT if self._provider == API_PROVIDER_GEMINI else DEFAULT_OPENAI_ENDPOINT)): str,
                    vol.Optional(CONF_TEMPERATURE, default=input_copy.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
                    ),
                    vol.Optional(CONF_MAX_TOKENS, default=input_copy.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
                    ),
                    vol.Optional(CONF_REQUEST_INTERVAL, default=input_copy.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=MIN_REQUEST_INTERVAL)
                    ),
                    vol.Optional(
                        CONF_CONTEXT_MESSAGES,
                        default=input_copy.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES)
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=1, max=20)
                    ),
                    vol.Optional(
                        CONF_MAX_HISTORY_SIZE,
                        default=input_copy.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY)
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=1, max=100)
                    ),
                }),
                errors={"name": str(e)}
            )

        try:
            # Special handling for Gemini API validation
            if self._provider == API_PROVIDER_GEMINI:
                # For Gemini, we just check if API key is present as there's no simple endpoint to validate
                if not input_copy.get(CONF_API_KEY):
                    self._errors["base"] = "invalid_auth"
                    _LOGGER.error("API validation error: 'api_key'")
                    return self.async_show_form(
                        step_id="provider",
                        data_schema=vol.Schema({
                            vol.Required(CONF_NAME, default=input_copy.get(CONF_NAME, "my_assistant")): str,
                            vol.Required(CONF_API_KEY): str,
                            vol.Required(CONF_MODEL, default=input_copy.get(CONF_MODEL, DEFAULT_GEMINI_MODEL)): str,
                            vol.Required(CONF_API_ENDPOINT, default=input_copy.get(CONF_API_ENDPOINT, DEFAULT_GEMINI_ENDPOINT)): str,
                            # Other fields remain the same
                        }),
                        errors=self._errors
                    )
            else:
                # For other providers, validate API connection
                if not await self._async_validate_api(input_copy):
                    return self.async_show_form(
                        step_id="provider",
                        data_schema=vol.Schema({
                            vol.Required(CONF_NAME, default=input_copy.get(CONF_NAME, "my_assistant")): str,
                            vol.Required(CONF_API_KEY, default=input_copy.get(CONF_API_KEY, "")): str,
                            vol.Required(CONF_MODEL, default=input_copy.get(CONF_MODEL, DEFAULT_MODEL)): str,
                            vol.Required(CONF_API_ENDPOINT, default=input_copy.get(CONF_API_ENDPOINT, DEFAULT_OPENAI_ENDPOINT)): str,
                            vol.Optional(CONF_TEMPERATURE, default=input_copy.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.All(
                                vol.Coerce(float),
                                vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
                            ),
                            vol.Optional(CONF_MAX_TOKENS, default=input_copy.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.All(
                                vol.Coerce(int),
                                vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
                            ),
                            vol.Optional(CONF_REQUEST_INTERVAL, default=input_copy.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)): vol.All(
                                vol.Coerce(float),
                                vol.Range(min=MIN_REQUEST_INTERVAL)
                            ),
                            vol.Optional(
                                CONF_CONTEXT_MESSAGES,
                                default=input_copy.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES)
                            ): vol.All(
                                vol.Coerce(int),
                                vol.Range(min=1, max=20)
                            ),
                            vol.Optional(
                                CONF_MAX_HISTORY_SIZE,
                                default=input_copy.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY)
                            ): vol.All(
                                vol.Coerce(int),
                                vol.Range(min=1, max=100)
                            ),
                        }),
                        errors=self._errors
                    )
        except Exception as e:
            # Handle any unexpected exceptions during validation
            _LOGGER.exception("Unexpected error during API validation")
            return self.async_show_form(
                step_id="provider",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME, default=input_copy.get(CONF_NAME, "my_assistant")): str,
                    vol.Required(CONF_API_KEY, default=input_copy.get(CONF_API_KEY, "")): str,
                    vol.Required(CONF_MODEL, default=input_copy.get(CONF_MODEL, DEFAULT_GEMINI_MODEL if self._provider == API_PROVIDER_GEMINI else DEFAULT_MODEL)): str,
                    vol.Required(CONF_API_ENDPOINT, default=input_copy.get(CONF_API_ENDPOINT, DEFAULT_GEMINI_ENDPOINT if self._provider == API_PROVIDER_GEMINI else DEFAULT_OPENAI_ENDPOINT)): str,
                    # Other fields remain the same
                }),
                errors={"base": str(e)}
            )

        # All validation passed, create the entry
        return await self._create_entry(input_copy)

    def _validate_and_normalize_name(self, name: str) -> str:
        """
        Validate and normalize name with detailed error handling.

        Raises:
            ValueError: If name is invalid

        Returns:
            Normalized name
        """
        if not name:
            raise ValueError("empty")

        name = name.strip()
        normalized = ''.join(
            c if c.isalnum() or c in ' _' else '_'  # Only allow underscores
            for c in name
        )

        normalized = normalized.replace(' ', '_').lower()

        for entry in self._async_current_entries():
            if entry.data.get(CONF_NAME, "") == normalized:
                raise ValueError("name_exists")

        normalized = normalized[:50]

        if not normalized:
            raise ValueError("empty")

        return normalized

    async def _async_validate_api(self, user_input: Dict[str, Any]) -> bool:
        """Validate API connection."""
        try:
            if CONF_API_KEY not in user_input:
                _LOGGER.error("API validation error: 'api_key'")
                self._errors["base"] = "invalid_auth"
                return False

            session = async_get_clientsession(self.hass)
            headers = self._get_api_headers(user_input)
            endpoint = user_input[CONF_API_ENDPOINT].rstrip('/')

            if self._provider == API_PROVIDER_GEMINI:
                if not user_input[CONF_API_KEY]:
                    self._errors["base"] = "invalid_auth"
                    return False
                return True
            else:
                check_url = (
                    f"{endpoint}/v1/models" if self._provider == API_PROVIDER_ANTHROPIC
                    else f"{endpoint}/models"
                )

                async with session.get(check_url, headers=headers) as response:
                    if response.status == 401:
                        self._errors["base"] = "invalid_auth"
                        return False
                    elif response.status not in [200, 404]:
                        self._errors["base"] = "cannot_connect"
                        return False
                    return True

        except Exception as err:
            _LOGGER.error("API validation error: %s", str(err))
            self._errors["base"] = "cannot_connect"
            return False

    def _get_api_headers(self, user_input: Dict[str, Any]) -> Dict[str, str]:
        """Get API headers based on provider."""
        if CONF_API_KEY not in user_input:
            return {"Content-Type": "application/json"}

        api_key = user_input[CONF_API_KEY]

        if self._provider == API_PROVIDER_ANTHROPIC:
            return {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
        elif self._provider == API_PROVIDER_GEMINI:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def _create_entry(self, user_input: Dict[str, Any]) -> FlowResult:
        """Create the config entry with comprehensive data preservation."""
        instance_name = user_input[CONF_NAME]
        normalized_name = normalize_name(instance_name)

        unique_id = f"{DOMAIN}_{normalized_name}_{self._provider}".lower()

        default_model = (
            DEFAULT_DEEPSEEK_MODEL if self._provider == API_PROVIDER_DEEPSEEK else
            DEFAULT_GEMINI_MODEL if self._provider == API_PROVIDER_GEMINI else
            DEFAULT_MODEL
        )

        entry_data = {
            CONF_API_PROVIDER: self._provider,
            CONF_NAME: instance_name,
            "normalized_name": normalized_name,
            CONF_API_KEY: user_input.get(CONF_API_KEY),
            CONF_API_ENDPOINT: user_input.get(CONF_API_ENDPOINT),
            "unique_id": unique_id,
            CONF_MODEL: user_input.get(CONF_MODEL, default_model),
            CONF_TEMPERATURE: user_input.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            CONF_MAX_TOKENS: user_input.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            CONF_REQUEST_INTERVAL: user_input.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),
            CONF_CONTEXT_MESSAGES: user_input.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES),
            CONF_MAX_HISTORY_SIZE: user_input.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY),
        }

        for key, value in user_input.items():
            if key not in entry_data:
                entry_data[key] = value

        _LOGGER.debug(f"Creating config entry with data: {entry_data}")

        return self.async_create_entry(
            title=instance_name,
            data=entry_data
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_data = {**self.config_entry.data, **self.config_entry.options}
        provider = current_data.get(CONF_API_PROVIDER)

        default_model = (
            DEFAULT_DEEPSEEK_MODEL if provider == API_PROVIDER_DEEPSEEK else
            DEFAULT_GEMINI_MODEL if provider == API_PROVIDER_GEMINI else
            DEFAULT_MODEL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_MODEL,
                    default=current_data.get(CONF_MODEL, default_model)
                ): str,
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=current_data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
                ),
                vol.Optional(
                    CONF_MAX_TOKENS,
                    default=current_data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
                ),
                vol.Optional(
                    CONF_REQUEST_INTERVAL,
                    default=current_data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_REQUEST_INTERVAL)
                ),
                vol.Optional(
                    CONF_CONTEXT_MESSAGES,
                    default=current_data.get(
                        CONF_CONTEXT_MESSAGES,
                        DEFAULT_CONTEXT_MESSAGES
                    )
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=20)
                ),
                vol.Optional(
                    CONF_MAX_HISTORY_SIZE,
                    default=current_data.get(
                        CONF_MAX_HISTORY_SIZE,
                        DEFAULT_MAX_HISTORY
                    )
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=100)
                ),
            })
        )
