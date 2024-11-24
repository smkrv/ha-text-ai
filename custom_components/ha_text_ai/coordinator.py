"""DataUpdateCoordinator for HA Text AI."""
from datetime import timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    STATE_READY,
    STATE_PROCESSING,
    STATE_ERROR,
    STATE_RATE_LIMITED,
    STATE_MAINTENANCE,
)

_LOGGER = logging.getLogger(__name__)

class HATextAICoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,
        model: str,
        update_interval: int,
        instance_name: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        max_history_size: int = 50,
        is_anthropic: bool = False,
    ) -> None:
        """Initialize coordinator."""
        update_interval_td = timedelta(seconds=update_interval)
        self.instance_name = instance_name

        super().__init__(
            hass,
            _LOGGER,
            name=f"HA Text AI {instance_name}",
            update_interval=update_interval_td,
        )

        self.hass = hass
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_history_size = max_history_size
        self.is_anthropic = is_anthropic

        # Register instance
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN][instance_name] = self

        self._system_prompt = None
        self._conversation_history = []
        self._performance_metrics = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_errors": 0,
            "average_latency": 0,
            "max_latency": 0,
            "min_latency": float('inf'),
        }

        self._is_processing = False
        self._is_rate_limited = False
        self._is_maintenance = False
        self.endpoint_status = "ready"

        # Initialize last_response
        self.last_response = {
            "timestamp": dt_util.utcnow().isoformat(),
            "question": "",
            "response": "",
            "model": model,
            "instance": instance_name,
            "error": None
        }

        self._start_time = dt_util.utcnow()
        _LOGGER.info(f"Initialized HA Text AI coordinator with instance: {instance_name}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        return {
            "state": self._get_current_state(),
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
        }

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

    async def async_ask_question(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Process a question with optional parameters."""
        return await self.async_process_question(
            question, model, temperature, max_tokens, system_prompt
        )

    async def async_process_question(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Process a question with optional parameters."""
        if not question:
            raise ValueError("Question cannot be empty")

        _LOGGER.debug(f"Processing question for instance {self.instance_name}")

        try:
            self._is_processing = True
            await self.async_update_ha_state()

            temp_model = model or self.model
            temp_temperature = temperature or self.temperature
            temp_max_tokens = max_tokens or self.max_tokens
            temp_system_prompt = system_prompt or self._system_prompt

            start_time = dt_util.utcnow()

            messages = []
            if temp_system_prompt:
                if self.is_anthropic:
                    system_content = f"\n\nHuman: {temp_system_prompt}\n\nAssistant: I understand and will follow these instructions."
                    messages.append({"role": "user", "content": system_content})
                else:
                    messages.append({"role": "system", "content": temp_system_prompt})

            # Add conversation history
            for entry in self._conversation_history[-5:]:  # Last 5 messages for context
                messages.append({"role": "user", "content": entry["question"]})
                messages.append({"role": "assistant", "content": entry["response"]})

            messages.append({"role": "user", "content": question})

            kwargs = {
                "model": temp_model,
                "temperature": temp_temperature,
                "max_tokens": temp_max_tokens,
                "messages": messages,
            }

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
                "error": None
            }

            return response

        except Exception as err:
            self._handle_error(err)
            raise

    async def _process_anthropic_message(self, question: str, **kwargs) -> dict:
        """Process message using Anthropic API."""
        response = await self.client.messages.create(
            model=kwargs["model"],
            max_tokens=kwargs["max_tokens"],
            messages=kwargs["messages"],
            temperature=kwargs["temperature"],
        )
        return {
            "content": response.content[0].text,
            "tokens": {
                "prompt": response.usage.input_tokens,
                "completion": response.usage.output_tokens,
                "total": response.usage.input_tokens + response.usage.output_tokens
            }
        }

    async def _process_openai_message(self, question: str, **kwargs) -> dict:
        """Process message using OpenAI API."""
        response = await self.client.chat.completions.create(
            model=kwargs["model"],
            messages=kwargs["messages"],
            temperature=kwargs["temperature"],
            max_tokens=kwargs["max_tokens"],
        )
        return {
            "content": response.choices[0].message.content,
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }

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
        self._conversation_history.append({
            "timestamp": dt_util.utcnow().isoformat(),
            "question": question,
            "response": response["content"]
        })

        while len(self._conversation_history) > self.max_history_size:
            self._conversation_history.pop(0)

    def _handle_error(self, error: Exception) -> None:
        """Handle error and update metrics."""
        self._performance_metrics["total_errors"] += 1
        self._performance_metrics["failed_requests"] += 1

        self.last_response = {
            "timestamp": dt_util.utcnow().isoformat(),
            "question": "",
            "response": "",
            "model": self.model,
            "instance": self.instance_name,
            "error": str(error)
        }

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

    async def async_update_ha_state(self) -> None:
        """Update Home Assistant state."""
        await self.async_request_refresh()
