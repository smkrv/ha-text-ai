"""The HA Text AI integration."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import config_validation as cv

from .coordinator import HATextAICoordinator  

from .const import (
    DOMAIN,
    PLATFORMS,
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

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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
            endpoint=entry.data.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT),
            model=entry.data.get(CONF_MODEL, DEFAULT_MODEL),
            temperature=entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            max_tokens=entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            request_interval=entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),
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
            entry.data.get(CONF_MODEL, DEFAULT_MODEL)
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
