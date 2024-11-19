"""The HA Text AI integration."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN, PLATFORMS
from .coordinator import HATextAICoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the HA Text AI component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Text AI from a config entry."""
    try:
        session = aiohttp_client.async_get_clientsession(hass)

        coordinator = HATextAICoordinator(
            hass,
            api_key=entry.data[CONF_API_KEY],
            endpoint=entry.data.get("api_endpoint", "https://api.openai.com/v1"),
            model=entry.data.get("model", "gpt-3.5-turbo"),
            temperature=entry.data.get("temperature", 0.7),
            max_tokens=entry.data.get("max_tokens", 1000),
            request_interval=entry.data.get("request_interval", 1.0),
            session=session,
        )

        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception as refresh_ex:
            _LOGGER.error("Failed to refresh coordinator: %s", str(refresh_ex))
            return False

        if not coordinator.last_update_success:
            _LOGGER.error("Failed to communicate with OpenAI API")
            return False

        hass.data[DOMAIN][entry.entry_id] = coordinator

        try:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        except Exception as setup_ex:
            _LOGGER.error("Failed to setup platforms: %s", str(setup_ex))
            return False

        _LOGGER.info(
            "Successfully set up HA Text AI with model: %s",
            entry.data.get("model", "gpt-3.5-turbo")
        )

        return True

    except Exception as ex:
        _LOGGER.exception("Unexpected error setting up entry: %s", str(ex))
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        if entry.entry_id not in hass.data.get(DOMAIN, {}):
            return True

        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            coordinator = hass.data[DOMAIN].pop(entry.entry_id)
            await coordinator.async_shutdown()

        return unload_ok

    except Exception as ex:
        _LOGGER.exception("Error unloading entry: %s", str(ex))
        return False

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    try:
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)
    except Exception as ex:
        _LOGGER.exception("Error reloading entry: %s", str(ex))
