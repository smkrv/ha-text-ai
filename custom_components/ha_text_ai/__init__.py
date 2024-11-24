"""The HA Text AI integration."""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict

import voluptuous as vol
from async_timeout import timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import aiohttp_client

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
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SCHEMA_ASK_QUESTION = vol.Schema({
    vol.Required("instance"): cv.string,
    vol.Required("question"): cv.string,
    vol.Optional("system_prompt"): cv.string,
    vol.Optional("model"): cv.string,
    vol.Optional("temperature"): cv.positive_float,
    vol.Optional("max_tokens"): cv.positive_int,
})

SERVICE_SCHEMA_SET_SYSTEM_PROMPT = vol.Schema({
    vol.Required("instance"): cv.string,
    vol.Required("prompt"): cv.string,
})

SERVICE_SCHEMA_GET_HISTORY = vol.Schema({
    vol.Required("instance"): cv.string,
    vol.Optional("limit"): cv.positive_int,
    vol.Optional("filter_model"): cv.string,
})

async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the HA Text AI component."""
    hass.data.setdefault(DOMAIN, {})

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
        instance = call.data["instance"]
        coordinator = hass.data[DOMAIN].get(instance)
        if not coordinator:
            raise HomeAssistantError(f"Instance {instance} not found")

        try:
            await coordinator.async_ask_question(
                question=call.data["question"],
                model=call.data.get("model"),
                temperature=call.data.get("temperature"),
                max_tokens=call.data.get("max_tokens"),
                system_prompt=call.data.get("system_prompt"),
            )
        except Exception as err:
            _LOGGER.error("Error asking question: %s", str(err))
            raise HomeAssistantError(f"Failed to process question: {str(err)}")

    async def async_clear_history(call: ServiceCall) -> None:
        """Handle clear_history service."""
        instance = call.data["instance"]
        coordinator = hass.data[DOMAIN].get(instance)
        if not coordinator:
            raise HomeAssistantError(f"Instance {instance} not found")

        try:
            await coordinator.async_clear_history()
        except Exception as err:
            _LOGGER.error("Error clearing history: %s", str(err))
            raise HomeAssistantError(f"Failed to clear history: {str(err)}")

    async def async_get_history(call: ServiceCall) -> None:
        """Handle get_history service."""
        instance = call.data["instance"]
        coordinator = hass.data[DOMAIN].get(instance)
        if not coordinator:
            raise HomeAssistantError(f"Instance {instance} not found")

        try:
            return await coordinator.async_get_history(
                limit=call.data.get("limit"),
                filter_model=call.data.get("filter_model"),
                instance=instance
            )
        except Exception as err:
            _LOGGER.error("Error getting history: %s", str(err))
            raise HomeAssistantError(f"Failed to get history: {str(err)}")

    async def async_set_system_prompt(call: ServiceCall) -> None:
        """Handle set_system_prompt service."""
        instance = call.data["instance"]
        coordinator = hass.data[DOMAIN].get(instance)
        if not coordinator:
            raise HomeAssistantError(f"Instance {instance} not found")

        try:
            await coordinator.async_set_system_prompt(call.data["prompt"])
        except Exception as err:
            _LOGGER.error("Error setting system prompt: %s", str(err))
            raise HomeAssistantError(f"Failed to set system prompt: {str(err)}")

    hass.services.async_register(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        async_ask_question,
        schema=SERVICE_SCHEMA_ASK_QUESTION
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        async_clear_history,
        schema=vol.Schema({vol.Required("instance"): cv.string})
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_HISTORY,
        async_get_history,
        schema=SERVICE_SCHEMA_GET_HISTORY
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SYSTEM_PROMPT,
        async_set_system_prompt,
        schema=SERVICE_SCHEMA_SET_SYSTEM_PROMPT
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
        endpoint = entry.data.get(
            CONF_API_ENDPOINT,
            DEFAULT_OPENAI_ENDPOINT if api_provider == API_PROVIDER_OPENAI
            else DEFAULT_ANTHROPIC_ENDPOINT
        ).rstrip('/')
        api_key = entry.data[CONF_API_KEY]
        instance_name = entry.data.get(CONF_NAME, entry.entry_id)
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

        # Создаем API клиент
        api_client = {
            "session": session,
            "endpoint": endpoint,
            "headers": headers,
            "api_provider": api_provider,
            "model": model,
        }

        coordinator = HATextAICoordinator(
            hass=hass,
            client=api_client,
            model=model,
            update_interval=timedelta(
                seconds=entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)
            ),
            instance_name=instance_name,
            max_tokens=entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            temperature=entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            is_anthropic=is_anthropic,
        )

        # Инициализация координатора
        await coordinator.async_config_entry_first_refresh()

        # Сохраняем координатор
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Загружаем платформы
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True

    except Exception as ex:
        _LOGGER.exception("Setup error: %s", str(ex))
        raise ConfigEntryNotReady(f"Setup error: {str(ex)}") from ex

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        if entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][entry.entry_id]
            await coordinator.async_shutdown()
            hass.data[DOMAIN].pop(entry.entry_id)

        return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    except Exception as ex:
        _LOGGER.exception("Error unloading entry: %s", str(ex))
        return False
