"""Data coordinator for HA text AI."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Optional, List
import time
import ssl
import certifi
import aiohttp
import httpx

from homeassistant.helpers import aiohttp_client
from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError
from anthropic import AsyncAnthropic
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
import async_timeout

from .const import (
    DOMAIN,
    DEFAULT_TIMEOUT,
    QUEUE_MAX_SIZE,
    MAX_RETRIES,
    RETRY_DELAY,
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
        session: Optional[Any] = None,
        is_anthropic: bool = False,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=float(request_interval)),
        )

        self._validate_params(api_key, temperature, max_tokens)

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
        self._api_version = "v1"
        self._endpoint_status = "disconnected"
        self._performance_metrics: Dict[str, Any] = {
            "avg_response_time": 0,
            "total_errors": 0,
            "success_rate": 100,
            "requests_per_minute": 0,
        }
        self._last_request_time = 0
        self._is_anthropic = is_anthropic
        self._session = session or aiohttp_client.async_get_clientsession(hass)
        self.client = None  # Initialize client as None

    async def async_initialize(self) -> None:
        """Initialize coordinator."""
        try:
            await self._init_client()
            self._is_ready = True
            await self.async_refresh()
        except Exception as e:
            _LOGGER.error("Failed to initialize coordinator: %s", str(e))
            self._is_ready = False
            self._endpoint_status = "error"

    async def _create_ssl_context(self):
        """Create an async SSL context."""
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        return ssl_context

    async def _init_client(self):
        """Initialize API client with proper SSL context."""
        try:
            if self._is_anthropic:
                 self.client = AsyncAnthropic(
                     api_key=self.api_key
                 )
            else:  # OpenAI
                 transport = httpx.AsyncHTTPTransport(retries=3)
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
            _LOGGER.error("Error initializing API client: %s", str(e))
            raise

    def _validate_params(self, api_key: str, temperature: float, max_tokens: int) -> None:
        """Validate initialization parameters."""
        if not api_key:
            raise ValueError("API key is required")
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("Max tokens must be a positive integer")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via API."""
        # Возвращаем существующие ответы, если нет новых вопросов
        if self._question_queue.empty():
            return self._responses

        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT):
                self._is_processing = True

                try:
                    priority, question_data = await self._question_queue.get()
                    question = question_data["question"]
                    params = question_data["params"]

                    response_data = await self._make_api_call(
                        question,
                        model=params.get("model"),
                        temperature=params.get("temperature"),
                        max_tokens=params.get("max_tokens"),
                        system_prompt=params.get("system_prompt")
                    )

                    await self._handle_successful_response(
                        question, response_data, params, priority
                    )

                except asyncio.QueueEmpty:
                    # Если очередь пуста, просто возвращаем существующие ответы
                    return self._responses

                except asyncio.TimeoutError:
                    _LOGGER.error("Timeout while processing API request")
                    await self._handle_api_error(question, "Request timeout")

                except KeyError as ke:
                    _LOGGER.error("Invalid question data format: %s", str(ke))
                    await self._handle_api_error(question, f"Invalid data format: {ke}")

                except Exception as err:
                    _LOGGER.error("Error processing question: %s", str(err))
                    await self._handle_api_error(question, err)

                finally:
                    self._is_processing = False
                    self._question_queue.task_done()

        except Exception as e:
            _LOGGER.error("Critical error in _async_update_data: %s", str(e))
            self._is_ready = False
            self._endpoint_status = "error"

        return self._responses

    async def _handle_successful_response(self, question, response_data, params, priority):
        """Handle successful API response."""
        self._responses[question] = {
            "question": question,
            "response": response_data["response"],
            "error": None,
            "timestamp": dt_util.utcnow(),
            "model": response_data["model"],
            "temperature": params.get("temperature", self.temperature),
            "max_tokens": params.get("max_tokens", self.max_tokens),
            "response_time": response_data.get("response_time"),
            "tokens": response_data.get("tokens", 0),
            "priority": priority
        }

        self._error_count = 0
        self._is_ready = True
        self._endpoint_status = "connected"
        self._request_count += 1
        self._tokens_used += response_data.get("tokens", 0)
        self._last_request_time = time.time()

        # Fire event for successful response
        self.hass.bus.async_fire(f"{DOMAIN}_response_received", {
            "question": question,
            "model": response_data["model"],
            "tokens": response_data.get("tokens", 0)
        })

        _LOGGER.debug("Response received for question: %s", question)

    async def _handle_api_error(self, question: str, error: Exception) -> None:
        """Handle API errors with retry logic."""
        self._error_count += 1
        self._performance_metrics["total_errors"] += 1
        error_msg = str(error)

        if isinstance(error, AuthenticationError):
            error_msg = "Authentication failed - invalid API key"
            self._is_ready = False
            self._endpoint_status = "auth_error"
        elif isinstance(error, RateLimitError):
            error_msg = "Rate limit exceeded"
            self._is_rate_limited = True
            self._endpoint_status = "rate_limited"
            # Implement exponential backoff
            await asyncio.sleep(RETRY_DELAY * (2 ** (self._error_count - 1)))
        elif isinstance(error, APIError):
            if "maintenance" in str(error).lower():
                self._is_maintenance = True
                self._endpoint_status = "maintenance"
            error_msg = f"API error: {error}"
        else:
            self._endpoint_status = "error"

        self._responses[question] = {
            "question": question,
            "response": None,
            "error": error_msg,
            "timestamp": dt_util.utcnow(),
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        # Fire error event
        self.hass.bus.async_fire(f"{DOMAIN}_error_occurred", {
            "error_type": type(error).__name__,
            "error_message": error_msg,
            "question": question
        })

        _LOGGER.error("API error (%s): %s", type(error).__name__, error_msg)

        if self._error_count >= self._MAX_ERRORS:
            _LOGGER.warning(
                "Multiple errors occurred (%d). Coordinator needs attention.",
                self._error_count
            )

    def _update_metrics(self, response_data: Dict[str, Any]) -> None:
        """Update performance metrics."""
        response_time = response_data.get("response_time", 0)
        current_avg = self._performance_metrics["avg_response_time"]
        self._performance_metrics["avg_response_time"] = (
            (current_avg * self._request_count + response_time) /
            (self._request_count + 1)
        )

        total_requests = self._request_count + 1
        self._performance_metrics["success_rate"] = (
            (total_requests - self._performance_metrics["total_errors"]) /
            total_requests * 100
        )

        # Calculate requests per minute
        if self._last_request_time:
            time_diff = time.time() - self._last_request_time
            if time_diff > 0:
                self._performance_metrics["requests_per_minute"] = 60 / time_diff

    async def _make_api_call(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make API call to the selected service."""
        try:
            start_time = dt_util.utcnow()

            if self._is_anthropic:
                response = await self._make_anthropic_call(
                    question, model, temperature, max_tokens, system_prompt
                )
            else:
                response = await self._make_openai_call(
                    question, model, temperature, max_tokens, system_prompt
                )

            response_time = (dt_util.utcnow() - start_time).total_seconds()

            return {
                **response,
                "response_time": response_time
            }

        except Exception as err:
            _LOGGER.error("Error in API call: %s", err)
            raise

    async def _make_anthropic_call(
        self,
        question: str,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Make API call to Anthropic."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})

        completion = await self.client.messages.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )

        return {
            "response": completion.content[0].text,
            "model": completion.model,
            "tokens": completion.usage.total_tokens if hasattr(completion, 'usage') else 0
        }

    async def _make_openai_call(
        self,
        question: str,
        model: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Make API call to OpenAI."""
        completion = None
        try:
            # Input validation
            if not question:
                raise ValueError("Question cannot be empty")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": question})

            # Prepare API parameters
            api_params = {
                "model": model or self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            }

            _LOGGER.debug("Making OpenAI API call with parameters: %s", api_params)

            # Make API call
            completion = await self.client.chat.completions.create(**api_params)

            _LOGGER.debug("Raw API response: %s", completion)

            # Validate response
            if completion is None:
                raise ValueError("Received null response from API")

            if not hasattr(completion, 'choices') or not completion.choices:
                raise ValueError(f"No choices in API response: {completion}")

            if not completion.choices[0] or not hasattr(completion.choices[0], 'message'):
                raise ValueError(f"Invalid choice structure in response: {completion.choices}")

            message = completion.choices[0].message
            if not hasattr(message, 'content') or not message.content:
                raise ValueError(f"No content in message: {message}")

            response_text = message.content.strip()

            # Prepare response
            response = {
                "response": response_text,
                "model": getattr(completion, 'model', api_params['model']),
                "tokens": completion.usage.total_tokens if hasattr(completion, 'usage') else 0
            }

            _LOGGER.debug("Processed OpenAI response: %s", response)
            return response

        except Exception as e:
            _LOGGER.error("OpenAI API call error: %s", str(e))
            if completion:
                _LOGGER.debug("Failed response structure: %s", str(completion))
            _LOGGER.debug("Error details:", exc_info=True)

            # Добавляем контекст к ошибке
            error_context = {
                "question": question,
                "model": model or self.model,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
            _LOGGER.debug("Error context: %s", error_context)

            raise RuntimeError(f"OpenAI API call failed: {str(e)}") from e

    async def async_ask_question(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        priority: bool = False
    ) -> None:
        """Add question to queue with priority support."""
        try:
            if not self._is_ready and self._error_count >= self._MAX_ERRORS:
                _LOGGER.warning("Coordinator is not ready due to previous errors")
                return

            _LOGGER.debug("Processing question: %s with model: %s", question, model or self.model)

            question_data = {
                "question": question,
                "params": {
                    "system_prompt": system_prompt,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            }

            # Priority: 0 for high priority, 1 for normal
            priority_level = 0 if priority else 1

            await self._question_queue.put((priority_level, question_data))
            _LOGGER.debug("Question added to queue with priority %d", priority_level)


        except asyncio.QueueFull:
            _LOGGER.error("Question queue is full. Try again later.")
            raise RuntimeError("Queue is full")
        except Exception as e:
            _LOGGER.error("Error in async_ask_question: %s", str(e))
            raise


    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        try:
            while not self._question_queue.empty():
                try:
                    self._question_queue.get_nowait()
                    self._question_queue.task_done()
                except asyncio.QueueEmpty:
                    break

            if hasattr(self.client, 'close'):
                await self.client.close()
            elif hasattr(self.client, '_client') and hasattr(self.client._client, 'aclose'):
                await self.client._client.aclose()

            self._is_ready = False
            self._endpoint_status = "disconnected"

            # Final metrics update
            self._update_final_metrics()

        except Exception as err:
            _LOGGER.error("Error during shutdown: %s", err)

    def _update_final_metrics(self) -> None:
        """Update final metrics before shutdown."""
        self._performance_metrics["final_success_rate"] = (
            (self._request_count - self._performance_metrics["total_errors"]) /
            self._request_count * 100 if self._request_count > 0 else 0
        )
        self._performance_metrics["total_requests"] = self._request_count
        self._performance_metrics["total_tokens"] = self._tokens_used

    @property
    def performance_metrics(self) -> Dict[str, Any]:
        """Return current performance metrics."""
        return self._performance_metrics

    @property
    def queue_size(self) -> int:
        """Return current queue size."""
        return self._question_queue.qsize()

    @property
    def is_queue_full(self) -> bool:
        """Return whether queue is full."""
        return self._question_queue.full()

    @property
    def is_ready(self) -> bool:
        """Return if coordinator is ready."""
        return self._is_ready and self._error_count < self._MAX_ERRORS

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
        """Return if API is in maintenance."""
        return self._is_maintenance

    @property
    def error_count(self) -> int:
        """Return current error count."""
        return self._error_count

    @property
    def request_count(self) -> int:
        """Return total request count."""
        return self._request_count

    @property
    def tokens_used(self) -> int:
        """Return total tokens used."""
        return self._tokens_used

    @property
    def api_version(self) -> str:
        """Return API version."""
        return self._api_version

    @property
    def endpoint_status(self) -> str:
        """Return endpoint status."""
        return self._endpoint_status

    @property
    def responses(self) -> Dict[str, Any]:
        """Return all responses."""
        return self._responses

    @property
    def last_response(self) -> Optional[Dict[str, Any]]:
        """Return the last response."""
        if not self._responses:
            return None

        return list(self._responses.values())[-1]

    def reset_error_count(self) -> None:
        """Reset error counter."""
        self._error_count = 0
        self._is_rate_limited = False
        self._is_maintenance = False
        if not self._is_ready:
            self._is_ready = True
            self._endpoint_status = "connected"

    async def clear_queue(self) -> None:
        """Clear the question queue."""
        try:
            while not self._question_queue.empty():
                try:
                    self._question_queue.get_nowait()
                    self._question_queue.task_done()
                except asyncio.QueueEmpty:
                    break
        except Exception as err:
            _LOGGER.error("Error clearing queue: %s", err)

    async def clear_history(self) -> None:
        """Clear response history."""
        self._responses.clear()
        await self.async_refresh()

    def get_response(self, question: str) -> Optional[Dict[str, Any]]:
        """Get specific response by question."""
        return self._responses.get(question)

    def get_recent_responses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent responses."""
        return list(sorted(
            self._responses.values(),
            key=lambda x: x["timestamp"],
            reverse=True
        ))[:limit]

    async def retry_failed_requests(self) -> None:
        """Retry failed requests."""
        failed_requests = [
            (q, r) for q, r in self._responses.items()
            if r.get("error") is not None
        ]

        for question, response in failed_requests:
            await self.async_ask_question(
                question,
                system_prompt=response.get("system_prompt"),
                model=response.get("model"),
                temperature=response.get("temperature"),
                max_tokens=response.get("max_tokens"),
                priority=True
            )

    def update_system_prompt(self, new_prompt: str) -> None:
        """Update system prompt."""
        self.system_prompt = new_prompt
        _LOGGER.info("System prompt updated")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health_status = {
            "is_ready": self.is_ready,
            "is_processing": self.is_processing,
            "is_rate_limited": self.is_rate_limited,
            "is_maintenance": self.is_maintenance,
            "error_count": self.error_count,
            "endpoint_status": self.endpoint_status,
            "queue_size": self.queue_size,
            "request_count": self.request_count,
            "tokens_used": self.tokens_used,
            "performance_metrics": self.performance_metrics
        }

        return health_status

    async def _handle_timeout_error(self) -> None:
        """Handle timeout errors."""
        self._error_count += 1
        self._endpoint_status = "timeout"
        self._performance_metrics["total_errors"] += 1

        if not self._question_queue.empty():
            await self.clear_queue()

        # Fire timeout event
        self.hass.bus.async_fire(f"{DOMAIN}_timeout_error", {
            "error_count": self._error_count,
            "endpoint_status": self._endpoint_status
        })

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics and statistics."""
        return {
            "performance": self._performance_metrics,
            "requests": {
                "total": self._request_count,
                "successful": self._request_count - self._performance_metrics["total_errors"],
                "failed": self._performance_metrics["total_errors"]
            },
            "tokens": {
                "total_used": self._tokens_used,
                "average_per_request": self._tokens_used / self._request_count if self._request_count > 0 else 0
            },
            "status": {
                "is_ready": self.is_ready,
                "endpoint_status": self._endpoint_status,
                "error_count": self._error_count
            },
            "queue": {
                "size": self.queue_size,
                "is_full": self.is_queue_full
            }
        }

    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // 4

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit information."""
        return {
            "is_rate_limited": self._is_rate_limited,
            "retry_after": RETRY_DELAY * (2 ** (self._error_count - 1)) if self._is_rate_limited else 0
        }

    async def optimize_queue(self) -> None:
        """Optimize queue by removing duplicate requests."""
        if self._question_queue.empty():
            return

        seen_questions = set()
        optimized_queue = asyncio.PriorityQueue(maxsize=QUEUE_MAX_SIZE)

        while not self._question_queue.empty():
            try:
                priority, question_data = self._question_queue.get_nowait()
                question = question_data["question"]

                if question not in seen_questions:
                    seen_questions.add(question)
                    await optimized_queue.put((priority, question_data))

                self._question_queue.task_done()
            except asyncio.QueueEmpty:
                break

        self._question_queue = optimized_queue
