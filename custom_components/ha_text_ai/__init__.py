"""The HA text AI integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_ASK_QUESTION,
    SERVICE_CLEAR_HISTORY,
    SERVICE_GET_HISTORY,
    SERVICE_SET_SYSTEM_PROMPT,
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_MAX_TOKENS,
    CONF_API_ENDPOINT,
    CONF_REQUEST_INTERVAL,
)
from .coordinator import HATextAICoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the HA text AI component from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA text AI from a config entry."""
    coordinator = HATextAICoordinator(
        hass,
        api_key=entry.data[CONF_API_KEY],
        endpoint=entry.data.get(CONF_API_ENDPOINT),
        model=entry.data.get(CONF_MODEL),
        temperature=entry.data.get(CONF_TEMPERATURE),
        max_tokens=entry.data.get(CONF_MAX_TOKENS),
        request_interval=entry.data.get(CONF_REQUEST_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_ask_question(call: ServiceCall) -> None:
        """Handle the ask_question service call."""
        question = call.data["question"]
        model = call.data.get("model", coordinator.model)
        temperature = call.data.get("temperature", coordinator.temperature)
        max_tokens = call.data.get("max_tokens", coordinator.max_tokens)

        # Temporarily update parameters if they were overridden
        original_model = coordinator.model
        original_temperature = coordinator.temperature
        original_max_tokens = coordinator.max_tokens

        try:
            coordinator.model = model
            coordinator.temperature = temperature
            coordinator.max_tokens = max_tokens
            await coordinator.async_ask_question(question)
        finally:
            # Restore original parameters
            coordinator.model = original_model
            coordinator.temperature = original_temperature
            coordinator.max_tokens = original_max_tokens

    async def async_clear_history(call: ServiceCall) -> None:
        """Handle the clear_history service call."""
        coordinator._responses.clear()
        await coordinator.async_refresh()

    async def async_get_history(call: ServiceCall) -> None:
        """Handle the get_history service call."""
        limit = call.data.get("limit", 10)
        history = list(coordinator._responses.items())[-limit:]
        return {
            "history": [
                {"question": q, "response": r} for q, r in history
            ]
        }

    async def async_set_system_prompt(call: ServiceCall) -> None:
        """Handle the set_system_prompt service call."""
        prompt = call.data["prompt"]
        coordinator.system_prompt = prompt

    # Register all services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        async_ask_question,
        schema=vol.Schema({
            vol.Required("question"): cv.string,
            vol.Optional("model"): cv.string,
            vol.Optional("temperature"): vol.Coerce(float),
            vol.Optional("max_tokens"): vol.Coerce(int),
        })
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        async_clear_history,
        schema=vol.Schema({})
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_HISTORY,
        async_get_history,
        schema=vol.Schema({
            vol.Optional("limit"): vol.Coerce(int),
        })
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SYSTEM_PROMPT,
        async_set_system_prompt,
        schema=vol.Schema({
            vol.Required("prompt"): cv.string,
        })
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unregister services
        for service in [
            SERVICE_ASK_QUESTION,
            SERVICE_CLEAR_HISTORY,
            SERVICE_GET_HISTORY,
            SERVICE_SET_SYSTEM_PROMPT
        ]:
            hass.services.async_remove(DOMAIN, service)

    return unload_ok
