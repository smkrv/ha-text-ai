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
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .const import (
    API_TIMEOUT,
    API_RETRY_COUNT,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_DEEPSEEK,
    API_PROVIDER_OPENAI,
    API_PROVIDER_GEMINI,
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
        self._closed = False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()

    def _validate_parameters(
        self,
        temperature: float,
        max_tokens: int,
    ) -> None:
        """Validate API parameters with enhanced type checking."""
        # Type validation
        if not isinstance(temperature, (int, float)):
            raise TypeError(f"Temperature must be a number, got {type(temperature)}")
        if not isinstance(max_tokens, int):
            raise TypeError(f"Max tokens must be an integer, got {type(max_tokens)}")
            
        # Range validation
        if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
            raise ValueError(
                f"Temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}, got {temperature}"
            )
        if not MIN_MAX_TOKENS <= max_tokens <= MAX_MAX_TOKENS:
            raise ValueError(
                f"Max tokens must be between {MIN_MAX_TOKENS} and {MAX_MAX_TOKENS}, got {max_tokens}"
            )

    async def _make_request(
        self,
        url: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make API request with retry logic."""
        # Log request without sensitive data
        safe_payload = {k: v for k, v in payload.items() if k not in ['messages', 'system']}
        _LOGGER.debug(f"API Request: URL={url}, Safe payload: {safe_payload}")
        
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
                            # Log error without sensitive data
                            safe_error = {k: v for k, v in error_data.items() if k not in ['message', 'details']}
                            _LOGGER.error(f"API error (status {response.status}): {safe_error}")
                            raise HomeAssistantError(f"API error: status {response.status}")
                        return await response.json()
            except asyncio.TimeoutError:
                _LOGGER.warning(f"Timeout on attempt {attempt + 1}/{API_RETRY_COUNT}")
                if attempt == API_RETRY_COUNT - 1:
                    raise HomeAssistantError("API request timed out")
                await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                _LOGGER.warning(f"API request failed on attempt {attempt + 1}/{API_RETRY_COUNT}: {type(e).__name__}")
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
            elif self.api_provider == API_PROVIDER_GEMINI:
                return await self._create_gemini_completion(
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

    async def _create_gemini_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Create completion using Gemini API with google-genai library.

        Args:
            model: The model name to use
            messages: List of message dictionaries with role and content
            temperature: Sampling temperature between 0.0 and 2.0
            max_tokens: Maximum number of tokens to generate

        Returns:
            Dictionary with response content and token usage
        """
        try:
            def import_genai():
                from google import genai
                return genai

            genai = await asyncio.to_thread(import_genai)

            # Extract API key from headers (Bearer token)
            api_key = self.headers.get("Authorization", "").replace("Bearer ", "")

            def create_client():
                if self.endpoint and self.endpoint != "https://generativelanguage.googleapis.com/v1beta":
                    return genai.Client(api_key=api_key, transport="rest",
                                       client_options={"api_endpoint": self.endpoint})
                else:
                    return genai.Client(api_key=api_key)

            client = await asyncio.to_thread(create_client)

            # Process messages to extract system instruction and chat history
            system_instruction = ""
            contents = []

            for msg in messages:
                if msg['role'] == 'system':
                    system_instruction += msg['content'] + "\n"
                else:
                    # For chat history, we need to convert to the format Gemini expects
                    role = "user" if msg['role'] == 'user' else "model"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg['content']}]
                    })

            # Create configuration
            def create_config():
                from google.genai import types
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )

                # Add system instruction if present
                if system_instruction:
                    config.system_instruction = system_instruction.strip()

                return config

            config = await asyncio.to_thread(create_config)

            def generate_content():
                # For single message without history, use generate_content
                if len(contents) <= 1:
                    # If we have no content yet, create a simple prompt
                    if not contents:
                        prompt = "I need your assistance."
                    else:
                        prompt = contents[0]["parts"][0]["text"]

                    return client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    )
                else:
                    # For multi-turn conversations, use chat
                    chat = client.chats.create(model=model, config=config)

                    # Send all messages in sequence
                    for content in contents:
                        if content["role"] == "user":
                            response = chat.send_message(content["parts"][0]["text"])
                            # We don't send assistant messages as they're already part of the history

                    return response

            response = await asyncio.to_thread(generate_content)

            # Extract response text
            def extract_response():
                response_text = response.text if hasattr(response, 'text') else ""

                # Try to get token usage if available
                usage = {}
                if hasattr(response, 'usage_metadata'):
                    usage = {
                        "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                        "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                        "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0)
                    }
                else:
                    # Estimate token count as fallback
                    usage = {
                        "prompt_tokens": len(" ".join([m["content"] for m in messages]).split()) // 3,
                        "completion_tokens": len(response_text.split()) // 3,
                        "total_tokens": 0  # Will be calculated below
                    }
                    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

                return response_text, usage

            response_text, usage = await asyncio.to_thread(extract_response)

            return {
                "choices": [{
                    "message": {
                        "content": response_text
                    }
                }],
                "usage": usage
            }

        except ImportError as e:
            _LOGGER.error(f"Google Gemini library not installed: {str(e)}")
            raise HomeAssistantError(f"Missing dependency: {str(e)}. Please install google-genai.")
        except Exception as e:
            _LOGGER.error(f"Gemini API error: {str(e)}")
            raise HomeAssistantError(f"Gemini API error: {str(e)}")

    async def shutdown(self) -> None:
        """Shutdown API client."""
        _LOGGER.debug("Shutting down API client")
        await self.session.close()
