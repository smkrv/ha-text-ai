"""Data coordinator for HA text AI."""
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

class HATextAICoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,
        model: str,
        update_interval: int,
        instance_name: str,  # Добавляем идентификатор интеграции
        max_tokens: int = 1000,
        temperature: float = 0.7,
        max_history_size: int = 50,
        is_anthropic: bool = False,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"HA Text AI {instance_name}",  # Уникальное имя для каждой интеграции
            update_interval=update_interval,
        )

        self.instance_name = instance_name  # Сохраняем идентификатор
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._max_history_size = max_history_size
        self._is_anthropic = is_anthropic
        self._system_prompt = None

        # Статусы
        self._is_processing = False
        self._is_rate_limited = False
        self._is_maintenance = False

        # История и метрики
        self._history: List[Dict[str, Any]] = []
        self._request_count = 0
        self._error_count = 0
        self._last_error = None
        self._performance_metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "avg_response_time": 0.0,
            "last_request_time": None,
        }

        # Версия API и последний ответ
        self.api_version = "v1"
        self.last_response = None
        self.endpoint_status = "initialized"

    @property
    def is_processing(self) -> bool:
        """Return True if currently processing a request."""
        return self._is_processing

    @property
    def is_rate_limited(self) -> bool:
        """Return True if currently rate limited."""
        return self._is_rate_limited

    @property
    def is_maintenance(self) -> bool:
        """Return True if in maintenance mode."""
        return self._is_maintenance

    async def async_ask_question(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Process a question with optional parameters."""
        try:
            temp_model = model or self.model
            temp_temperature = temperature or self.temperature
            temp_max_tokens = max_tokens or self.max_tokens
            temp_system_prompt = system_prompt or self._system_prompt

            messages = []
            if temp_system_prompt:
                messages.append({"role": "system", "content": temp_system_prompt})
            messages.append({"role": "user", "content": question})

            kwargs = {
                "model": temp_model,
                "temperature": temp_temperature,
                "max_tokens": temp_max_tokens,
                "messages": messages,
            }

            return await self.async_process_message(question, **kwargs)

        except Exception as err:
            _LOGGER.error("Error processing question: %s", err)
            raise HomeAssistantError(f"Failed to process question: {err}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data from API."""
        try:
            await self.async_refresh_metrics()
            return {
                "status": self.endpoint_status,
                "metrics": self._performance_metrics,
                "last_update": dt_util.utcnow().isoformat(),
                "last_response": self.last_response,
                "is_processing": self._is_processing,
                "is_rate_limited": self._is_rate_limited,
                "is_maintenance": self._is_maintenance,
                "instance": self.instance_name,  # Добавляем идентификатор интеграции
            }
        except Exception as e:
            self._last_error = str(e)
            self._error_count += 1
            _LOGGER.error("Error updating data: %s", str(e))
            raise HomeAssistantError(f"Error updating data: {str(e)}")

    async def async_refresh_metrics(self) -> None:
        """Refresh performance metrics."""
        self._performance_metrics.update({
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "last_request_time": dt_util.utcnow().isoformat(),
            "instance": self.instance_name,  # Добавляем идентификатор интеграции
        })

    async def async_process_message(self, message: str, **kwargs) -> dict:
        """Process message and update last_response."""
        try:
            self._is_processing = True
            self.async_update_listeners()

            start_time = time.time()

            messages = kwargs.pop("messages", [{"role": "user", "content": message}])
            model = kwargs.pop("model", self.model)
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)

            if self._is_anthropic:
                response = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    **kwargs
                )
                response_text = response.content[0].text
            else:
                response = await self.client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                    **kwargs
                )
                response_text = response.choices[0].message.content

            elapsed_time = time.time() - start_time
            self._request_count += 1

            if self._performance_metrics["avg_response_time"] == 0:
                self._performance_metrics["avg_response_time"] = elapsed_time
            else:
                self._performance_metrics["avg_response_time"] = (
                    (self._performance_metrics["avg_response_time"] * (self._request_count - 1) + elapsed_time)
                    / self._request_count
                )

            self.last_response = {
                "timestamp": dt_util.utcnow().isoformat(),
                "question": message,
                "response": response_text,
                "model": model,
                "instance": self.instance_name,  # Добавляем идентификатор интеграции
                "error": None
            }

            self._history.append(self.last_response)
            if len(self._history) > self._max_history_size:
                self._history.pop(0)

            self.endpoint_status = "ready"
            self._is_processing = False
            self.async_update_listeners()

            return self.last_response

        except Exception as err:
            self._error_count += 1
            self._last_error = str(err)
            self._performance_metrics["total_errors"] += 1

            self.last_response = {
                "timestamp": dt_util.utcnow().isoformat(),
                "question": message,
                "response": None,
                "instance": self.instance_name,  # Добавляем идентификатор интеграции
                "error": str(err)
            }

            self.endpoint_status = "error"
            self._is_processing = False
            self.async_update_listeners()
            raise

    async def async_set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt."""
        self._system_prompt = prompt
        _LOGGER.debug("[%s] System prompt updated: %s", self.instance_name, prompt)

    async def async_clear_history(self) -> None:
        """Clear conversation history."""
        self._history.clear()
        _LOGGER.debug("[%s] Conversation history cleared", self.instance_name)
        self.async_update_listeners()

    async def async_get_history(
        self,
        limit: Optional[int] = None,
        filter_model: Optional[str] = None,
        instance: Optional[str] = None  # Добавляем фильтр по интеграции
    ) -> List[Dict[str, Any]]:
        """Get conversation history with optional filtering."""
        history = self._history.copy()

        if instance and instance != self.instance_name:
            return []  # Возвращаем пустой список для чужих интеграций

        if filter_model:
            history = [h for h in history if h.get("model") == filter_model]

        if limit and limit > 0:
            history = history[-limit:]

        return history

    async def async_reset_metrics(self) -> None:
        """Reset all metrics."""
        self._request_count = 0
        self._error_count = 0
        self._performance_metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "avg_response_time": 0.0,
            "last_request_time": None,
            "instance": self.instance_name,  # Добавляем идентификатор интеграции
        }
        _LOGGER.debug("[%s] Metrics reset", self.instance_name)
        self.async_update_listeners()
