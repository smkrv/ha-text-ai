"""The HA text AI integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import HomeAssistantError, ConfigEntryNotReady

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

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the HA text AI component."""
    hass.data.setdefault(DOMAIN, {})

    async def async_ask_question(call: ServiceCall) -> None:
        """Handle the ask_question service call."""
        if not hass.data[DOMAIN]:
            raise HomeAssistantError("No AI Text integration configured")

        coordinator = next(iter(hass.data[DOMAIN].values()))
        question = call.data["question"]

 
        original_params = {
            "model": coordinator.model,
            "temperature": coordinator.temperature,
            "max_tokens": coordinator.max_tokens
        }

        try:

            if "model" in call.data:
                coordinator.model = call.data["model"]
            if "temperature" in call.data:
                coordinator.temperature = call.data["temperature"]
            if "max_tokens" in call.data:
                coordinator.max_tokens = call.data["max_tokens"]

            await coordinator.async_ask_question(question)
        except Exception as ex:
            _LOGGER.error("Error asking question: %s", str(ex))
            raise HomeAssistantError(f"Failed to ask question: {str(ex)}") from ex
        finally:

            coordinator.model = original_params["model"]
            coordinator.temperature = original_params["temperature"]
            coordinator.max_tokens = original_params["max_tokens"]

    async def async_clear_history(call: ServiceCall) -> None:
        """Handle the clear_history service call."""
        if not hass.data[DOMAIN]:
            raise HomeAssistantError("No AI Text integration configured")

        coordinator = next(iter(hass.data[DOMAIN].values()))
        coordinator._responses.clear()
        await coordinator.async_refresh()

    async def async_get_history(call: ServiceCall) -> dict[str, list]:
        """Handle the get_history service call."""
        if not hass.data[DOMAIN]:
            raise HomeAssistantError("No AI Text integration configured")

        coordinator = next(iter(hass.data[DOMAIN].values()))
        if not coordinator._responses:
            return {"history": []}

        limit = call.data.get("limit", 10)
        history = list(coordinator._responses.items())
        limited_history = history[-limit:] if len(history) > limit else history

        return {
            "history": [
                {"question": q, "response": r} for q, r in limited_history
            ]
        }

    async def async_set_system_prompt(call: ServiceCall) -> None:
        """Handle the set_system_prompt service call."""
        if not hass.data[DOMAIN]:
            raise HomeAssistantError("No AI Text integration configured")

        coordinator = next(iter(hass.data[DOMAIN].values()))
        coordinator.system_prompt = call.data["prompt"]


    hass.services.async_register(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        async_ask_question,
        schema=vol.Schema({
            vol.Required("question"): cv.string,
            vol.Optional("model"): cv.string,
            vol.Optional("temperature"): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=2)
            ),
            vol.Optional("max_tokens"): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=4096)
            ),
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
            vol.Optional("limit", default=10): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            ),
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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA text AI from a config entry."""
    try:
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
        hass.data[DOMAIN][entry.entry_id] = coordinator

        return await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as ex:
        raise ConfigEntryNotReady(f"Failed to setup entry: {str(ex)}") from ex

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)


        if not hass.data[DOMAIN]:
            services = [
                SERVICE_ASK_QUESTION,
                SERVICE_CLEAR_HISTORY,
                SERVICE_GET_HISTORY,
                SERVICE_SET_SYSTEM_PROMPT
            ]
            for service in services:
                if service in hass.services.async_services().get(DOMAIN, {}):
                    hass.services.async_remove(DOMAIN, service)

    return unload_ok
