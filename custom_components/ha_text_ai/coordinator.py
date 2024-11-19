"""Data coordinator for HA text AI."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import async_timeout

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
        session: Optional[Any] = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=request_interval),
        )

        self._validate_params(api_key, temperature, max_tokens)

        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self._question_queue = asyncio.Queue()
        self._responses: Dict[str, Any] = {}
        self.system_prompt: Optional[str] = None
        self._is_ready = False
        self._error_count = 0
        self._MAX_ERRORS = 3

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.endpoint,
            http_client=session,
        )

    def _validate_params(self, api_key: str, temperature: float, max_tokens: int) -> None:
        """Validate initialization parameters."""
        if not api_key:
            raise ValueError("API key is required")
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("Max tokens must be a positive integer")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via OpenAI API."""
        if self._question_queue.empty():
            return self._responses

        try:
            async with async_timeout.timeout(30):
                question = await self._question_queue.get()
                try:
                    response_content = await self._make_api_call(question)
                    self._responses[question] = {
                        "question": question,
                        "response": response_content,
                        "error": None,
                        "timestamp": self.hass.loop.time()
                    }
                    self._error_count = 0
                    self._is_ready = True
                    _LOGGER.debug("Response received for question: %s", question)

                except Exception as err:
                    self._handle_api_error(question, err)
                finally:
                    self._question_queue.task_done()

                return self._responses

        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout while processing question")
            await self._handle_timeout_error()
            return self._responses

    def _handle_api_error(self, question: str, error: Exception) -> None:
        """Handle API errors."""
        self._error_count += 1
        error_msg = str(error)

        if isinstance(error, AuthenticationError):
            error_msg = "Authentication failed - invalid API key"
            self._is_ready = False
        elif isinstance(error, RateLimitError):
            error_msg = "Rate limit exceeded"
        elif isinstance(error, APIError):
            error_msg = f"API error: {error}"

        self._responses[question] = {
            "question": question,
            "response": None,
            "error": error_msg,
            "timestamp": self.hass.loop.time()
        }

        _LOGGER.error("API error (%s): %s", type(error).__name__, error_msg)

        if self._error_count >= self._MAX_ERRORS:
            _LOGGER.warning(
                "Multiple errors occurred (%d). Coordinator needs attention.",
                self._error_count
            )

    async def _handle_timeout_error(self) -> None:
        """Handle timeout errors."""
        self._error_count += 1
        if not self._question_queue.empty():
            try:
                # Clear the queue if we have timeout issues
                while not self._question_queue.empty():
                    self._question_queue.get_nowait()
                    self._question_queue.task_done()
            except Exception as err:
                _LOGGER.error("Error clearing question queue: %s", err)

    async def _make_api_call(self, question: str) -> str:
        """Make API call to OpenAI."""
        try:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": question})

            completion = await self.client.chat.completions.create(
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
        if not self._is_ready and self._error_count >= self._MAX_ERRORS:
            _LOGGER.warning("Coordinator is not ready due to previous errors")
            return

        await self._question_queue.put(question)
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        try:
            # Clear the queue
            while not self._question_queue.empty():
                self._question_queue.get_nowait()
                self._question_queue.task_done()

            await self.client.close()
            self._is_ready = False

        except Exception as err:
            _LOGGER.error("Error during shutdown: %s", err)

    @property
    def is_ready(self) -> bool:
        """Return if coordinator is ready."""
        return self._is_ready

    @property
    def error_count(self) -> int:
        """Return current error count."""
        return self._error_count

    def reset_error_count(self) -> None:
        """Reset error counter."""
        self._error_count = 0
