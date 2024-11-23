"""Data coordinator for HA text AI."""
import logging
import asyncio
from datetime import timedelta, datetime
from typing import Any, Dict, Optional, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import HomeAssistantError
import httpx
from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError
from anthropic import AsyncAnthropic

from .const import (
    DOMAIN,
    QUEUE_MAX_SIZE,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
)

_LOGGER = logging.getLogger(__name__)

class HATextAICoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def _validate_params(self, api_key: str, temperature: float, max_tokens: int) -> None:
        """Validate initialization parameters.

        Args:
            api_key: API key for authentication
            temperature: Sampling temperature for text generation
            max_tokens: Maximum number of tokens to generate

        Raises:
            ValueError: If any parameters are invalid
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        try:
            temp = float(temperature)
            if not 0 <= temp <= 2:
                raise ValueError("Temperature must be between 0 and 2")
        except (TypeError, ValueError):
            raise ValueError("Temperature must be a number between 0 and 2")

        try:
            tokens = int(max_tokens)
            if tokens < 1:
                raise ValueError("Max tokens must be a positive number")
        except (TypeError, ValueError):
            raise ValueError("Max tokens must be a positive integer")

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        endpoint: str,
        model: str,
        temperature: float,
        max_tokens: int,
        request_interval: float,
        name: str,
        session: Optional[Any] = None,
        is_anthropic: bool = False,
    ) -> None:
        """Initialize coordinator."""
        self._name = name
        self._validate_params(api_key, temperature, max_tokens)
        self._entity_id = None
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self._question_queue = asyncio.PriorityQueue(maxsize=QUEUE_MAX_SIZE)
        self._responses: Dict[str, Any] = {}
        self.system_prompt: Optional[str] = None
        self._is_ready = False
        self._is_processing = False
        self._is_rate_limited = False
        self._is_maintenance = False
        self._error_count = 0
        self._MAX_ERRORS = 3
        self._request_count = 0
        self._tokens_used = 0
        self._api_version = "v1"  # Keep single definition
        self._endpoint_status = "disconnected"
        self._last_error = None
        self._last_request_time = 0
        self._is_anthropic = is_anthropic
        self._session = session or aiohttp_client.async_get_clientsession(hass)
        self.client = None
        self.hass = hass  # Store hass reference for _init_client
        self._start_time = time.time()

        # History and metrics
        self._history: List[Dict[str, Any]] = []
        self._max_history_size = 100
        self._performance_metrics: Dict[str, Any] = {
            "avg_response_time": 0,
            "total_errors": 0,
            "success_rate": 100,
            "requests_per_minute": 0,
            "avg_tokens_per_request": 0,
        }

        super().__init__(
            hass,
            _LOGGER,
            name=self._name,
            update_interval=timedelta(seconds=float(request_interval)),
        )

    async def _init_client(self):
        """Initialize API client with proper SSL context."""
        try:
            if self._is_anthropic:
                self.client = AsyncAnthropic(
                    api_key=self.api_key
                )
            else:  # OpenAI
                # Create transport in separate thread
                transport = await self.hass.async_add_executor_job(
                    lambda: httpx.AsyncHTTPTransport(retries=3)
                )

                limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

                async_client = httpx.AsyncClient(
                    base_url=self.endpoint,
                    timeout=httpx.Timeout(30.0),
                    transport=transport,
                    limits=limits,
                    follow_redirects=True
                )

                self.client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.endpoint,
                    http_client=async_client,
                    max_retries=3
                )
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.error("Error initializing API client: %s", str(e))
            raise

    async def async_initialize(self) -> None:
        """Initialize coordinator."""
        try:
            await self._init_client()
            self._is_ready = True
            self._endpoint_status = "connected"
        except Exception as e:
            self._last_error = str(e)
            self._endpoint_status = "error"
            _LOGGER.error("Failed to initialize coordinator: %s", str(e))
            raise

    async def async_ask(
        self,
        question: str,
        priority: bool = False,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Add question to queue with priority."""
        if not self._is_ready:
            raise HomeAssistantError("Coordinator is not ready")

        if not question or not isinstance(question, str):
            raise ValueError("Invalid question format")

        # Validate optional parameters
        if temperature is not None and not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if max_tokens is not None and not isinstance(max_tokens, int):
            raise ValueError("max_tokens must be an integer")

        request_id = str(uuid.uuid4())

        request_params = {
            "id": request_id,
            "question": question,
            "system_prompt": system_prompt or self.system_prompt,
            "model": model or self.model,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "timestamp": dt_util.utcnow().isoformat(),
        }

        priority_level = 0 if priority else 1
        await self._question_queue.put((priority_level, request_id, request_params))

        # Wait for response
        while request_id not in self._responses:
            await asyncio.sleep(0.1)

        response = self._responses.pop(request_id)

        # Add to history
        history_entry = {
            "timestamp": request_params["timestamp"],
            "question": question,
            "response": response,
            "model": request_params["model"],
            "metadata": {
                "temperature": request_params["temperature"],
                "max_tokens": request_params["max_tokens"],
                "system_prompt": request_params["system_prompt"],
                "priority": priority,
            }
        }
        self._add_to_history(history_entry)

        return response

    async def _process_queue(self) -> None:
        """Process questions from queue."""
        while True:
            try:
                if self._is_rate_limited:
                    await asyncio.sleep(60)
                    self._is_rate_limited = False
                    continue

                priority, request_id, params = await self._question_queue.get()

                try:
                    response = await self._make_api_request(params)
                    self._responses[request_id] = response
                    self._update_metrics(response)
                except Exception as e:
                    self._last_error = str(e)
                    _LOGGER.error("Error processing request: %s", str(e))
                    self._responses[request_id] = f"Error: {str(e)}"
                finally:
                    self._question_queue.task_done()

            except Exception as e:
                self._last_error = str(e)
                _LOGGER.error("Queue processing error: %s", str(e))
                await asyncio.sleep(1)

    async def _make_api_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with retry logic."""
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                if self._is_anthropic:
                    response = await self._make_anthropic_call(**params)
                else:
                    response = await self._make_openai_call(**params)
                return response
            except (AuthenticationError, ValueError) as e:
                # Don't retry auth errors
                raise
            except RateLimitError:
                self._is_rate_limited = True
                await asyncio.sleep(RETRY_DELAY * (2 ** attempts))
                attempts += 1
            except Exception as e:
                attempts += 1
                if attempts >= MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_DELAY)

    async def _make_anthropic_call(self, **params) -> Dict[str, Any]:
        """Make API call to Anthropic."""
        start_time = time.time()
        messages = []
        if params.get("system_prompt"):
            messages.append({"role": "system", "content": params["system_prompt"]})
        messages.append({"role": "user", "content": params["question"]})

        try:
            completion = await self.client.messages.create(
                model=params.get("model", self.model),
                messages=messages,
                temperature=params.get("temperature", self.temperature),
                max_tokens=params.get("max_tokens", self.max_tokens),
            )

            response_time = time.time() - start_time

            return {
                "response": completion.content[0].text,
                "model": completion.model,
                "tokens": completion.usage.total_tokens if hasattr(completion, 'usage') else 0,
                "response_time": response_time
            }
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.error("Anthropic API call error: %s", str(e))
            raise

    async def _make_openai_call(self, **params) -> Dict[str, Any]:
        """Make API call to OpenAI."""
        start_time = time.time()
        try:
            if not params.get("question"):
                raise ValueError("Question cannot be empty")

            messages = []
            if params.get("system_prompt"):
                messages.append({"role": "system", "content": params["system_prompt"]})
            messages.append({"role": "user", "content": params["question"]})

            api_params = {
                "model": params.get("model", self.model),
                "messages": messages,
                "temperature": params.get("temperature", self.temperature),
                "max_tokens": params.get("max_tokens", self.max_tokens),
            }

            completion = await self.client.chat.completions.create(**api_params)
            response_time = time.time() - start_time

            if not completion.choices:
                raise ValueError("No response choices available")

            return {
                "response": completion.choices[0].message.content.strip(),
                "model": completion.model,
                "tokens": completion.usage.total_tokens,
                "response_time": response_time
            }

        except Exception as e:
            self._last_error = str(e)
            error_msg = f"OpenAI API call failed: {str(e)}"
            _LOGGER.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _add_to_history(self, entry: Dict[str, Any]) -> None:
        """Add entry to history with size limit."""
        self._history.append(entry)
        if len(self._history) > self._max_history_size:
            self._history.pop(0)

    async def get_history(
        self,
        limit: Optional[int] = None,
        start_date: Optional[datetime] = None,
        filter_model: Optional[str] = None,  # Добавляем параметр
        include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """Get conversation history."""
        history = self._history

        if start_date:
            history = [
                h for h in history
                if datetime.fromisoformat(h["timestamp"]) >= start_date
            ]

        # Добавляем фильтрацию по модели
        if filter_model:
            history = [h for h in history if h["model"] == filter_model]

        if not include_metadata:
            history = [{
                "timestamp": h["timestamp"],
                "question": h["question"],
                "response": h["response"],
                "model": h["model"]
            } for h in history]

        if limit and limit > 0:
            history = history[-limit:]

        return history

    def _update_metrics(self, response_data: Dict[str, Any]) -> None:
        """Update performance metrics."""
        # Update response time metrics
        response_time = response_data.get("response_time", 0)
        current_avg = self._performance_metrics["avg_response_time"]
        self._performance_metrics["avg_response_time"] = (
            (current_avg * self._request_count + response_time) /
            (self._request_count + 1)
        )

        # Update success rate
        total_requests = self._request_count + 1
        self._performance_metrics["success_rate"] = (
            (total_requests - self._performance_metrics["total_errors"]) /
            total_requests * 100
        )

        # Update tokens metrics
        tokens = response_data.get("tokens", 0)
        self._tokens_used += tokens
        self._performance_metrics["avg_tokens_per_request"] = (
            self._tokens_used / total_requests
        )

        # Calculate requests per minute
        if self._last_request_time:
            time_diff = time.time() - self._last_request_time
            if time_diff > 0:
                self._performance_metrics["requests_per_minute"] = 60 / time_diff

        self._last_request_time = time.time()
        self._request_count += 1

    async def async_refresh_metrics(self) -> None:
        """Refresh performance metrics."""
        try:
            self._performance_metrics.update({
                "queue_size": self._question_queue.qsize(),
                "last_update": dt_util.utcnow().isoformat(),
                "uptime": time.time() - self._start_time if hasattr(self, '_start_time') else 0,
                "memory_usage": {
                    "history_size": len(self._history),
                    "response_cache_size": len(self._responses)
                }
            })
        except Exception as e:
            _LOGGER.error("Error refreshing metrics: %s", str(e))

    async def export_metrics(self) -> Dict[str, Any]:
        """Export detailed metrics and statistics."""
        await self.async_refresh_metrics()
        return {
            "entity_id": self._entity_id,
            "performance": self._performance_metrics,
            "requests": {
                "total": self._request_count,
                "successful": self._request_count - self._performance_metrics["total_errors"],
                "failed": self._performance_metrics["total_errors"]
            },
            "tokens": {
                "total_used": self._tokens_used,
                "average_per_request": self._performance_metrics["avg_tokens_per_request"]
            },
            "status": {
                "is_ready": self.is_ready,
                "endpoint_status": self._endpoint_status,
                "error_count": self._error_count,
                "last_error": self._last_error
            },
            "queue": {
                "size": self.queue_size,
                "is_full": self.is_queue_full
            }
        }
    @property
    def is_ready(self) -> bool:
        """Return if coordinator is ready."""
        return self._is_ready

    @property
    def is_processing(self) -> bool:
        """Return if coordinator is processing."""
        return self._is_processing

    @property
    def is_rate_limited(self) -> bool:
        """Return if coordinator is rate limited."""
        return self._is_rate_limited

    @property
    def is_maintenance(self) -> bool:
        """Return if coordinator is in maintenance mode."""
        return self._is_maintenance

    @property
    def queue_size(self) -> int:
        """Return current queue size."""
        return self._question_queue.qsize()

    @property
    def is_queue_full(self) -> bool:
        """Return if queue is full."""
        return self.queue_size >= QUEUE_MAX_SIZE

    @property
    def last_error(self) -> Optional[str]:
        """Return last error message."""
        return self._last_error

    @property
    def endpoint_status(self) -> str:
        """Return endpoint connection status."""
        return self._endpoint_status

    async def async_start(self) -> None:
        """Start coordinator operations."""
        if not self._is_ready:
            await self.async_initialize()

        self._start_time = time.time()
        self._is_processing = True
        asyncio.create_task(self._process_queue())

    async def async_stop(self) -> None:
        """Stop coordinator operations."""
        self._is_processing = False
        self._is_ready = False
        # Clear queues and caches
        while not self._question_queue.empty():
            try:
                await self._question_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._responses.clear()

    async def async_reset(self) -> None:
        """Reset coordinator state."""
        await self.async_stop()
        self._error_count = 0
        self._request_count = 0
        self._tokens_used = 0
        self._last_error = None
        self._history.clear()
        self._performance_metrics = {
            "avg_response_time": 0,
            "total_errors": 0,
            "success_rate": 100,
            "requests_per_minute": 0,
            "avg_tokens_per_request": 0,
        }
        await self.async_start()

    async def async_clear_history(self) -> None:
        """Clear conversation history."""
        self._history.clear()

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        if not isinstance(prompt, str):
            raise ValueError("System prompt must be a string")
        self.system_prompt = prompt

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data from API."""
        try:
            await self.async_refresh_metrics()
            return {
                "status": self.endpoint_status,
                "metrics": self._performance_metrics,
                "last_update": dt_util.utcnow().isoformat()
            }
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.error("Error updating data: %s", str(e))
            raise HomeAssistantError(f"Error updating data: {str(e)}")

    async def __aenter__(self):
        """Async enter."""
        await self.async_start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit."""
        await self.async_stop()
