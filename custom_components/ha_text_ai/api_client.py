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

from homeassistant.exceptions import HomeAssistantError
from .const import (
    DEFAULT_API_TIMEOUT,
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
        api_timeout: int = DEFAULT_API_TIMEOUT,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize API client."""
        self.session = session
        self.endpoint = endpoint
        self.headers = headers
        self.api_provider = api_provider
        self.model = model
        self.api_timeout = api_timeout
        self.timeout = ClientTimeout(total=api_timeout)
        self._api_key = api_key
        if self.api_provider == API_PROVIDER_GEMINI and not api_key:
            raise ValueError("Gemini provider requires api_key parameter")
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
        """Make API request with retry logic for transient errors only."""
        safe_payload = {k: v for k, v in payload.items() if k not in ['messages', 'system']}
        _LOGGER.debug("API Request: URL=%s, Safe payload: %s", url, safe_payload)

        for attempt in range(API_RETRY_COUNT):
            try:
                async with self.session.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout,
                ) as response:
                    _LOGGER.debug("Response status: %s", response.status)
                    if response.status == 200:
                        return await response.json()

                    # Try to get error details
                    error_data = {}
                    try:
                        error_data = await response.json()
                    except Exception:
                        error_data = {"raw": await response.text()}

                    # Rate limit — retry with backoff
                    if response.status == 429:
                        _LOGGER.warning(
                            "Rate limit on attempt %d/%d", attempt + 1, API_RETRY_COUNT
                        )
                        if attempt < API_RETRY_COUNT - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        raise HomeAssistantError("API rate limit exceeded")

                    # Client/server errors — don't retry
                    truncated_error = str(error_data)[:512]
                    _LOGGER.error("API error (status %d): %s", response.status, truncated_error)
                    raise HomeAssistantError(f"API error: status {response.status}")

            except asyncio.TimeoutError:
                _LOGGER.warning("Timeout on attempt %d/%d", attempt + 1, API_RETRY_COUNT)
                if attempt == API_RETRY_COUNT - 1:
                    raise HomeAssistantError("API request timed out")
                await asyncio.sleep(2 ** attempt)
            except HomeAssistantError:
                raise
            except Exception as e:
                _LOGGER.warning(
                    "API request failed on attempt %d/%d: %s",
                    attempt + 1, API_RETRY_COUNT, type(e).__name__,
                )
                if attempt == API_RETRY_COUNT - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise HomeAssistantError("API request failed after all retries")

    async def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create completion using appropriate API."""
        try:
            self._validate_parameters(temperature, max_tokens)

            if self.api_provider == API_PROVIDER_ANTHROPIC:
                return await self._create_anthropic_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema
                )
            elif self.api_provider == API_PROVIDER_DEEPSEEK:
                return await self._create_deepseek_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema
                )
            elif self.api_provider == API_PROVIDER_GEMINI:
                return await self._create_gemini_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema
                )
            else:
                return await self._create_openai_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema
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
        structured_output: bool = False,
        json_schema: Optional[str] = None,
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

        # Add structured output format if enabled (DeepSeek is OpenAI-compatible)
        if structured_output and json_schema:
            try:
                import json
                schema = json.loads(json_schema)
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_response",
                        "strict": True,
                        "schema": schema
                    }
                }
                _LOGGER.debug("DeepSeek structured output enabled with schema")
            except json.JSONDecodeError as e:
                _LOGGER.warning("Invalid JSON schema provided: %s. Falling back to json_object mode.", e)
                payload["response_format"] = {"type": "json_object"}

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
        structured_output: bool = False,
        json_schema: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create completion using OpenAI API."""
        url = f"{self.endpoint}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add structured output format if enabled
        if structured_output and json_schema:
            try:
                import json
                schema = json.loads(json_schema)
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_response",
                        "strict": True,
                        "schema": schema
                    }
                }
                _LOGGER.debug("OpenAI structured output enabled with schema")
            except json.JSONDecodeError as e:
                _LOGGER.warning("Invalid JSON schema provided: %s. Falling back to json_object mode.", e)
                payload["response_format"] = {"type": "json_object"}

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
        structured_output: bool = False,
        json_schema: Optional[str] = None,
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

        # For Anthropic, add structured output instruction to system prompt
        if structured_output and json_schema:
            schema_instruction = (
                f"\n\nIMPORTANT: You MUST respond ONLY with valid JSON that matches "
                f"this JSON Schema:\n{json_schema}\n"
                f"Do not include any text before or after the JSON. "
                f"Do not wrap the JSON in markdown code blocks."
            )
            if system_prompt:
                system_prompt += schema_instruction
            else:
                system_prompt = schema_instruction.strip()
            _LOGGER.debug("Anthropic structured output enabled via system prompt")

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

    async def _create_gemini_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create completion using Gemini API with google-genai library.

        Args:
            model: The model name to use
            messages: List of message dictionaries with role and content
            temperature: Sampling temperature between 0.0 and 2.0
            max_tokens: Maximum number of tokens to generate
            structured_output: Enable JSON structured output mode
            json_schema: JSON Schema for structured output validation

        Returns:
            Dictionary with response content and token usage
        """
        try:
            def import_genai():
                from google import genai
                return genai

            genai = await asyncio.to_thread(import_genai)

            api_key = self._api_key

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

            # Parse JSON schema if structured output is enabled
            parsed_schema = None
            if structured_output and json_schema:
                try:
                    import json
                    parsed_schema = json.loads(json_schema)
                    _LOGGER.debug("Gemini structured output enabled with schema")
                except json.JSONDecodeError as e:
                    _LOGGER.warning("Invalid JSON schema provided: %s. Structured output disabled.", e)

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

                # Add structured output configuration for Gemini
                if structured_output and parsed_schema:
                    config.response_mime_type = "application/json"
                    config.response_schema = parsed_schema

                return config

            config = await asyncio.to_thread(create_config)

            def generate_content():
                # For single message without history, use generate_content
                if len(contents) <= 1:
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
                    # For multi-turn conversations, pass history to chat
                    # and only send the last user message
                    last_user_msg = None
                    history = []

                    # Find the last user message — that's the new query
                    for i in range(len(contents) - 1, -1, -1):
                        if contents[i]["role"] == "user":
                            last_user_msg = contents[i]["parts"][0]["text"]
                            history = contents[:i]
                            break

                    if last_user_msg is None:
                        # No user messages at all — shouldn't happen, but handle gracefully
                        return client.models.generate_content(
                            model=model,
                            contents="I need your assistance.",
                            config=config
                        )

                    chat = client.chats.create(
                        model=model, config=config, history=history
                    )
                    return chat.send_message(last_user_msg)

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
            _LOGGER.error("Google Gemini library not installed: %s", e)
            raise HomeAssistantError("Missing dependency: google-genai. Please install it.")
        except Exception as e:
            _LOGGER.error("Gemini API error: %s", e)
            raise HomeAssistantError("Gemini API request failed")

    async def shutdown(self) -> None:
        """Shutdown API client."""
        _LOGGER.debug("Shutting down API client")
        self._closed = True
        # Do NOT close the shared Home Assistant session
