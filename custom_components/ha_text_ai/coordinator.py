"""Data coordinator for HA text AI."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

import openai
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    DEFAULT_REQUEST_INTERVAL,
)

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

        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._question_queue = asyncio.Queue()
        self._responses: Dict[str, Any] = {}

        openai.api_key = self.api_key
        if endpoint != "https://api.openai.com/v1":
            openai.api_base = endpoint

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via OpenAI API."""
        if self._question_queue.empty():
            return self._responses

        try:
            question = await self._question_queue.get()
            response = await self.hass.async_add_executor_job(
                self._make_api_call, question
            )
            self._responses[question] = response
            return self._responses

        except openai.error.AuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            return self._responses

    def _make_api_call(self, question: str) -> str:
        """Make API call to OpenAI."""
        try:
            completion = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": question}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return completion.choices[0].message.content
        except Exception as err:
            _LOGGER.error("Error in API call: %s", err)
            raise

    async def async_ask_question(self, question: str) -> None:
        """Add question to queue."""
        await self._question_queue.put(question)
        await self.async_refresh()
