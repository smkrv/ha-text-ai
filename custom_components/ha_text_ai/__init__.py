"""The HA Text AI integration."""
import logging
from typing import Any, Dict, Optional
import asyncio
import voluptuous as vol
import json
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import config_validation as cv
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
    API_CHAT_PATH,
    API_TIMEOUT,
    API_RETRY_COUNT,
    API_BACKOFF_FACTOR,
    LOGGER_NAME,
    STATE_ERROR,
    STATE_READY,
    STATE_PROCESSING,
    STATE_RATE_LIMITED,
    STATE_MAINTENANCE,
    STATE_DISCONNECTED,
    STATE_RETRYING,
    STATE_QUEUED,
    STATE_UPDATING,
    SUPPORTED_MODELS,
    EVENT_RESPONSE_RECEIVED,
    EVENT_ERROR_OCCURRED,
    EVENT_STATE_CHANGED,
)

_LOGGER = logging.getLogger(LOGGER_NAME)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Service validation schemas
SERVICE_SCHEMA_ASK_QUESTION = vol.Schema({
    vol.Required("question"): cv.string,
    vol.Optional("system_prompt"): cv.string,
    vol.Optional("model"): vol.In(SUPPORTED_MODELS),
    vol.Optional("temperature"): vol.All(
        vol.Coerce(float), vol.Range(min=0, max=2)
    ),
    vol.Optional("max_tokens"): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=4096)
    ),
    vol.Optional("priority"): vol.Boolean,
})

SERVICE_SCHEMA_GET_HISTORY = vol.Schema({
    vol.Optional("limit", default=10): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=100)
    ),
    vol.Optional("filter_model"): vol.In(SUPPORTED_MODELS),
    vol.Optional("start_date"): cv.datetime,
    vol.Optional("include_metadata"): vol.Boolean,
})

SERVICE_SCHEMA_SET_SYSTEM_PROMPT = vol.Schema({
    vol.Required("prompt"): cv.string,
})

async def async_check_api(session, endpoint: str, headers: dict, is_anthropic: bool = False) -> bool:
    """Check API availability for different providers."""
    try:
        if is_anthropic:
            check_url = f"{endpoint}/v1/models"
        else:
            check_url = f"{endpoint}/{API_VERSION}/{API_MODELS_PATH}"

        async with timeout(API_TIMEOUT):
            async with session.get(check_url, headers=headers) as response:
                if response.status == 200:
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

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the HA Text AI component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Text AI from a config entry."""
    try:
        session = aiohttp_client.async_get_clientsession(hass)

        # Determine API type based on model
        model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        is_anthropic = any(m in model.lower() for m in ["claude", "anthropic"])

        api_key = entry.data[CONF_API_KEY]
        endpoint = entry.data.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT).rstrip('/')

        # Configure headers based on API type
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if is_anthropic:
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

        # Perform first refresh
        await coordinator.async_config_entry_first_refresh()

        # Check coordinator status
        if coordinator.endpoint_status == "auth_error":
            raise ConfigEntryNotReady("Authentication failed")
        elif coordinator.endpoint_status == "rate_limited":
            _LOGGER.warning("API rate limited during setup")
        elif coordinator.endpoint_status == "maintenance":
            raise ConfigEntryNotReady("API is in maintenance mode")
        elif coordinator.endpoint_status == "error":
            raise ConfigEntryNotReady("API error during setup")
        elif not coordinator.last_update_success:
            raise ConfigEntryNotReady("Failed to initialize coordinator")

        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register event handlers
        @callback
        def handle_state_change(event):
            """Handle state changes."""
            if event.data.get("entity_id").startswith(f"{DOMAIN}."):
                _LOGGER.debug("State changed: %s", event.data)

        hass.bus.async_listen(EVENT_STATE_CHANGED, handle_state_change)

        # Register services
        async def async_ask_question(call: ServiceCall) -> None:
            """Handle the ask_question service call."""
            question = call.data.get("question", "")
            if not question:
                _LOGGER.error("No question provided in service call")
                return

            request_params = {}
            for param in ["system_prompt", "model", "temperature", "max_tokens"]:
                if param in call.data:
                    request_params[param] = call.data[param]

            try:
                await coordinator.async_ask_question(question, **request_params)
                except Exception as err:
                    _LOGGER.error("Error asking question: %s", str(err))

        async def async_clear_history(call: ServiceCall) -> None:
            """Handle the clear_history service call."""
            try:
                coordinator._responses.clear()
                await coordinator.async_refresh()
                _LOGGER.info("History cleared successfully")
            except Exception as err:
                _LOGGER.error("Error clearing history: %s", str(err))

        async def async_get_history(call: ServiceCall) -> dict:
            """Handle the get_history service call."""
            try:
                limit = min(int(call.data.get("limit", 10)), 100)
                filter_model = str(call.data.get("filter_model", ""))
                start_date = call.data.get("start_date")
                include_metadata = call.data.get("include_metadata", False)

                responses = coordinator._responses
                metrics = {
                    "total_requests": coordinator.request_count,
                    "total_tokens": coordinator.tokens_used,
                    "api_version": coordinator.api_version,
                    "endpoint_status": coordinator.endpoint_status,
                    "error_count": coordinator.error_count
                }

                filtered_responses = responses.copy()

                if filter_model:
                    filtered_responses = {
                        k: v for k, v in filtered_responses.items()
                        if v.get("model") == filter_model
                    }

                if start_date:
                    filtered_responses = {
                        k: v for k, v in filtered_responses.items()
                        if v.get("timestamp") >= start_date
                    }

                if not include_metadata:
                    filtered_responses = {
                        k: {
                            "question": v["question"],
                            "response": v["response"],
                            "timestamp": v["timestamp"]
                        } for k, v in filtered_responses.items()
                    }

                sorted_responses = dict(
                    sorted(
                        filtered_responses.items(),
                        key=lambda x: x[1]["timestamp"],
                        reverse=True
                    )[:limit]
                )

                return {
                    "metrics": metrics,
                    "responses": sorted_responses
                }
            except Exception as err:
                _LOGGER.error("Error getting history: %s", str(err))
                return {}

        async def async_set_system_prompt(call: ServiceCall) -> None:
            """Handle the set_system_prompt service call."""
            try:
                prompt = str(call.data.get("prompt", "")).strip()
                if prompt:
                    coordinator.system_prompt = prompt
                    _LOGGER.info("System prompt updated successfully")
                else:
                    _LOGGER.error("Empty prompt provided")
            except Exception as err:
                _LOGGER.error("Error setting system prompt: %s", str(err))

        # Register services with validation
        hass.services.async_register(
            DOMAIN,
            "ask_question",
            async_ask_question,
            schema=SERVICE_SCHEMA_ASK_QUESTION
        )

        hass.services.async_register(
            DOMAIN,
            "clear_history",
            async_clear_history
        )

        hass.services.async_register(
            DOMAIN,
            "get_history",
            async_get_history,
            schema=SERVICE_SCHEMA_GET_HISTORY
        )

        hass.services.async_register(
            DOMAIN,
            "set_system_prompt",
            async_set_system_prompt,
            schema=SERVICE_SCHEMA_SET_SYSTEM_PROMPT
        )

        _LOGGER.info(
            "Successfully set up HA Text AI with model: %s",
            entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        )

        return True

    except Exception as ex:
        _LOGGER.exception("Setup error: %s", str(ex))
        raise ConfigEntryNotReady from ex

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        coordinator = hass.data[DOMAIN].get(entry.entry_id)
        if coordinator:
            # Clear queue and history
            coordinator._responses.clear()
            while not coordinator._question_queue.empty():
                try:
                    coordinator._question_queue.get_nowait()
                    coordinator._question_queue.task_done()
                except Exception:
                    pass

            # Properly close the client
            if hasattr(coordinator, 'client'):
                await coordinator.client.aclose()

            # Close connection
            await coordinator.async_shutdown()

        # Remove services
        for service in ["ask_question", "clear_history", "get_history", "set_system_prompt"]:
            hass.services.async_remove(DOMAIN, service)

        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)

        return unload_ok

    except Exception as ex:
        _LOGGER.exception("Error unloading entry: %s", str(ex))
        return False

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        new = {**entry.data}

        # Migrate settings
        if CONF_MODEL in new and new[CONF_MODEL] not in SUPPORTED_MODELS:
            new[CONF_MODEL] = DEFAULT_MODEL

        entry.version = 2
        hass.config_entries.async_update_entry(entry, data=new)

    return True
