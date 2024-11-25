"""Config flow for HA text AI integration."""
import logging
from typing import Any, Dict, Optional

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
    API_PROVIDERS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_OPENAI_ENDPOINT,
    DEFAULT_ANTHROPIC_ENDPOINT,
    DEFAULT_CONTEXT_MESSAGES,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
    MIN_REQUEST_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

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
        if user_input is None:
            default_endpoint = (
                DEFAULT_OPENAI_ENDPOINT if self._provider == API_PROVIDER_OPENAI
                else DEFAULT_ANTHROPIC_ENDPOINT
            )

            suggested_name = f"HA Text AI {len(self._async_current_entries()) + 1}"

            return self.async_show_form(
                step_id="provider",
                data_schema=vol.Schema({
                    vol.Required(CONF_NAME, default=suggested_name): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_MODEL, default=DEFAULT_MODEL): str,
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
                }),
                errors=self._errors
            )

        instance_name = user_input[CONF_NAME]
        await self._async_validate_name(instance_name)
        if self._errors:
            return await self.async_step_provider()

        if not await self._async_validate_api(user_input):
            return await self.async_step_provider()

        return await self._create_entry(user_input)

    async def _async_validate_name(self, name: str) -> bool:
        """Validate that the name is unique."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_NAME) == name:
                self._errors["name"] = "name_exists"
                return False
        return True

    async def _async_validate_api(self, user_input: Dict[str, Any]) -> bool:
        """Validate API connection."""
        try:
            session = async_get_clientsession(self.hass)
            headers = self._get_api_headers(user_input)
            endpoint = user_input[CONF_API_ENDPOINT].rstrip('/')

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
        api_key = user_input[CONF_API_KEY]

        if self._provider == API_PROVIDER_ANTHROPIC:
            return {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def _create_entry(self, user_input: Dict[str, Any]) -> FlowResult:
        """Create the config entry."""
        instance_name = user_input[CONF_NAME]
        unique_id = f"{DOMAIN}_{instance_name}_{self._provider}".lower().replace(" ", "_")

        return self.async_create_entry(
            title=instance_name,
            data={
                CONF_API_PROVIDER: self._provider,
                CONF_NAME: instance_name,
                **user_input,
                "unique_id": unique_id,
                CONF_CONTEXT_MESSAGES: user_input.get(
                CONF_CONTEXT_MESSAGES,
                DEFAULT_CONTEXT_MESSAGES)
        }
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_MODEL,
                    default=current_data.get(CONF_MODEL, DEFAULT_MODEL)
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
            })
        )
