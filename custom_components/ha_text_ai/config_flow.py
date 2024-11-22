"""Config flow for HA text AI integration."""
from typing import Any, Dict, Optional
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
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
    CONF_API_PROVIDER,
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDERS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_OPENAI_ENDPOINT,
    DEFAULT_ANTHROPIC_ENDPOINT,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
    MIN_REQUEST_INTERVAL,
)

import logging
_LOGGER = logging.getLogger(__name__)

class HATextAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA text AI."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self._show_provider_selection()

        if "provider" in user_input:
            return self._show_provider_config(user_input["provider"])

        return await self._process_configuration(user_input)

    def _show_provider_selection(self):
        """Show provider selection screen."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("provider"): vol.In(API_PROVIDERS)
            }),
            description_placeholders={"providers": ", ".join(API_PROVIDERS)}
        )

    def _show_provider_config(self, provider):
        """Show configuration screen for selected provider."""
        default_endpoint = DEFAULT_OPENAI_ENDPOINT if provider == API_PROVIDER_OPENAI else DEFAULT_ANTHROPIC_ENDPOINT

        default_name = f"HA Text AI {len(self._async_current_entries()) + 1}"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name", default=default_name): str,
                vol.Required(CONF_API_PROVIDER): vol.In([provider]),
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_MODEL, default=DEFAULT_MODEL): str,
                vol.Optional(CONF_API_ENDPOINT, default=default_endpoint): str,
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
            }),
            description_placeholders={"provider": provider}
        )

async def _process_configuration(self, user_input):
    """Validate and process user configuration."""
    errors = {}

    try:
        # Генерируем уникальный идентификатор один раз
        unique_id = f"{user_input[CONF_API_KEY]}_{user_input[CONF_MODEL]}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        session = async_get_clientsession(self.hass)

        # Minimal API key validation
        headers = {
            "Authorization": f"Bearer {user_input[CONF_API_KEY]}",
            "Content-Type": "application/json"
        }

        # Adjust headers and endpoint based on provider
        if user_input[CONF_API_PROVIDER] == API_PROVIDER_ANTHROPIC:
            headers = {
                "x-api-key": user_input[CONF_API_KEY],
                "anthropic-version": "2023-06-01"
            }

        # Basic connection test
        try:
            async with session.get(
                f"{user_input[CONF_API_ENDPOINT]}/models",
                headers=headers
            ) as response:
                if response.status not in [200, 404]:
                    errors["base"] = "cannot_connect"
        except Exception as e:
            _LOGGER.error(f"Connection test failed: {e}")
            errors["base"] = "cannot_connect"

        if not errors:
            return self.async_create_entry(
                title=user_input.get("name", f"HA Text AI ({user_input[CONF_API_PROVIDER]})"),
                data=user_input
            )

    except Exception as e:
        _LOGGER.error(f"Unexpected error: {e}")
        errors["base"] = "unknown"

    # Return to provider config, preserving previous input
    return self.async_show_form(
        step_id="user",
        data_schema=vol.Schema({
            vol.Required("name", default=user_input.get("name", f"HA Text AI {len(self._async_current_entries()) + 1}")): str,
            vol.Required(CONF_API_PROVIDER): vol.In([user_input[CONF_API_PROVIDER]]),
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_MODEL, default=user_input.get(CONF_MODEL, DEFAULT_MODEL)): str,
            vol.Optional(CONF_API_ENDPOINT, default=user_input.get(CONF_API_ENDPOINT,
                DEFAULT_OPENAI_ENDPOINT if user_input[CONF_API_PROVIDER] == API_PROVIDER_OPENAI
                else DEFAULT_ANTHROPIC_ENDPOINT)): str,
            vol.Optional(CONF_TEMPERATURE, default=user_input.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
            ),
            vol.Optional(CONF_MAX_TOKENS, default=user_input.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
            ),
            vol.Optional(CONF_REQUEST_INTERVAL, default=user_input.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)): vol.All(
                vol.Coerce(float),
                vol.Range(min=MIN_REQUEST_INTERVAL)
            ),
        }),
        description_placeholders={"provider": user_input[CONF_API_PROVIDER]},
        errors=errors
    )
    
def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
    """Create the options flow."""
    return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_data = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
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
            })
        )
