"""
The HA Text AI coordinator.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_CONTEXT_MESSAGES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    STATE_ERROR,
    STATE_MAINTENANCE,
    STATE_PROCESSING,
    STATE_RATE_LIMITED,
    STATE_READY,
    TRUNCATION_INDICATOR,
)
from .history import HistoryManager
from .metrics import MetricsManager
from .utils import normalize_name

_LOGGER = logging.getLogger(__name__)


class HATextAICoordinator(DataUpdateCoordinator):
    """Home Assistant Text AI Conversation Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,
        model: str,
        update_interval: int,
        instance_name: str,
        config_entry: ConfigEntry,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_history_size: int = DEFAULT_MAX_HISTORY,
        context_messages: int = DEFAULT_CONTEXT_MESSAGES,
        api_timeout: int = DEFAULT_API_TIMEOUT,
    ) -> None:
        """Initialize coordinator."""
        self.instance_name = instance_name
        self.normalized_name = normalize_name(instance_name)

        history_dir = os.path.join(
            hass.config.path(".storage"), "ha_text_ai_history"
        )
        metrics_file = os.path.join(
            history_dir,
            f"ha_text_ai_metrics_{self.normalized_name}.json",
        )

        # Delegate history and metrics to dedicated managers
        self._history = HistoryManager(
            hass=hass,
            instance_name=instance_name,
            normalized_name=self.normalized_name,
            history_dir=history_dir,
            max_history_size=max_history_size,
        )
        self._metrics = MetricsManager(
            hass=hass,
            instance_name=instance_name,
            metrics_file=metrics_file,
        )

        self.hass = hass
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_timeout = api_timeout

        # Concurrency control
        self._request_lock = asyncio.Lock()

        # State flags
        self._is_processing = False
        self._is_rate_limited = False
        self._is_maintenance = False
        self.endpoint_status = "ready"
        self._system_prompt: Optional[str] = None

        self._last_response: Dict[str, Any] = {
            "timestamp": dt_util.utcnow().isoformat(),
            "question": "",
            "response": "",
            "model": model,
            "instance": instance_name,
            "normalized_name": self.normalized_name,
            "error": None,
        }

        super().__init__(
            hass,
            _LOGGER,
            name=instance_name,
            update_interval=timedelta(seconds=update_interval),
            config_entry=config_entry,
        )

        self.available = True
        self._state = STATE_READY
        self._start_time = dt_util.utcnow()
        self.context_messages = context_messages

        _LOGGER.info("Initialized HA Text AI coordinator: %s", instance_name)

    # ------------------------------------------------------------------
    # Convenience accessors for backward compatibility
    # ------------------------------------------------------------------
    @property
    def _conversation_history(self) -> List[Dict[str, Any]]:
        return self._history.conversation_history

    @property
    def max_history_size(self) -> int:
        return self._history.max_history_size

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_initialize(self) -> None:
        """Initialize coordinator: directories, history, metrics. Must be awaited."""
        await self._history.async_initialize()
        await self._metrics.async_initialize()

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        _LOGGER.debug("Shutting down coordinator for %s", self.instance_name)

    # ------------------------------------------------------------------
    # Last response
    # ------------------------------------------------------------------
    @property
    def last_response(self) -> Dict[str, Any]:
        """Get the last response."""
        return self._last_response

    @last_response.setter
    def last_response(self, value: Dict[str, Any]) -> None:
        self._last_response = value

    # ------------------------------------------------------------------
    # HA state update
    # ------------------------------------------------------------------
    async def async_update_ha_state(self) -> None:
        """Update Home Assistant state via coordinator refresh."""
        try:
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error updating HA state for %s: %s", self.instance_name, err)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update coordinator data."""
        try:
            current_state = self._get_current_state()
            history_data = self._history.get_limited_history()
            metrics = await self._metrics.get_current_metrics()

            data = {
                "state": current_state,
                "metrics": metrics or {},
                "last_response": self._get_sanitized_last_response(),
                "is_processing": self._is_processing,
                "is_rate_limited": self._is_rate_limited,
                "is_maintenance": self._is_maintenance,
                "endpoint_status": self.endpoint_status,
                "uptime": self._calculate_uptime(),
                "system_prompt": self._get_truncated_system_prompt(),
                "history_size": self._history.history_size,
                "conversation_history": history_data["entries"],
                "history_info": history_data["info"],
                "normalized_name": self.normalized_name,
            }

            self._validate_update_data(data)
            return data

        except Exception as err:
            _LOGGER.error("Error updating data: %s", err, exc_info=True)
            return self._get_safe_initial_state()

    # ------------------------------------------------------------------
    # Question processing
    # ------------------------------------------------------------------
    async def async_ask_question(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        context_messages: Optional[int] = None,
        structured_output: bool = False,
        json_schema: Optional[str] = None,
    ) -> dict:
        """Process question with context management."""
        if self.client is None:
            raise HomeAssistantError("AI client not initialized")

        async with self._request_lock:
            try:
                self._is_processing = True
                await self.async_update_ha_state()

                temp_context = context_messages if context_messages is not None else self.context_messages
                temp_model = model if model is not None else self.model
                temp_temperature = temperature if temperature is not None else self.temperature
                temp_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
                temp_system_prompt = system_prompt if system_prompt is not None else self._system_prompt

                start_time = dt_util.utcnow()

                messages = []
                if temp_system_prompt:
                    messages.append({"role": "system", "content": temp_system_prompt})

                context_history = self._conversation_history[-temp_context:]
                for entry in context_history:
                    messages.append({"role": "user", "content": entry["question"]})
                    messages.append({"role": "assistant", "content": entry["response"]})

                messages.append({"role": "user", "content": question})

                response = await self._send_to_api(
                    question=question,
                    model=temp_model,
                    messages=messages,
                    temperature=temp_temperature,
                    max_tokens=temp_max_tokens,
                    structured_output=structured_output,
                    json_schema=json_schema,
                )

                latency = (dt_util.utcnow() - start_time).total_seconds()
                await self._metrics.update_metrics(latency, response)
                await self._history.update_history(question, response)

                return response

            except Exception as err:
                error_details = await self._metrics.handle_error(err, self.model)
                if error_details.get("is_connection_error"):
                    self.endpoint_status = "unavailable"
                self.last_response = error_details
                raise HomeAssistantError(f"Failed to process question: {err}")

            finally:
                self._is_processing = False
                await self.async_update_ha_state()

    async def _send_to_api(
        self,
        question: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: Optional[str] = None,
    ) -> dict:
        """Send request to AI provider and return structured response.

        Note: timeout is handled by APIClient via aiohttp ClientTimeout.
        No additional asyncio.timeout wrapper to avoid dual timeout stacking.
        """
        try:
            response = await self.client.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                structured_output=structured_output,
                json_schema=json_schema,
            )

            # Reset error state on success
            self._is_rate_limited = False
            self.endpoint_status = "ready"

            timestamp = dt_util.utcnow().isoformat()
            content = response["choices"][0]["message"]["content"]
            tokens = {
                "prompt": response["usage"]["prompt_tokens"],
                "completion": response["usage"]["completion_tokens"],
                "total": response["usage"]["total_tokens"],
            }

            self.last_response = {
                "timestamp": timestamp,
                "question": question,
                "response": content,
                "model": model,
                "instance": self.instance_name,
                "normalized_name": self.normalized_name,
                "error": None,
            }

            return {
                "content": content,
                "tokens": tokens,
                "model": model,
                "timestamp": timestamp,
                "instance": self.instance_name,
                "question": question,
                "success": True,
            }

        except Exception as err:
            _LOGGER.error("Error in API call: %s", err)
            raise

    # ------------------------------------------------------------------
    # History / prompt delegation
    # ------------------------------------------------------------------
    async def async_clear_history(self) -> None:
        """Clear conversation history."""
        await self._history.async_clear_history()
        await self.async_update_ha_state()

    async def async_get_history(
        self,
        limit: Optional[int] = None,
        filter_model: Optional[str] = None,
        start_date: Optional[str] = None,
        include_metadata: bool = False,
        sort_order: str = "newest",
    ) -> List[Dict[str, Any]]:
        """Get conversation history with optional filtering."""
        return await self._history.async_get_history(
            limit=limit,
            filter_model=filter_model,
            start_date=start_date,
            include_metadata=include_metadata,
            sort_order=sort_order,
            default_model=self.model,
        )

    async def async_set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        self._system_prompt = prompt
        await self.async_update_ha_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_current_state(self) -> str:
        if self._is_processing:
            return STATE_PROCESSING
        if self._is_rate_limited:
            return STATE_RATE_LIMITED
        if self._is_maintenance:
            return STATE_MAINTENANCE
        if self.last_response.get("error") or self.last_response.get("error_message"):
            return STATE_ERROR
        return STATE_READY

    def _get_safe_initial_state(self) -> Dict[str, Any]:
        return {
            "state": STATE_ERROR,
            "metrics": {},
            "last_response": self.last_response,
            "is_processing": False,
            "is_rate_limited": False,
            "is_maintenance": False,
            "endpoint_status": "error",
            "uptime": self._calculate_uptime(),
            "system_prompt": None,
            "history_size": 0,
            "conversation_history": [],
            "history_info": {
                "total_entries": 0,
                "displayed_entries": 0,
            },
            "normalized_name": self.normalized_name,
        }

    def _get_sanitized_last_response(self) -> Dict[str, Any]:
        """Get sanitized version of last response with truncation."""
        response = self.last_response.copy()

        for field in ("response", "question"):
            if field in response and response[field]:
                original = response[field]
                truncated = len(original) > 4096
                response[field] = (
                    original[:4096] + TRUNCATION_INDICATOR if truncated else original
                )
                response[f"is_{field}_truncated"] = truncated
                response[f"full_{field}_length"] = len(original)

        return response

    def _calculate_uptime(self) -> float:
        return (dt_util.utcnow() - self._start_time).total_seconds()

    def _get_truncated_system_prompt(self) -> Optional[str]:
        if not self._system_prompt:
            return None
        if len(self._system_prompt) <= 4096:
            return self._system_prompt
        return self._system_prompt[:4096] + TRUNCATION_INDICATOR

    @staticmethod
    def _validate_update_data(data: Dict[str, Any]) -> None:
        for key in ("state", "metrics", "last_response"):
            if key not in data:
                raise ValueError(f"Missing required key: {key}")
        if not isinstance(data["metrics"], dict):
            raise ValueError("Invalid metrics format")
