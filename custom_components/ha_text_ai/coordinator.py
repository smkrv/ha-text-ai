"""
The HA Text AI coordinator.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME
from .config_flow import normalize_name

from .const import (
    DOMAIN,
    STATE_READY,
    STATE_PROCESSING,
    STATE_ERROR,
    STATE_RATE_LIMITED,
    STATE_MAINTENANCE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_CONTEXT_MESSAGES,
    DEFAULT_NAME_PREFIX,
    CONF_MAX_HISTORY_SIZE,
)

_LOGGER = logging.getLogger(__name__)


class HATextAICoordinator(DataUpdateCoordinator):
    """The HA Text AI coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,
        model: str,
        update_interval: int,
        instance_name: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_history_size: int = DEFAULT_MAX_HISTORY,
        context_messages: int = DEFAULT_CONTEXT_MESSAGES,
        is_anthropic: bool = False,
    ) -> None:
        """Initialize coordinator."""
        self.instance_name = instance_name
        self.normalized_name = None

        # Use the normalize_name function from config_flow to ensure consistency
        from .config_flow import normalize_name
        self.normalized_name = normalize_name(instance_name)

        self.hass = hass
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_history_size = max_history_size
        self.is_anthropic = is_anthropic

        # Initialize with default state
        self._initial_state = {
            "state": STATE_READY,
            "metrics": {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_errors": 0,
                "average_latency": 0,
                "max_latency": 0,
                "min_latency": float("inf"),
            },
            "last_response": {
                "timestamp": dt_util.utcnow().isoformat(),
                "question": "",
                "response": "",
                "model": model,
                "instance": instance_name,
                "normalized_name": self.normalized_name,
                "error": None,
            },
            "is_processing": False,
            "is_rate_limited": False,
            "is_maintenance": False,
            "endpoint_status": "ready",
            "uptime": 0,
            "system_prompt": None,
            "history_size": 0,
            "conversation_history": [],
        }

        update_interval_td = timedelta(seconds=update_interval)

        super().__init__(
            hass,
            _LOGGER,
            name=instance_name,
            update_interval=update_interval_td,
        )

        # Register instance
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN][instance_name] = self
        self.context_messages = context_messages

        self._system_prompt = None
        self._conversation_history = []
        self._performance_metrics = self._initial_state["metrics"].copy()
        self._is_processing = False
        self._is_rate_limited = False
        self._is_maintenance = False
        self.endpoint_status = "ready"
        self.last_response = self._initial_state["last_response"].copy()
        self._start_time = dt_util.utcnow()

        _LOGGER.info(
            f"Initialized HA Text AI coordinator with instance: {instance_name}"
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            current_state = self._get_current_state()
            _LOGGER.debug(
                f"Updating data for {self.instance_name}, current state: {current_state}"
            )

            data = {
                "state": current_state,
                "metrics": self._performance_metrics,
                "last_response": self.last_response,
                "is_processing": self._is_processing,
                "is_rate_limited": self._is_rate_limited,
                "is_maintenance": self._is_maintenance,
                "endpoint_status": self.endpoint_status,
                "uptime": (dt_util.utcnow() - self._start_time).total_seconds(),
                "system_prompt": self._system_prompt,
                "history_size": len(self._conversation_history),
                "conversation_history": self._conversation_history,
                "normalized_name": self.normalized_name,
            }

            # Validate data
            if not isinstance(data, dict):
                raise ValueError("Invalid data format")

            _LOGGER.debug(f"Updated data for {self.instance_name}: {data}")
            return data

        except Exception as err:
            _LOGGER.error(f"Error updating data for {self.instance_name}: {err}")
            return self._initial_state

    async def async_update_ha_state(self) -> None:
        """Update Home Assistant state."""
        try:
            _LOGGER.debug(
                f"Requesting state update for {self.instance_name} (normalized: {self.normalized_name})"
            )
            await self.async_request_refresh()

            # Force update of all entities
            entity_id_base = f"sensor.ha_text_ai_{self.normalized_name.lower()}"
            for entity_id in self.hass.states.async_entity_ids():
                if entity_id.startswith(entity_id_base):
                    self.hass.states.async_set(entity_id, self._get_current_state())

        except Exception as err:
            _LOGGER.error(f"Error updating HA state for {self.instance_name}: {err}")

    def _get_current_state(self) -> str:
        """Get current state based on internal flags."""
        if self._is_processing:
            return STATE_PROCESSING
        elif self._is_rate_limited:
            return STATE_RATE_LIMITED
        elif self._is_maintenance:
            return STATE_MAINTENANCE
        elif self.last_response.get("error"):
            return STATE_ERROR
        return STATE_READY

    def _calculate_context_tokens(self, messages: List[Dict[str, str]], model: str = None) -> int:
        """
        Estimate tokens for conversation context.

        Args:
            messages: List of message dictionaries
            model: Optional model name for provider-specific estimation

        Returns:
            Estimated number of tokens
        """
        try:
            # Anthropic specific token counting
            if self.is_anthropic and hasattr(self.client, 'count_tokens'):
                return sum(self.client.count_tokens(msg['content']) for msg in messages)

            def estimate_tokens(text: str) -> int:
                """
                Flexible token estimation algorithm.

                Heuristics:
                - Count words
                - Estimate special characters
                - Fallback to character-based estimation
                """
                # Word-based estimation
                words = len(text.split())

                # Special character handling
                special_chars = sum(1 for char in text if not char.isalnum())

                # Character-based fallback
                char_tokens = len(text) // 4

                # Combine estimations with bias towards words
                total_tokens = (words * 1.5) + (special_chars * 0.5) + char_tokens

                return max(int(total_tokens), words)

            # Calculate total tokens across all messages
            total_tokens = sum(estimate_tokens(msg['content']) for msg in messages)

            # Logging for debugging
            _LOGGER.debug(
                f"Token Estimation: "
                f"Messages: {len(messages)}, "
                f"Estimated Tokens: {total_tokens}"
            )

            return total_tokens

        except Exception as e:
            # Safe fallback with detailed logging
            _LOGGER.warning(
                f"Token estimation failed. "
                f"Error: {e}. "
                f"Using conservative estimation."
            )

            # Conservative token estimation
            return len(messages) * 100

    async def async_ask_question(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        context_messages: Optional[int] = None,
    ) -> dict:
        """
        Process a question with optional parameters.

        This method is a direct wrapper around async_process_question,
        allowing flexible AI interaction with optional model, temperature,
        and context customization.

        Args:
            question: The input question or prompt
            model: Optional AI model to use
            temperature: Optional response creativity level
            max_tokens: Optional maximum response length
            system_prompt: Optional system-level instruction
            context_messages: Optional number of context messages to include

        Returns:
            Full response dictionary from the AI
        """
        return await self.async_process_question(
            question, model, temperature, max_tokens, system_prompt, context_messages
        )

    async def async_process_question(
            self,
            question: str,
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            system_prompt: Optional[str] = None,
            context_messages: Optional[int] = None,
        ) -> dict:
            """
            Enhanced question processing with intelligent token management.
            """
            try:
                self._is_processing = True
                await self.async_update_ha_state()

                temp_context_messages = context_messages or self.context_messages
                temp_model = model or self.model
                temp_temperature = temperature or self.temperature
                temp_max_tokens = max_tokens or self.max_tokens
                temp_system_prompt = system_prompt or self._system_prompt

                # Start timing
                start_time = dt_util.utcnow()

                # Prepare messages with system prompt
                messages = []
                if temp_system_prompt:
                    messages.append({"role": "system", "content": temp_system_prompt})

                # Context history management
                context_history = self._conversation_history[-temp_context_messages:]

                # Comprehensive token calculation
                context_tokens = self._calculate_context_tokens(
                    [{"content": entry["question"]} for entry in context_history] +
                    [{"content": entry["response"]} for entry in context_history] +
                    [{"content": question}],
                    temp_model
                )

                # Dynamic token allocation
                available_tokens = max(0, temp_max_tokens - context_tokens)

                # Context trimming if over token limit
                if context_tokens > temp_max_tokens:
                    _LOGGER.warning(
                        f"Token limit exceeded. "
                        f"Context: {context_tokens}, "
                        f"Max: {temp_max_tokens}"
                    )

                    # Intelligent context reduction
                    while context_tokens > temp_max_tokens // 2 and context_history:
                        context_history.pop(0)
                        context_tokens = self._calculate_context_tokens(
                            [{"content": entry["question"]} for entry in context_history] +
                            [{"content": entry["response"]} for entry in context_history] +
                            [{"content": question}],
                            temp_model
                        )

                # Rebuild messages with trimmed context
                for entry in context_history:
                    messages.append({"role": "user", "content": entry["question"]})
                    messages.append({"role": "assistant", "content": entry["response"]})

                messages.append({"role": "user", "content": question})

                # Detailed token logging
                _LOGGER.debug(
                    f"Token Analysis: "
                    f"Context Tokens: {context_tokens}, "
                    f"Max Tokens: {temp_max_tokens}, "
                    f"Available Tokens: {available_tokens}"
                )

                # Prepare API call with dynamic token management
                kwargs = {
                    "model": temp_model,
                    "temperature": temp_temperature,
                    "max_tokens": min(temp_max_tokens, available_tokens),
                    "messages": messages,
                }

                # Process message
                response = await self.async_process_message(question, **kwargs)

                # Update metrics
                end_time = dt_util.utcnow()
                latency = (end_time - start_time).total_seconds()
                self._update_metrics(latency, response)

                # Update history
                self._update_history(question, response)

                return response

            except Exception as err:
                self._handle_error(err)
                raise HomeAssistantError(f"Failed to process question: {err}")

            finally:
                self._is_processing = False
                await self.async_update_ha_state()

    async def async_process_message(self, question: str, **kwargs) -> dict:
        """Process message using the AI client."""
        try:
            if self.is_anthropic:
                response = await self._process_anthropic_message(question, **kwargs)
            else:
                response = await self._process_openai_message(question, **kwargs)

            self.last_response = {
                "timestamp": dt_util.utcnow().isoformat(),
                "question": question,
                "response": response["content"],
                "model": kwargs.get("model", self.model),
                "instance": self.instance_name,
                "error": None,
            }

            return response

        except Exception as err:
            self._handle_error(err)
            raise

    async def _process_anthropic_message(self, question: str, **kwargs) -> dict:
        """Process message using Anthropic API."""
        try:
            _LOGGER.debug(f"Anthropic API call: model={kwargs['model']}, max_tokens={kwargs['max_tokens']}")
            response = await self.client.messages.create(
                model=kwargs["model"],
                max_tokens=kwargs["max_tokens"],
                messages=kwargs["messages"],
                temperature=kwargs["temperature"],
            )
            _LOGGER.debug(f"Anthropic response: tokens={response.usage}")
            return {
                "content": response.content[0].text,
                "tokens": {
                    "prompt": response.usage.input_tokens,
                    "completion": response.usage.output_tokens,
                    "total": response.usage.input_tokens + response.usage.output_tokens,
                },
            }
        except Exception as e:
            _LOGGER.error(f"Anthropic API error: {str(e)}")
            raise

    async def _process_openai_message(self, question: str, **kwargs) -> dict:
        """Process message using OpenAI API."""
        try:
            response = await self.client.create(
                model=kwargs["model"],
                messages=kwargs["messages"],
                temperature=kwargs["temperature"],
                max_tokens=kwargs["max_tokens"],
            )

            return {
                "content": response["choices"][0]["message"]["content"],
                "tokens": {
                    "prompt": response["usage"]["prompt_tokens"],
                    "completion": response["usage"]["completion_tokens"],
                    "total": response["usage"]["total_tokens"],
                },
            }
        except Exception as e:
            _LOGGER.error(f"Error in OpenAI API call: {str(e)}")
            raise

    def _update_metrics(self, latency: float, response: dict) -> None:
        """Update performance metrics."""
        metrics = self._performance_metrics
        tokens = response.get("tokens", {})

        metrics["total_tokens"] += tokens.get("total", 0)
        metrics["prompt_tokens"] += tokens.get("prompt", 0)
        metrics["completion_tokens"] += tokens.get("completion", 0)
        metrics["successful_requests"] += 1

        metrics["average_latency"] = (
            (metrics["average_latency"] * (metrics["successful_requests"] - 1) + latency)
            / metrics["successful_requests"]
        )
        metrics["max_latency"] = max(metrics["max_latency"], latency)
        metrics["min_latency"] = min(metrics["min_latency"], latency)

    def _update_history(self, question: str, response: dict) -> None:
        """Update conversation history."""
        self._conversation_history.append(
            {
                "timestamp": dt_util.utcnow().isoformat(),
                "question": question,
                "response": response["content"],
            }
        )

        while len(self._conversation_history) > self.max_history_size:
            self._conversation_history.pop(0)

    def _handle_error(self, error: Exception) -> None:
        """
        Enhanced error handling with comprehensive diagnostics.

        Captures detailed error information, tracks error metrics,
        and provides context for troubleshooting AI processing issues.
        """
        self._performance_metrics["total_errors"] += 1
        self._performance_metrics["failed_requests"] += 1

        error_details = {
            "timestamp": dt_util.utcnow().isoformat(),
            "model": self.model,
            "instance": self.instance_name,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc() if _LOGGER.isEnabledFor(logging.DEBUG) else None,
        }

        # Specific error type handling
        error_mapping = {
            HomeAssistantError: {"is_ha_error": True},
            ConnectionError: {
                "is_connection_error": True,
                "is_rate_limited": True
            },
            TimeoutError: {"is_timeout": True},
            PermissionError: {"is_permission_denied": True},
            ValueError: {"is_validation_error": True}
        }

        for error_type, error_flags in error_mapping.items():
            if isinstance(error, error_type):
                error_details.update(error_flags)
                break

        # Update system state based on error type
        if error_details.get("is_rate_limited"):
            self._is_rate_limited = True
            _LOGGER.warning(f"Rate limit detected for {self.instance_name}")

        if error_details.get("is_connection_error"):
            self.endpoint_status = "unavailable"

        self.last_response = error_details
        _LOGGER.error(f"AI Processing Error: {error_details}")

        # Optional: Add more sophisticated error tracking or notification logic
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Full Error Traceback: {error_details['traceback']}")

    async def async_clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history = []
        await self.async_update_ha_state()

    async def async_get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self._conversation_history

    async def async_set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        self._system_prompt = prompt
        await self.async_update_ha_state()

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        _LOGGER.debug(f"Shutting down coordinator for {self.instance_name}")
        self.hass.data[DOMAIN].pop(self.instance_name, None)
