"""
The HA Text AI integration.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import logging
import os
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, TypeVar

import voluptuous as vol
from async_timeout import timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import aiohttp_client

from .coordinator import HATextAICoordinator
from .api_client import APIClient
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_MAX_TOKENS,
    CONF_API_ENDPOINT,
    CONF_REQUEST_INTERVAL,
    CONF_API_PROVIDER,
    CONF_CONTEXT_MESSAGES,
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_DEEPSEEK,
    API_PROVIDER_GEMINI,
    DEFAULT_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_OPENAI_ENDPOINT,
    DEFAULT_ANTHROPIC_ENDPOINT,
    DEFAULT_DEEPSEEK_ENDPOINT,
    DEFAULT_GEMINI_ENDPOINT,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_CONTEXT_MESSAGES,
    API_TIMEOUT,
    SERVICE_ASK_QUESTION,
    SERVICE_CLEAR_HISTORY,
    SERVICE_GET_HISTORY,
    SERVICE_SET_SYSTEM_PROMPT,
    DEFAULT_MAX_HISTORY,
    CONF_MAX_HISTORY_SIZE,
    ICONS_SUBDOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
ConfigType = TypeVar("ConfigType", bound=Dict[str, Any])

SERVICE_SCHEMA_ASK_QUESTION = vol.Schema({
    vol.Required("instance"): cv.string,
    vol.Required("question"): cv.string,
    vol.Optional("system_prompt"): cv.string,
    vol.Optional("model"): cv.string,
    vol.Optional("temperature"): cv.positive_float,
    vol.Optional("max_tokens"): cv.positive_int,
    vol.Optional("context_messages"): cv.positive_int,
})

SERVICE_SCHEMA_SET_SYSTEM_PROMPT = vol.Schema({
    vol.Required("instance"): cv.string,
    vol.Required("prompt"): cv.string,
})

SERVICE_SCHEMA_GET_HISTORY = vol.Schema({
    vol.Required("instance"): cv.string,
    vol.Optional("limit"): cv.positive_int,
    vol.Optional("filter_model"): cv.string,
    vol.Optional("start_date"): cv.string,
    vol.Optional("include_metadata"): cv.boolean,
    vol.Optional("sort_order"): vol.In(["newest", "oldest"]),
})

def get_coordinator_by_instance(hass: HomeAssistant, instance: str) -> HATextAICoordinator:
    """Get coordinator by instance name."""
    if instance.startswith("sensor."):
        instance = instance.replace("sensor.ha_text_ai_", "", 1)

    for entry_id, coord in hass.data[DOMAIN].items():
        if isinstance(coord, HATextAICoordinator) and coord.instance_name.lower() == instance.lower():
            return coord

    raise HomeAssistantError(f"Instance {instance} not found")

def get_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Home Assistant Text AI component."""
    # Initialize domain data storage
    hass.data.setdefault(DOMAIN, {})

    async def async_ask_question(call: ServiceCall) -> dict:
        """Handle ask_question service with response data."""
        try:
            coordinator = get_coordinator_by_instance(hass, call.data["instance"])
            response = await coordinator.async_ask_question(
                question=call.data["question"],
                model=call.data.get("model"),
                temperature=call.data.get("temperature"),
                max_tokens=call.data.get("max_tokens"),
                system_prompt=call.data.get("system_prompt"),
                context_messages=call.data.get("context_messages"),
            )
            
            # Return structured response data
            return {
                "response_text": response.get("content", ""),
                "tokens_used": response.get("tokens", {}).get("total", 0),
                "prompt_tokens": response.get("tokens", {}).get("prompt", 0),
                "completion_tokens": response.get("tokens", {}).get("completion", 0),
                "model_used": response.get("model", call.data.get("model", coordinator.model)),
                "instance": call.data["instance"],
                "question": call.data["question"],
                "timestamp": response.get("timestamp"),
                "success": True
            }
        except Exception as err:
            _LOGGER.error("Error asking question: %s", str(err))
            # Return error response
            return {
                "response_text": "",
                "tokens_used": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "model_used": call.data.get("model", ""),
                "instance": call.data["instance"],
                "question": call.data["question"],
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(err)
            }

    async def async_clear_history(call: ServiceCall) -> None:
        """Handle clear_history service."""
        try:
            coordinator = get_coordinator_by_instance(hass, call.data["instance"])
            await coordinator.async_clear_history()
        except Exception as err:
            _LOGGER.error("Error clearing history: %s", str(err))
            raise HomeAssistantError(f"Failed to clear history: {str(err)}")

    async def async_get_history(call: ServiceCall) -> list:
        """Handle get_history service."""
        try:
            coordinator = get_coordinator_by_instance(hass, call.data["instance"])
            return await coordinator.async_get_history(
                limit=call.data.get("limit"),
                filter_model=call.data.get("filter_model"),
                start_date=call.data.get("start_date"),
                include_metadata=call.data.get("include_metadata", False),
                sort_order=call.data.get("sort_order", "newest")
            )
        except Exception as err:
            _LOGGER.error("Error getting history: %s", str(err))
            raise HomeAssistantError(f"Failed to get history: {str(err)}")

    async def async_set_system_prompt(call: ServiceCall) -> None:
        """Handle set_system_prompt service."""
        try:
            coordinator = get_coordinator_by_instance(hass, call.data["instance"])
            await coordinator.async_set_system_prompt(call.data["prompt"])
        except Exception as err:
            _LOGGER.error("Error setting system prompt: %s", str(err))
            raise HomeAssistantError(f"Failed to set system prompt: {str(err)}")

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        async_ask_question,
        schema=SERVICE_SCHEMA_ASK_QUESTION,
        supports_response=True
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

    # Handle icons
    try:
        source_icon_path = os.path.join(
            os.path.dirname(__file__),
            ICONS_SUBDOMAIN,
            'icon@2x.png'
        )

        destination_directory = os.path.join(
            hass.config.path('www'),
            DOMAIN,
            ICONS_SUBDOMAIN
        )

        destination_icon_path = os.path.join(
            destination_directory,
            'icon.png'
        )

        if not os.path.exists(source_icon_path):
            _LOGGER.error("Source icon not found: %s", source_icon_path)
            return True

        def create_directory():
            os.makedirs(destination_directory, exist_ok=True)

        await hass.async_add_executor_job(create_directory)

        should_copy = True

        if os.path.exists(destination_icon_path):
            source_hash = await hass.async_add_executor_job(get_file_hash, source_icon_path)
            dest_hash = await hass.async_add_executor_job(get_file_hash, destination_icon_path)
            should_copy = source_hash != dest_hash

        if should_copy:
            def copy_file():
                shutil.copyfile(source_icon_path, destination_icon_path)

            await hass.async_add_executor_job(copy_file)
            _LOGGER.debug("Icon updated: %s", destination_icon_path)

    except PermissionError as e:
        _LOGGER.error("Permission denied when managing icons: %s", str(e))
    except Exception as e:
        _LOGGER.error("Failed to manage icons: %s", str(e))

    return True

async def async_check_api(session, endpoint: str, headers: dict, provider: str) -> bool:
    """Check API availability for different providers."""
    try:
        if provider == API_PROVIDER_GEMINI:
            # Gemini API does not support GET /models for validation, just check key presence
            if headers.get("Authorization", "").replace("Bearer ", ""):
                return True
            else:
                _LOGGER.error("Gemini API key is missing or empty")
                return False
        elif provider == API_PROVIDER_ANTHROPIC:
            check_url = f"{endpoint}/v1/models"
        elif provider == API_PROVIDER_DEEPSEEK:
            check_url = f"{endpoint}/models"
        else:  # OpenAI
            check_url = f"{endpoint}/models"

        async with timeout(API_TIMEOUT):
            async with session.get(check_url, headers=headers) as response:
                if response.status in [200, 404]:
                    return True
                elif response.status == 401:
                    _LOGGER.error("Invalid API key")
                    return False
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
    _LOGGER.debug(f"Setting up HA Text AI entry: {entry.data}")

    try:
        if CONF_API_PROVIDER not in entry.data:
            _LOGGER.error("API provider not specified")
            raise ConfigEntryNotReady("API provider is required")

        # Get configuration
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
        request_interval = entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)
        max_tokens = entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        temperature = entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        max_history_size = entry.data.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY)
        context_messages = entry.data.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES)
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

        _LOGGER.debug("Creating API client for %s with endpoint %s", api_provider, endpoint)

        api_client = APIClient(
            session=session,
            endpoint=endpoint,
            headers=headers,
            api_provider=api_provider,
            model=model,
        )

        coordinator = HATextAICoordinator(
            hass=hass,
            client=api_client,
            model=model,
            update_interval=request_interval,
            instance_name=instance_name,
            max_tokens=max_tokens,
            temperature=temperature,
            max_history_size=max_history_size,
            context_messages=context_messages,
            is_anthropic=is_anthropic,
        )

        _LOGGER.debug(f"Created coordinator for {instance_name}")

        # Store coordinator
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        _LOGGER.debug(f"Stored coordinator in hass.data[{DOMAIN}][{entry.entry_id}]")

        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.debug(f"Setup completed for {instance_name}")

        return True

    except Exception as err:
        _LOGGER.exception(f"Error setting up HA Text AI: {err}")
        raise

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        if entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][entry.entry_id]

            if hasattr(coordinator.client, 'shutdown'):
                await coordinator.client.shutdown()

            await coordinator.async_shutdown()
            hass.data[DOMAIN].pop(entry.entry_id)

        return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    except Exception as ex:
        _LOGGER.exception("Error unloading entry: %s", str(ex))
        return False
