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
    CONF_MODEL,
    CONF_TEMPERATURE,
    CONF_MAX_TOKENS,
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
        self.system_prompt: Optional[str] = None

        openai.api_key = self.api_key
        if endpoint != "https://api.openai.com/v1":
            openai.api_base = endpoint

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via OpenAI API."""
        if self._question_queue.empty():
            return self._responses

        try:
            question = await self._question_queue.get()
            response_content = await self.hass.async_add_executor_job(
                self._make_api_call, question
            )
            response = {
                "question": question,
                "response": response_content
            }
            self._responses[question] = response
            _LOGGER.debug(f"Response from API: {response}")
            return self._responses

        except openai.error.AuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            return self._responses

    def _make_api_call(self, question: str) -> str:
        """Make API call to OpenAI."""
        try:
            messages = [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
            messages.append({"role": "user", "content": question})
            completion = openai.chat.completions.create(
                model=self.model,
                messages=messages,
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
        _LOGGER.debug(f"Question added to queue: {question}")
        await self.async_refresh()

    def clear_history(self) -> None:
        """Clear the stored question and response history."""
        self._responses.clear()
        _LOGGER.info("History cleared.")

    def get_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get the history of questions and responses."""
        return {"history": list(self._responses.values())[-limit:]}

    def set_system_prompt(self, prompt: str) -> None:
        """Set a system prompt that will be used for all future questions."""
        self.system_prompt = prompt
        _LOGGER.info(f"System prompt set: {prompt}")
