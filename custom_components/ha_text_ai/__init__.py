"""The HA Text AI integration."""
from __future__ import annotations

import logging
import os
import shutil
from typing import Any, Dict, Optional
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform
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
    CONF_API_PROVIDER,
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_OPENAI_ENDPOINT,
    DEFAULT_ANTHROPIC_ENDPOINT,
    DEFAULT_REQUEST_INTERVAL,
    API_TIMEOUT,
    SERVICE_ASK_QUESTION,
    SERVICE_CLEAR_HISTORY,
    SERVICE_GET_HISTORY,
    SERVICE_SET_SYSTEM_PROMPT,
    SERVICE_SCHEMA_ASK_QUESTION,
    SERVICE_SCHEMA_SET_SYSTEM_PROMPT,
    SERVICE_SCHEMA_GET_HISTORY,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

@callback
def get_coordinator_by_id(hass: HomeAssistant, entity_id: str) -> Optional[HATextAICoordinator]:
    """Get coordinator by entity ID."""
    if DOMAIN in hass.data:
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if coordinator.entity_id == entity_id:
                return coordinator
    return None

async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the HA Text AI component."""
    hass.data.setdefault(DOMAIN, {})

    # Copy custom icon
    try:
        source = os.path.join(os.path.dirname(__file__), 'icons', 'icon.svg')
        dest_dir = os.path.join(hass.config.path('www'), 'icons')
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, 'icon.svg')
        if not os.path.exists(dest):
            shutil.copyfile(source, dest)
    except Exception as ex:
        _LOGGER.warning("Failed to copy custom icon: %s", str(ex))

    async def async_ask_question(call: ServiceCall) -> None:
        """Handle ask_question service."""
        entity_id = call.target.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No target entity specified")

        coordinator = get_coordinator_by_id(hass, entity_id)
        if not coordinator:
            raise HomeAssistantError(f"No coordinator found for entity {entity_id}")

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
        entity_id = call.target.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No target entity specified")

        coordinator = get_coordinator_by_id(hass, entity_id)
        if not coordinator:
            raise HomeAssistantError(f"No coordinator found for entity {entity_id}")

        try:
            await coordinator.clear_history()
        except Exception as err:
            _LOGGER.error("Error clearing history: %s", str(err))
            raise HomeAssistantError(f"Failed to clear history: {str(err)}")

    async def async_get_history(call: ServiceCall) -> None:
        """Handle get_history service."""
        entity_id = call.target.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No target entity specified")

        coordinator = get_coordinator_by_id(hass, entity_id)
        if not coordinator:
            raise HomeAssistantError(f"No coordinator found for entity {entity_id}")

        try:
            limit = call.data.get("limit", 10)
            start_date = call.data.get("start_date")
            include_metadata = call.data.get("include_metadata", False)
            sort_order = call.data.get("sort_order", "desc")

            history = await coordinator.get_history(
                limit=limit,
                start_date=start_date,
                include_metadata=include_metadata,
                sort_order=sort_order
            )
            return history
        except Exception as err:
            _LOGGER.error("Error getting history: %s", str(err))
            raise HomeAssistantError(f"Failed to get history: {str(err)}")

    async def async_set_system_prompt(call: ServiceCall) -> None:
        """Handle set_system_prompt service."""
        entity_id = call.target.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No target entity specified")

        coordinator = get_coordinator_by_id(hass, entity_id)
        if not coordinator:
            raise HomeAssistantError(f"No coordinator found for entity {entity_id}")

        prompt = call.data.get("prompt")
        if not prompt:
            raise HomeAssistantError("No prompt provided")

        try:
            coordinator.update_system_prompt(prompt)
        except Exception as err:
            _LOGGER.error("Error setting system prompt: %s", str(err))
            raise HomeAssistantError(f"Failed to set system prompt: {str(err)}")

    # Base schema with target
    base_schema = vol.Schema({
        vol.Required("target"): {
            vol.Required("entity_id"): cv.entity_id
        }
    })

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        async_ask_question,
        schema=base_schema.extend(SERVICE_SCHEMA_ASK_QUESTION.schema)
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        async_clear_history,
        schema=base_schema
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_HISTORY,
        async_get_history,
        schema=base_schema.extend(SERVICE_SCHEMA_GET_HISTORY.schema)
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SYSTEM_PROMPT,
        async_set_system_prompt,
        schema=base_schema.extend(SERVICE_SCHEMA_SET_SYSTEM_PROMPT.schema)
    )

    return True

async def async_check_api(session, endpoint: str, headers: dict, provider: str) -> bool:
    """Check API availability for different providers."""
    try:
        if provider == API_PROVIDER_ANTHROPIC:
            check_url = f"{endpoint}/v1/models"
        else:  # OpenAI
            check_url = f"{endpoint}/models"

        async with timeout(API_TIMEOUT):
            async with session.get(check_url, headers=headers) as response:
                if response.status in [200, 404]:
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
        if CONF_API_PROVIDER not in entry.data:
            _LOGGER.error("API provider not specified")
            raise ConfigEntryNotReady("API provider is required")

        session = aiohttp_client.async_get_clientsession(hass)
        api_provider = entry.data.get(CONF_API_PROVIDER)
        model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        endpoint = entry.data.get(CONF_API_ENDPOINT,
            DEFAULT_OPENAI_ENDPOINT if api_provider == API_PROVIDER_OPENAI
            else DEFAULT_ANTHROPIC_ENDPOINT).rstrip('/')
        api_key = entry.data[CONF_API_KEY]

        is_anthropic = api_provider == API_PROVIDER_ANTHROPIC
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if is_anthropic:
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        if not await async_check_api(session, endpoint, headers, api_provider):
            raise ConfigEntryNotReady("API connection failed")

        coordinator = HATextAICoordinator(
            hass,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
            temperature=entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            max_tokens=entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            request_interval=float(entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)),
            name=entry.title or entry.data.get(CONF_NAME, "HA Text AI"),
            session=session,
            is_anthropic=is_anthropic
        )

        await coordinator.async_initialize()
        await coordinator.async_config_entry_first_refresh()

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True

    except Exception as ex:
        _LOGGER.exception("Setup error: %s", str(ex))
        raise ConfigEntryNotReady(f"Setup error: {str(ex)}") from ex

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
