"""The HA Text AI integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import asyncio
import voluptuous as vol
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import aiohttp_client
from async_timeout import timeout

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
    API_VERSION,
    API_MODELS_PATH,
    API_TIMEOUT,
    API_RETRY_COUNT,
    API_BACKOFF_FACTOR,
    SERVICE_ASK_QUESTION,
    SERVICE_CLEAR_HISTORY,
    SERVICE_SET_SYSTEM_PROMPT,
    SERVICE_SCHEMA_ASK_QUESTION,
    SERVICE_SCHEMA_SET_SYSTEM_PROMPT,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

@callback
def get_coordinator(hass: HomeAssistant) -> Optional[HATextAICoordinator]:
    """Get the first available coordinator."""
    if DOMAIN in hass.data and hass.data[DOMAIN]:
        return next(iter(hass.data[DOMAIN].values()), None)
    return None

async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the HA Text AI component."""
    hass.data.setdefault(DOMAIN, {})

    async def async_ask_question(call: ServiceCall) -> None:
        """Handle ask_question service."""
        coordinator = get_coordinator(hass)
        if not coordinator:
            raise HomeAssistantError("No coordinator available")

        question = call.data.get("question")
        if not question:
            raise HomeAssistantError("No question provided")

        try:
            params = {
                "system_prompt": call.data.get("system_prompt"),
                "model": call.data.get("model"),
                "temperature": call.data.get("temperature"),
                "max_tokens": call.data.get("max_tokens"),
                "priority": call.data.get("priority", False)
            }
            await coordinator.async_ask_question(question, **params)
        except Exception as err:
            _LOGGER.error("Error asking question: %s", str(err))
            raise HomeAssistantError(f"Failed to process question: {str(err)}")

    async def async_clear_history(call: ServiceCall) -> None:
        """Handle clear_history service."""
        coordinator = get_coordinator(hass)
        if not coordinator:
            raise HomeAssistantError("No coordinator available")

        try:
            await coordinator.clear_history()
        except Exception as err:
            _LOGGER.error("Error clearing history: %s", str(err))
            raise HomeAssistantError(f"Failed to clear history: {str(err)}")

    async def async_set_system_prompt(call: ServiceCall) -> None:
        """Handle set_system_prompt service."""
        coordinator = get_coordinator(hass)
        if not coordinator:
            raise HomeAssistantError("No coordinator available")

        prompt = call.data.get("prompt")
        if not prompt:
            raise HomeAssistantError("No prompt provided")

        try:
            coordinator.update_system_prompt(prompt)
        except Exception as err:
            _LOGGER.error("Error setting system prompt: %s", str(err))
            raise HomeAssistantError(f"Failed to set system prompt: {str(err)}")

    # Register services with proper schema validation
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        async_ask_question,
        schema=vol.Schema(SERVICE_SCHEMA_ASK_QUESTION)
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        async_clear_history,
        schema=vol.Schema({})
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SYSTEM_PROMPT,
        async_set_system_prompt,
        schema=vol.Schema(SERVICE_SCHEMA_SET_SYSTEM_PROMPT)
    )

    return True

async def async_check_api(session, endpoint: str, headers: dict, is_anthropic: bool = False) -> bool:
    """Check API availability for different providers."""
    try:
        # Определяем, является ли это VSE GPT endpoint
        is_vsegpt = "vsegpt" in endpoint.lower()

        if is_vsegpt:
            # Для VSE GPT используем специальный endpoint
            check_url = f"{endpoint.rstrip('/')}/v1/models"
            headers["Authorization"] = f"Bearer {headers.get('x-api-key', '')}"
        elif is_anthropic:
            check_url = f"{endpoint}/v1/models"
        else:
            check_url = f"{endpoint}/{API_VERSION}/{API_MODELS_PATH}"

        async with timeout(API_TIMEOUT):
            async with session.get(check_url, headers=headers) as response:
                if response.status == 200:
                    return True
                elif response.status == 404 and is_vsegpt:
                    # VSE GPT может возвращать 404 для /models endpoint
                    return True
                elif response.status == 401:
                    raise ConfigEntryNotReady("Invalid API key")
                elif response.status == 429:
                    _LOGGER.warning("Rate limit exceeded during API check")
                    return False
                else:
                    _LOGGER.error("API check failed with status: %d", response.status)
                    return False
    except Exception as ex:
        _LOGGER.error("API check error: %s", str(ex))
        return False

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Text AI from a config entry."""
    try:
        session = aiohttp_client.async_get_clientsession(hass)

        # Determine API type based on model and endpoint
        model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        endpoint = entry.data.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT).rstrip('/')
        api_key = entry.data[CONF_API_KEY]

        is_vsegpt = "vsegpt" in endpoint.lower()
        is_anthropic = any(m in model.lower() for m in ["claude", "anthropic"]) or is_vsegpt

        # Configure headers based on API type
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if is_vsegpt:
            headers["Authorization"] = f"Bearer {api_key}"
            if is_anthropic:
                headers["anthropic-version"] = "2023-06-01"
        elif is_anthropic:
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        # Check API with retries
        for attempt in range(API_RETRY_COUNT):
            if await async_check_api(session, endpoint, headers, is_anthropic):
                break
            if attempt < API_RETRY_COUNT - 1:
                delay = API_BACKOFF_FACTOR * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise ConfigEntryNotReady("Failed to connect to API")

        # Create coordinator
        try:
            # Create coordinator
            coordinator = HATextAICoordinator(
                hass,
                api_key=api_key,
                endpoint=endpoint,
                model=model,
                temperature=entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                max_tokens=entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                request_interval=entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),
                session=session,
                is_anthropic=is_anthropic
            )

            # Initialize the coordinator
            await coordinator.async_initialize()
            await coordinator.async_config_entry_first_refresh()

            # Store coordinator
            if DOMAIN not in hass.data:
                hass.data[DOMAIN] = {}
            hass.data[DOMAIN][entry.entry_id] = coordinator

            # Set up platforms
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

            return True

        except Exception as ex:
            _LOGGER.exception("Error initializing coordinator: %s", str(ex))
            raise ConfigEntryNotReady(f"Error initializing coordinator: {str(ex)}") from ex

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        coordinator = hass.data[DOMAIN].get(entry.entry_id)
        if coordinator:
            await coordinator.async_shutdown()

        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)

        return unload_ok

    except Exception as ex:
        _LOGGER.exception("Error unloading entry: %s", str(ex))
        return False
