"""The HA Text AI integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, PLATFORMS
from .coordinator import HATextAICoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Text AI from a config entry."""
    try:
        coordinator = HATextAICoordinator(
            hass,
            api_key=entry.data["api_key"],
            endpoint=entry.data.get("api_endpoint", "https://api.openai.com/v1"),
            model=entry.data.get("model", "gpt-3.5-turbo"),
            temperature=entry.data.get("temperature", 0.7),
            max_tokens=entry.data.get("max_tokens", 1000),
            request_interval=entry.data.get("request_interval", 1.0),
        )

        await coordinator.async_config_entry_first_refresh()

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        return await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as ex:
        raise ConfigEntryNotReady(f"Failed to setup entry: {str(ex)}") from ex

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

"""Data coordinator for HA text AI."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

import openai
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HATextAICoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        endpoint: str,
        model: str,
        temperature: float,
        max_tokens: int,
        request_interval: float,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=request_interval),
        )

        if not api_key:
            raise ValueError("API key is required")
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("Max tokens must be a positive integer")

        self.api_key = api_key
        self.endpoint = endpoint or "https://api.openai.com/v1"
        self.model = model or "gpt-3.5-turbo"
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self._question_queue = asyncio.Queue()
        self._responses: Dict[str, Any] = {}
        self.system_prompt: Optional[str] = None

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.endpoint
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via OpenAI API."""
        if self._question_queue.empty():
            return self._responses

        try:
            question = await self._question_queue.get()
            response_content = await self.hass.async_add_executor_job(
                self._make_api_call, question
            )
            self._responses[question] = {
                "question": question,
                "response": response_content
            }
            _LOGGER.debug("Response from API: %s", response_content)
            return self._responses

        except openai.AuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            return self._responses

    def _make_api_call(self, question: str) -> str:
        """Make API call to OpenAI."""
        try:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": question})

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return completion.choices[0].message.content
        except Exception as err:
            _LOGGER.error("Error in API call: %s", err)
            raise
