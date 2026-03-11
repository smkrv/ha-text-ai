"""
The HA Text AI integration.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import aiohttp_client

from .coordinator import HATextAICoordinator
from .api_client import APIClient
from .utils import safe_log_data, validate_endpoint
from .providers import get_default_endpoint, get_default_model, build_auth_headers
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_MAX_TOKENS,
    CONF_API_ENDPOINT,
    CONF_REQUEST_INTERVAL,
    CONF_API_TIMEOUT,
    CONF_API_PROVIDER,
    CONF_CONTEXT_MESSAGES,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_DEEPSEEK,
    API_PROVIDER_GEMINI,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_REQUEST_INTERVAL,
    DEFAULT_API_TIMEOUT,
    DEFAULT_CONTEXT_MESSAGES,
    SERVICE_ASK_QUESTION,
    SERVICE_CLEAR_HISTORY,
    SERVICE_GET_HISTORY,
    SERVICE_SET_SYSTEM_PROMPT,
    DEFAULT_MAX_HISTORY,
    CONF_MAX_HISTORY_SIZE,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SCHEMA_ASK_QUESTION = vol.Schema({
    vol.Required("instance"): cv.string,
    vol.Required("question"): vol.All(cv.string, vol.Length(min=1, max=100000)),
    vol.Optional("system_prompt"): vol.All(cv.string, vol.Length(max=50000)),
    vol.Optional("model"): cv.string,
    vol.Optional("temperature"): vol.All(
        vol.Coerce(float), vol.Range(min=0.0, max=2.0)
    ),
    vol.Optional("max_tokens"): cv.positive_int,
    vol.Optional("context_messages"): cv.positive_int,
    vol.Optional("structured_output", default=False): cv.boolean,
    vol.Optional("json_schema"): vol.All(cv.string, vol.Length(max=50000)),
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

async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
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
                structured_output=call.data.get("structured_output", False),
                json_schema=call.data.get("json_schema"),
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
                "error": "Service call failed"
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
        supports_response=SupportsResponse.OPTIONAL
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
        schema=SERVICE_SCHEMA_GET_HISTORY,
        supports_response=SupportsResponse.OPTIONAL
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SYSTEM_PROMPT,
        async_set_system_prompt,
        schema=SERVICE_SCHEMA_SET_SYSTEM_PROMPT
    )

    return True

async def async_check_api(session, endpoint: str, headers: dict, provider: str, api_timeout: int = DEFAULT_API_TIMEOUT) -> bool:
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

        async with asyncio.timeout(api_timeout):
            async with session.get(check_url, headers=headers) as response:
                if response.status == 200:
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
    _LOGGER.debug("Setting up HA Text AI entry: %s", safe_log_data(dict(entry.data)))

    try:
        # Get provider from data or options (options takes precedence)
        config = {**entry.data, **entry.options}
        api_provider = config.get(CONF_API_PROVIDER)

        if not api_provider:
            _LOGGER.error("API provider not specified")
            raise ConfigEntryNotReady("API provider is required")

        session = aiohttp_client.async_get_clientsession(hass)

        model = config.get(CONF_MODEL, get_default_model(api_provider))
        raw_endpoint = config.get(CONF_API_ENDPOINT, get_default_endpoint(api_provider))
        try:
            endpoint = validate_endpoint(raw_endpoint)
        except ValueError as err:
            _LOGGER.error("Invalid API endpoint %s: %s", raw_endpoint, err)
            raise ConfigEntryNotReady(f"Invalid API endpoint: {err}")
        # API key can now be updated via options
        api_key = config.get(CONF_API_KEY, entry.data.get(CONF_API_KEY))
        instance_name = entry.data.get(CONF_NAME, entry.entry_id)
        request_interval = config.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL)
        api_timeout = config.get(CONF_API_TIMEOUT, DEFAULT_API_TIMEOUT)
        max_tokens = config.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        temperature = config.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        max_history_size = config.get(CONF_MAX_HISTORY_SIZE, DEFAULT_MAX_HISTORY)
        context_messages = config.get(CONF_CONTEXT_MESSAGES, DEFAULT_CONTEXT_MESSAGES)
        is_anthropic = api_provider == API_PROVIDER_ANTHROPIC

        headers = build_auth_headers(api_provider, api_key)

        if not await async_check_api(session, endpoint, headers, api_provider, api_timeout):
            raise ConfigEntryNotReady("API connection failed")

        _LOGGER.debug("Creating API client for %s with endpoint %s", api_provider, endpoint)

        api_client = APIClient(
            session=session,
            endpoint=endpoint,
            headers=headers,
            api_provider=api_provider,
            model=model,
            api_timeout=api_timeout,
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
            api_timeout=api_timeout,
        )

        # Initialize coordinator (directories, history, metrics)
        await coordinator.async_initialize()

        _LOGGER.debug("Created coordinator for %s", instance_name)

        # Store coordinator
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        _LOGGER.debug("Stored coordinator in hass.data[%s][%s]", DOMAIN, entry.entry_id)

        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register update listener for options changes
        entry.async_on_unload(entry.add_update_listener(async_update_options))

        _LOGGER.debug("Setup completed for %s", instance_name)

        return True

    except Exception as err:
        _LOGGER.exception("Error setting up HA Text AI: %s", err)
        raise

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the config entry."""
    _LOGGER.info("Options updated for %s, reloading integration", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)


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
