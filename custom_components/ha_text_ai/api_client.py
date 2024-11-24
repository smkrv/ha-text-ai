# api_client.py
"""API Client for HA Text AI.

This file contains the implementation of an API client for the HA Text AI integration compatible with both OpenAI and Anthropic service providers.
The client handles API requests, manages connection sessions, implements retry logic, and validates parameters for requests to ensure the correct functionality of the AI service integration within Home Assistant.
"""

import logging
import asyncio
from typing import Any, Dict, List
from aiohttp import ClientSession, ClientTimeout
from async_timeout import timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .const import (
    API_TIMEOUT,
    API_RETRY_COUNT,
    API_PROVIDER_ANTHROPIC,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
)

_LOGGER = logging.getLogger(__name__)

class APIClient:
    """API Client for OpenAI and Anthropic.

    This client handles requests to OpenAI and Anthropic services to create text-based AI completions.
    """

    def __init__(
        self,
        session: ClientSession,
        endpoint: str,
        headers: Dict[str, str],
        api_provider: str,
        model: str,
    ) -> None:
        """Initialize API client.

        Initialize with session, endpoint URL, request headers, type of API provider (OpenAI or Anthropic), and the AI model in use.
        """
        self.session = session
        self.endpoint = endpoint
        self.headers = headers
        self.api_provider = api_provider
        self.model = model
        self.timeout = ClientTimeout(total=API_TIMEOUT)

    def _validate_parameters(
        self,
        temperature: float,
        max_tokens: int,
    ) -> None:
        """Validate API parameters.

        Check that the temperature and max_tokens are within their respective allowed ranges.
        """
        if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
            raise ValueError(
                f"Temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}"
            )
        if not MIN_MAX_TOKENS <= max_tokens <= MAX_MAX_TOKENS:
            raise ValueError(
                f"Max tokens must be between {MIN_MAX_TOKENS} and {MAX_MAX_TOKENS}"
            )

    async def _make_request(
        self,
        url: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make API request with retry logic.

        Attempt the API request a pre-defined number of times in case of failure, with an exponential backoff strategy for timeouts.
        """
        for attempt in range(API_RETRY_COUNT):
            try:
                async with timeout(API_TIMEOUT):
                    async with self.session.post(
                        url,
                        json=payload,
                        headers=self.headers,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_data = await response.json()
                            raise HomeAssistantError(f"API error: {error_data}")
                        return await response.json()
            except asyncio.TimeoutError:
                if attempt == API_RETRY_COUNT - 1:
                    raise HomeAssistantError("API request timed out")
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                if attempt == API_RETRY_COUNT - 1:
                    raise
                _LOGGER.warning("API request failed, retrying: %s", str(e))
                await asyncio.sleep(1 * (attempt + 1))

    async def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using appropriate API.

        Make a completion request using either OpenAI or Anthropic API based on the provider specified during initialization.
        """
        try:
            self._validate_parameters(temperature, max_tokens)

            if self.api_provider == API_PROVIDER_ANTHROPIC:
                return await self._create_anthropic_completion(
                    model, messages, temperature, max_tokens
                )
            else:
                return await self._create_openai_completion(
                    model, messages, temperature, max_tokens
                )
        except Exception as e:
            _LOGGER.error("API request failed: %s", str(e))
            raise HomeAssistantError(f"API request failed: {str(e)}")

    async def _create_openai_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using OpenAI API.

        Send details of the completion request to the OpenAI API and process the response.
        """
        url = f"{self.endpoint}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = await self._make_request(url, payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": data["choices"][0]["message"]["content"]
                    }
                }
            ],
            "usage": {
                "prompt_tokens": data["usage"]["prompt_tokens"],
                "completion_tokens": data["usage"]["completion_tokens"],
                "total_tokens": data["usage"]["total_tokens"]
            }
        }

    async def _create_anthropic_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using Anthropic API.

        Adapt messages format to Anthropic's requirement and make the API request to generate text completion.
        """
        url = f"{self.endpoint}/v1/messages"

        # Convert messages to Anthropic format
        system_prompt = next(
            (msg["content"] for msg in messages if msg["role"] == "system"),
            None
        )
        conversation = [msg for msg in messages if msg["role"] != "system"]

        payload = {
            "model": model,
            "messages": conversation,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        data = await self._make_request(url, payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": data["content"][0]["text"]
                    }
                }
            ],
            "usage": {
                "prompt_tokens": data["usage"]["input_tokens"],
                "completion_tokens": data["usage"]["output_tokens"],
                "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
            }
        }
