"""
Config flow for HA text AI integration.

@license: PolyForm Noncommercial 1.0.0 (https://polyformproject.org/licenses/noncommercial/1.0.0)
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_MAX_TOKENS,
    CONF_API_ENDPOINT,
    CONF_REQUEST_INTERVAL,
    CONF_API_TIMEOUT,
    CONF_API_PROVIDER,
    CONF_CONTEXT_MESSAGES,
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_DEEPSEEK,
    API_PROVIDER_GEMINI,
    API_PROVIDERS,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_API_TIMEOUT,
    DEFAULT_CONTEXT_MESSAGES,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
    MIN_REQUEST_INTERVAL,
    MIN_API_TIMEOUT,
    MAX_API_TIMEOUT,
    DEFAULT_NAME_PREFIX,
    DEFAULT_INSTANCE_NAME,
    DEFAULT_MAX_HISTORY,
    CONF_MAX_HISTORY_SIZE,
    MIN_CONTEXT_MESSAGES,
    MAX_CONTEXT_MESSAGES,
    MIN_HISTORY_SIZE,
    MAX_HISTORY_SIZE,
)
from homeassistant.util import dt as dt_util

from .utils import normalize_name, safe_log_data, validate_endpoint
from .providers import get_default_endpoint, get_default_model, build_auth_headers

_LOGGER = logging.getLogger(__name__)


def _build_parameter_schema(data: Dict[str, Any]) -> dict:
    """Build shared parameter schema fields used by both ConfigFlow and OptionsFlow."""
    return {
        vol.Optional(
            CONF_TEMPERATURE,
            default=data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
        ): vol.All(vol.Coerce(float), vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)),
        vol.Optional(
            CONF_MAX_TOKENS,
            default=data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)),
        vol.Optional(
            CONF_REQUEST_INTERVAL,
            default=data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),
        ): vol.All(vol.Coerce(float), vol.Range(min=MIN_REQUEST_INTERVAL)),
        vol.Optional(
            CONF_API_TIMEOUT,
            default=data.get(CONF_API_TIMEOUT, DEFAULT_API_TIMEOUT),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_API_TIMEOUT, max=MAX_API_TIMEOUT)),
        vol.Optional(
            CONF_CONTEXT_MESSAGES,
            default=data.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_CONTEXT_MESSAGES, max=MAX_CONTEXT_MESSAGES)),
        vol.Optional(
            CONF_MAX_HISTORY_SIZE,
            default=data.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_HISTORY_SIZE, max=MAX_HISTORY_SIZE)),
    }


class HATextAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA text AI."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._errors = {}
        self._data = {}
        self._provider = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> ConfigFlowResult:
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

    def _build_provider_schema(
        self, data: Optional[Dict[str, Any]] = None
    ) -> vol.Schema:
        """Build provider configuration schema with optional defaults from data."""
        defaults = data or {}
        schema_dict = {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_INSTANCE_NAME)): str,
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_MODEL, default=defaults.get(CONF_MODEL, get_default_model(self._provider))): str,
            vol.Required(CONF_API_ENDPOINT, default=defaults.get(CONF_API_ENDPOINT, get_default_endpoint(self._provider))): str,
        }
        schema_dict.update(_build_parameter_schema(defaults))
        return vol.Schema(schema_dict)

    async def async_step_provider(self, user_input: Optional[Dict[str, Any]] = None) -> ConfigFlowResult:
        """Handle provider configuration step."""
        self._errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="provider",
                data_schema=self._build_provider_schema(),
            )

        _LOGGER.debug("Provider step input data: %s", safe_log_data(user_input))

        input_copy = user_input.copy()

        # Check if CONF_NAME exists in input_copy and ensure it's not empty
        if CONF_NAME not in input_copy or not input_copy[CONF_NAME]:
            _LOGGER.warning("Missing name in configuration input: %s", safe_log_data(input_copy))
            input_copy[CONF_NAME] = f"assistant_{dt_util.utcnow().strftime('%Y%m%d_%H%M%S')}"
            _LOGGER.info("Auto-generated name: %s", input_copy[CONF_NAME])

        # Ensure API key is present
        if CONF_API_KEY not in input_copy or not input_copy[CONF_API_KEY]:
            self._errors["base"] = "invalid_auth"
            _LOGGER.error("API validation error: 'api_key'")
            return self.async_show_form(
                step_id="provider",
                data_schema=self._build_provider_schema(input_copy),
                errors=self._errors
            )

        try:
            normalized_name = self._validate_and_normalize_name(input_copy[CONF_NAME])
            input_copy[CONF_NAME] = normalized_name
        except ValueError as e:
            return self.async_show_form(
                step_id="provider",
                data_schema=self._build_provider_schema(input_copy),
                errors={"name": str(e)}
            )

        try:
            if not await self._async_validate_api(input_copy):
                return self.async_show_form(
                    step_id="provider",
                    data_schema=self._build_provider_schema(input_copy),
                    errors=self._errors
                )
        except Exception:
            _LOGGER.exception("Unexpected error during API validation")
            return self.async_show_form(
                step_id="provider",
                data_schema=self._build_provider_schema(input_copy),
                errors={"base": "unknown"}
            )

        return await self._create_entry(input_copy)

    def _validate_and_normalize_name(self, name: str) -> str:
        """Validate and normalize name.

        Truncates before uniqueness check to prevent collisions.

        Raises:
            ValueError: If name is invalid or already exists.
        """
        if not name or not name.strip():
            raise ValueError("empty")

        normalized = normalize_name(name.strip())[:50]

        if not normalized:
            raise ValueError("empty")

        for entry in self._async_current_entries():
            if entry.data.get(CONF_NAME, "") == normalized:
                raise ValueError("name_exists")

        return normalized

    async def _async_validate_api(self, user_input: Dict[str, Any]) -> bool:
        """Validate API connection using provider registry."""
        try:
            if CONF_API_KEY not in user_input:
                _LOGGER.error("API validation error: 'api_key'")
                self._errors["base"] = "invalid_auth"
                return False

            try:
                endpoint = await validate_endpoint(self.hass, user_input[CONF_API_ENDPOINT])
            except ValueError as err:
                _LOGGER.error("Endpoint validation failed: %s", err)
                self._errors["base"] = "cannot_connect"
                return False

            if self._provider == API_PROVIDER_GEMINI:
                if not user_input[CONF_API_KEY]:
                    self._errors["base"] = "invalid_auth"
                    return False
                return True

            session = async_get_clientsession(self.hass)
            headers = build_auth_headers(self._provider, user_input[CONF_API_KEY])

            from .providers import get_provider_config
            check_path = get_provider_config(self._provider).get("check_path", "/models")
            check_url = f"{endpoint}{check_path}"

            async with session.get(check_url, headers=headers) as response:
                if response.status == 401:
                    self._errors["base"] = "invalid_auth"
                    return False
                elif response.status != 200:
                    self._errors["base"] = "cannot_connect"
                    return False
                return True

        except Exception as err:
            _LOGGER.error("API validation error: %s", str(err))
            self._errors["base"] = "cannot_connect"
            return False

    async def _create_entry(self, user_input: Dict[str, Any]) -> ConfigFlowResult:
        """Create the config entry with unique_id deduplication."""
        instance_name = user_input[CONF_NAME]
        normalized_name = normalize_name(instance_name)

        unique_id = f"{DOMAIN}_{normalized_name}_{self._provider}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        default_model = get_default_model(self._provider)

        entry_data = {
            CONF_API_PROVIDER: self._provider,
            CONF_NAME: instance_name,
            CONF_API_KEY: user_input.get(CONF_API_KEY),
            CONF_API_ENDPOINT: user_input.get(CONF_API_ENDPOINT),
            CONF_MODEL: user_input.get(CONF_MODEL, default_model),
            CONF_TEMPERATURE: user_input.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            CONF_MAX_TOKENS: user_input.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            CONF_REQUEST_INTERVAL: user_input.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),
            CONF_API_TIMEOUT: user_input.get(CONF_API_TIMEOUT, DEFAULT_API_TIMEOUT),
            CONF_CONTEXT_MESSAGES: user_input.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES),
            CONF_MAX_HISTORY_SIZE: user_input.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY),
        }

        _LOGGER.debug("Creating config entry with data: %s", safe_log_data(entry_data))

        return self.async_create_entry(
            title=instance_name,
            data=entry_data
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    async def _async_validate_api(self, provider: str, api_key: str, endpoint: str) -> bool:
        """Validate API connection using provider registry."""
        try:
            if not api_key:
                self._errors["base"] = "invalid_auth"
                return False

            try:
                endpoint = await validate_endpoint(self.hass, endpoint)
            except ValueError as err:
                _LOGGER.error("Endpoint validation failed: %s", err)
                self._errors["base"] = "cannot_connect"
                return False

            if provider == API_PROVIDER_GEMINI:
                return True

            session = async_get_clientsession(self.hass)
            headers = build_auth_headers(provider, api_key)

            from .providers import get_provider_config
            check_path = get_provider_config(provider).get("check_path", "/models")
            check_url = f"{endpoint}{check_path}"

            async with session.get(check_url, headers=headers) as response:
                if response.status == 401:
                    self._errors["base"] = "invalid_auth"
                    return False
                elif response.status != 200:
                    self._errors["base"] = "cannot_connect"
                    return False
                return True

        except Exception as err:
            _LOGGER.error("API validation error: %s", str(err))
            self._errors["base"] = "cannot_connect"
            return False

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> ConfigFlowResult:
        """Handle provider selection step."""
        if not hasattr(self, "_errors"):
            self._errors: dict[str, str] = {}
            self._selected_provider: Optional[str] = None
        current_data = {**self.config_entry.data, **self.config_entry.options}
        current_provider = current_data.get(CONF_API_PROVIDER, API_PROVIDER_OPENAI)

        if user_input is not None:
            self._selected_provider = user_input.get(CONF_API_PROVIDER, current_provider)
            return await self.async_step_settings()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_API_PROVIDER,
                    default=current_provider
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=API_PROVIDERS,
                        translation_key="api_provider"
                    )
                ),
            }),
            description_placeholders={
                "current_provider": current_provider
            }
        )

    async def async_step_settings(self, user_input: Optional[Dict[str, Any]] = None) -> ConfigFlowResult:
        """Handle settings configuration step."""
        self._errors = {}
        current_data = {**self.config_entry.data, **self.config_entry.options}
        provider = self._selected_provider or current_data.get(CONF_API_PROVIDER, API_PROVIDER_OPENAI)

        # Determine if provider changed to show appropriate defaults
        provider_changed = provider != current_data.get(CONF_API_PROVIDER)

        # Use new defaults if provider changed, otherwise use current values
        if provider_changed:
            default_endpoint = get_default_endpoint(provider)
            default_model = get_default_model(provider)
        else:
            default_endpoint = current_data.get(CONF_API_ENDPOINT, get_default_endpoint(provider))
            default_model = current_data.get(CONF_MODEL, get_default_model(provider))

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, "").strip()
            endpoint = user_input.get(CONF_API_ENDPOINT, default_endpoint)

            # Require API key re-entry when endpoint or provider changed
            stored_endpoint = current_data.get(CONF_API_ENDPOINT, "")
            endpoint_changed = endpoint != stored_endpoint
            if not api_key and (provider_changed or endpoint_changed):
                self._errors["base"] = "api_key_required"
                return self.async_show_form(
                    step_id="settings",
                    data_schema=self._get_settings_schema(
                        provider=provider,
                        current_data=current_data,
                        user_input=user_input,
                        default_endpoint=default_endpoint,
                        default_model=default_model,
                    ),
                    errors=self._errors,
                    description_placeholders={
                        "provider": provider
                    }
                )

            # Fall back to stored key if not re-entered and endpoint unchanged
            if not api_key:
                api_key = current_data.get(CONF_API_KEY, "")

            if await self._async_validate_api(provider, api_key, endpoint):
                final_data = {
                    CONF_API_PROVIDER: provider,
                    **user_input,
                    CONF_API_KEY: api_key,
                }
                return self.async_create_entry(title="", data=final_data)

            # Show form again with errors
            return self.async_show_form(
                step_id="settings",
                data_schema=self._get_settings_schema(
                    provider=provider,
                    current_data=current_data,
                    user_input=user_input,
                    default_endpoint=default_endpoint,
                    default_model=default_model,
                ),
                errors=self._errors,
                description_placeholders={
                    "provider": provider
                }
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=self._get_settings_schema(
                provider=provider,
                current_data=current_data,
                user_input=None,
                default_endpoint=default_endpoint,
                default_model=default_model,
            ),
            description_placeholders={
                "provider": provider
            }
        )

    def _get_settings_schema(
        self,
        provider: str,
        current_data: Dict[str, Any],
        user_input: Optional[Dict[str, Any]],
        default_endpoint: str,
        default_model: str,
    ) -> vol.Schema:
        """Build settings schema using shared parameter definitions."""
        data = user_input or current_data

        schema_dict = {
            vol.Optional(CONF_API_KEY, default=""): str,
            vol.Required(
                CONF_API_ENDPOINT,
                default=data.get(CONF_API_ENDPOINT, default_endpoint),
            ): str,
            vol.Required(
                CONF_MODEL,
                default=data.get(CONF_MODEL, default_model),
            ): str,
        }
        schema_dict.update(_build_parameter_schema(data))
        return vol.Schema(schema_dict)
