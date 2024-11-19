"""The HA Text AI integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall, callback
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
            raise ConfigEntryNotReady from refresh_ex

        if not coordinator.last_update_success:
            raise ConfigEntryNotReady("Failed to communicate with OpenAI API")

        hass.data[DOMAIN][entry.entry_id] = coordinator

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        async def async_ask_question(call: ServiceCall) -> None:
            """Handle the ask_question service call."""
            question = call.data.get("question", "")
            if not question:
                _LOGGER.error("No question provided in service call")
                return

            # Собираем все опциональные параметры
            request_params = {}

            # Обработка system_prompt
            system_prompt = call.data.get("system_prompt")
            if system_prompt is not None:
                request_params["system_prompt"] = system_prompt

            # Обработка model
            model = call.data.get("model")
            if model is not None:
                request_params["model"] = model

            # Обработка temperature
            temperature = call.data.get("temperature")
            if temperature is not None:
                try:
                    request_params["temperature"] = float(temperature)
                except ValueError:
                    _LOGGER.error("Invalid temperature value: %s", temperature)
                    return

            # Обработка max_tokens
            max_tokens = call.data.get("max_tokens")
            if max_tokens is not None:
                try:
                    request_params["max_tokens"] = int(max_tokens)
                except ValueError:
                    _LOGGER.error("Invalid max_tokens value: %s", max_tokens)
                    return

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
                limit = call.data.get("limit", 10)
                filter_model = call.data.get("filter_model", "")

                responses = coordinator._responses

                # Применяем фильтрацию по модели
                if filter_model:
                    filtered_responses = {
                        k: v for k, v in responses.items()
                        if v.get("model") == filter_model
                    }
                else:
                    filtered_responses = responses.copy()

                # Сортируем по времени и ограничиваем количество
                sorted_responses = dict(
                    sorted(
                        filtered_responses.items(),
                        key=lambda x: x[1]["timestamp"],
                        reverse=True
                    )[:limit]
                )

                return sorted_responses
            except Exception as err:
                _LOGGER.error("Error getting history: %s", str(err))
                return {}

        async def async_set_system_prompt(call: ServiceCall) -> None:
            """Handle the set_system_prompt service call."""
            prompt = call.data.get("prompt", "")
            if prompt:
                try:
                    coordinator.system_prompt = prompt
                    _LOGGER.info("System prompt updated successfully")
                except Exception as err:
                    _LOGGER.error("Error setting system prompt: %s", str(err))
            else:
                _LOGGER.error("No prompt provided in service call")

        # Регистрация сервисов
        hass.services.async_register(
            DOMAIN,
            "ask_question",
            async_ask_question
        )

        hass.services.async_register(
            DOMAIN,
            "clear_history",
            async_clear_history
        )

        hass.services.async_register(
            DOMAIN,
            "get_history",
            async_get_history
        )

        hass.services.async_register(
            DOMAIN,
            "set_system_prompt",
            async_set_system_prompt
        )

        _LOGGER.info(
            "Successfully set up HA Text AI with model: %s",
            entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        )

        return True

    except Exception as ex:
        _LOGGER.exception("Unexpected error setting up entry: %s", str(ex))
        raise ConfigEntryNotReady from ex

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        if entry.entry_id not in hass.data.get(DOMAIN, {}):
            return True

        # Удаляем все сервисы при выгрузке интеграции
        services = ["ask_question", "clear_history", "get_history", "set_system_prompt"]
        for service in services:
            hass.services.async_remove(DOMAIN, service)

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
        _LOGGER.exception("Error reloading entry: %s", str(ex))  # убрано лишнее двоеточие
