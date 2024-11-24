"""API Client for HA Text AI."""
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

class APIClient:
    """API Client for OpenAI and Anthropic."""

    def __init__(
        self,
        session: Any,
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

    async def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using appropriate API."""
        try:
            if self.api_provider == "anthropic":
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
        """Create completion using OpenAI API."""
        url = f"{self.endpoint}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with self.session.post(url, json=payload, headers=self.headers) as response:
            if response.status != 200:
                error_data = await response.json()
                raise HomeAssistantError(f"OpenAI API error: {error_data}")

            data = await response.json()
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
        """Create completion using Anthropic API."""
        url = f"{self.endpoint}/v1/messages"

        # Convert messages to Anthropic format
        system_prompt = next((msg["content"] for msg in messages if msg["role"] == "system"), None)
        conversation = [msg for msg in messages if msg["role"] != "system"]

        payload = {
            "model": model,
            "messages": conversation,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with self.session.post(url, json=payload, headers=self.headers) as response:
            if response.status != 200:
                error_data = await response.json()
                raise HomeAssistantError(f"Anthropic API error: {error_data}")

            data = await response.json()
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
