"""
API Client for HA Text AI.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
import logging
import asyncio
from typing import Any, Dict, List, Optional
from aiohttp import ClientSession, ClientTimeout
from async_timeout import timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .const import (
    API_TIMEOUT,
    API_RETRY_COUNT,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_DEEPSEEK,
    API_PROVIDER_OPENAI,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
)

_LOGGER = logging.getLogger(__name__)


class APIClient:
    """API Client for OpenAI and Anthropic."""

    def __init__(
        self,
        session: ClientSession,
        endpoint: str,
        headers: Dict[str, str],
        api_provider: str,
        model: str,
    ) -> None:
        """Initialize API client."""
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
        """Validate API parameters."""
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
        """Make API request with retry logic."""
        _LOGGER.debug(f"API Request: URL={url}, Payload={payload}")
        for attempt in range(API_RETRY_COUNT):
            try:
                async with timeout(API_TIMEOUT):
                    async with self.session.post(
                        url,
                        json=payload,
                        headers=self.headers,
                        timeout=self.timeout,
                    ) as response:
                        _LOGGER.debug(f"Response status: {response.status}")
                        if response.status != 200:
                            error_data = await response.json()
                            _LOGGER.error(f"API error: {error_data}")
                            raise HomeAssistantError(f"API error: {error_data}")
                        return await response.json()
            except asyncio.TimeoutError:
                _LOGGER.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == API_RETRY_COUNT - 1:
                    raise HomeAssistantError("API request timed out")
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                _LOGGER.warning(f"API request failed on attempt {attempt + 1}: {str(e)}")
                if attempt == API_RETRY_COUNT - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))

    async def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using appropriate API."""
        try:
            self._validate_parameters(temperature, max_tokens)

            if self.api_provider == API_PROVIDER_ANTHROPIC:
                return await self._create_anthropic_completion(
                    model, messages, temperature, max_tokens
                )
            elif self.api_provider == API_PROVIDER_DEEPSEEK:
                return await self._create_deepseek_completion(
                    model, messages, temperature, max_tokens
                )
            else:
                return await self._create_openai_completion(
                    model, messages, temperature, max_tokens
                )
        except Exception as e:
            _LOGGER.error("API request failed: %s", str(e))
            raise HomeAssistantError(f"API request failed: {str(e)}")

    async def _create_deepseek_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using DeepSeek API."""
        url = f"{self.endpoint}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        data = await self._make_request(url, payload)
        return {
            "choices": [
                {
                    "message": {"content": data["choices"][0]["message"]["content"]},
                }
            ],
            "usage": {
                "prompt_tokens": data["usage"]["prompt_tokens"],
                "completion_tokens": data["usage"]["completion_tokens"],
                "total_tokens": data["usage"]["total_tokens"],
            },
        }

    async def _create_openai_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using OpenAI API."""
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
                    "message": {"content": data["choices"][0]["message"]["content"]},
                }
            ],
            "usage": {
                "prompt_tokens": data["usage"]["prompt_tokens"],
                "completion_tokens": data["usage"]["completion_tokens"],
                "total_tokens": data["usage"]["total_tokens"],
            },
        }

    async def _create_anthropic_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using Anthropic API."""
        url = f"{self.endpoint}/v1/messages"

        system_prompt = None
        filtered_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                if system_prompt is None:
                    system_prompt = msg['content']
                else:
                    system_prompt += f" {msg['content']}"
            else:
                filtered_messages.append(msg)

        payload = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        data = await self._make_request(url, payload)
        return {
            "choices": [
                {
                    "message": {"content": data["content"][0]["text"]},
                }
            ],
            "usage": {
                "prompt_tokens": data["usage"]["input_tokens"],
                "completion_tokens": data["usage"]["output_tokens"],
                "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
            },
        }

    async def check_connection(self) -> bool:
        """Check API connection."""
        try:
            await self._make_request(self.endpoint, {"test": "connection"})
            return True
        except Exception as e:
            _LOGGER.error(f"Connection check failed: {str(e)}")
            return False

    async def shutdown(self) -> None:
        """Shutdown API client."""
        _LOGGER.debug("Shutting down API client")
        await self.session.close()
