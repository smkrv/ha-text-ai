"""
API Client for HA Text AI.

@license: MIT (https://opensource.org/licenses/MIT)
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

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
        """Make API request with retry logic for transient errors only.

        Retries on:
        - asyncio.TimeoutError
        - HTTP 429 (rate limit) — honors Retry-After header when present
        - HTTP 502/503/504 (upstream transient errors)

        4xx (other than 429) return immediately — they are not retryable.
        """
        safe_payload = {k: v for k, v in payload.items() if k not in ['messages', 'system']}
        _LOGGER.debug("API Request: URL=%s, Safe payload: %s", url, safe_payload)

        retryable_5xx = {502, 503, 504}

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

                    # Rate limit — retry with backoff, prefer Retry-After header
                    if response.status == 429:
                        _LOGGER.warning(
                            "Rate limit on attempt %d/%d", attempt + 1, API_RETRY_COUNT
                        )
                        if attempt < API_RETRY_COUNT - 1:
                            retry_after = self._parse_retry_after(
                                response.headers.get("Retry-After")
                            )
                            await asyncio.sleep(retry_after or (2 ** attempt))
                            continue
                        raise HomeAssistantError("API rate limit exceeded")

                    # Upstream transient errors — retry with backoff
                    if response.status in retryable_5xx:
                        _LOGGER.warning(
                            "Upstream %d on attempt %d/%d",
                            response.status, attempt + 1, API_RETRY_COUNT,
                        )
                        if attempt < API_RETRY_COUNT - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        raise HomeAssistantError(
                            f"Upstream error after retries: status {response.status}"
                        )

                    # Other client/server errors — don't retry
                    truncated_error = str(error_data)[:512]
                    _LOGGER.error("API error (status %d): %s", response.status, truncated_error)
                    raise HomeAssistantError(f"API error: status {response.status}")

            except asyncio.TimeoutError as err:
                _LOGGER.warning("Timeout on attempt %d/%d", attempt + 1, API_RETRY_COUNT)
                if attempt == API_RETRY_COUNT - 1:
                    raise HomeAssistantError("API request timed out") from err
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

    @staticmethod
    def _parse_retry_after(value: Optional[str]) -> Optional[float]:
        """Parse Retry-After header (seconds). Caps at 60s to avoid long stalls."""
        if not value:
            return None
        try:
            seconds = float(value.strip())
        except (ValueError, AttributeError):
            return None
        if seconds <= 0:
            return None
        return min(seconds, 60.0)

    async def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: Optional[str] = None,
        disable_thinking: bool = False,
    ) -> Dict[str, Any]:
        """Create completion using appropriate API."""
        try:
            self._validate_parameters(temperature, max_tokens)

            if self.api_provider == API_PROVIDER_ANTHROPIC:
                return await self._create_anthropic_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema, disable_thinking
                )
            elif self.api_provider == API_PROVIDER_DEEPSEEK:
                return await self._create_deepseek_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema, disable_thinking
                )
            elif self.api_provider == API_PROVIDER_GEMINI:
                return await self._create_gemini_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema, disable_thinking
                )
            else:
                return await self._create_openai_completion(
                    model, messages, temperature, max_tokens,
                    structured_output, json_schema, disable_thinking
                )
        except Exception as e:
            _LOGGER.error("API request failed: %s", str(e))
            raise HomeAssistantError(f"API request failed: {str(e)}") from e

    @staticmethod
    def _is_openai_reasoning_model(model: str) -> bool:
        """Detect OpenAI reasoning models (o-series and GPT-5 family).

        Reasoning models require max_completion_tokens (not max_tokens),
        do not accept custom temperature, and use "developer" role instead
        of "system". Cutoff: models released 2025-09 and later are all
        reasoning-by-default (o3, o4-mini, gpt-5, gpt-5-mini, gpt-5-nano).
        """
        if not model:
            return False
        m = model.lower().lstrip()
        # Match bare model names and dated variants (o3-2025-04-16 etc.)
        return (
            m.startswith(("o1", "o3", "o4-mini", "o4"))
            or m.startswith(("gpt-5", "gpt5"))
        )

    @staticmethod
    def _convert_system_to_developer(
        messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Rename role "system" to "developer" for OpenAI reasoning models."""
        return [
            {**m, "role": "developer"} if m.get("role") == "system" else m
            for m in messages
        ]

    @staticmethod
    def _apply_no_think_tag(
        messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Append Qwen-style /no_think soft switch to the last user message.

        Why: Qwen3 reasoning models treat "/no_think" in the last user turn as a
        request to skip thinking. Non-Qwen models ignore the trailing token
        harmlessly, so this is safe to apply to all OpenAI-compatible backends.
        """
        if not messages:
            return messages
        patched = [m.copy() for m in messages]
        for i in range(len(patched) - 1, -1, -1):
            if patched[i].get("role") == "user":
                content = patched[i].get("content", "")
                if "/no_think" not in content:
                    patched[i]["content"] = f"{content} /no_think".strip()
                break
        return patched

    @staticmethod
    def _strip_think_blocks(text: str) -> str:
        """Remove <think>...</think> reasoning blocks from model output.

        Why: Some reasoning models (DeepSeek-R1, Qwen-Thinking) emit chain-of-thought
        wrapped in <think> tags even when thinking is nominally disabled. Strip them
        so the final answer stays clean. Handles nested blocks via iterative
        replacement, and drops dangling opening tags when a response is
        truncated mid-block.
        """
        if not text or "<think>" not in text:
            return text
        import re
        pattern = re.compile(r"<think>.*?</think>", flags=re.DOTALL)
        cleaned = text
        # Iterative pass: each iteration peels one layer of nested tags.
        # Bounded to 10 iterations to avoid pathological inputs.
        for _ in range(10):
            new = pattern.sub("", cleaned)
            if new == cleaned:
                break
            cleaned = new
        # If a truncated response left a dangling <think> open, drop the rest
        # from that marker onward to avoid leaking partial reasoning.
        if "<think>" in cleaned:
            cleaned = cleaned.split("<think>", 1)[0]
        return cleaned.strip()

    @staticmethod
    def _apply_structured_output(
        payload: Dict[str, Any],
        structured_output: bool,
        json_schema: Optional[str],
    ) -> None:
        """Apply OpenAI-compatible structured output to payload in-place."""
        if not (structured_output and json_schema):
            return
        import json
        try:
            schema = json.loads(json_schema)
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": schema,
                },
            }
        except json.JSONDecodeError as e:
            _LOGGER.warning("Invalid JSON schema: %s. Falling back to json_object.", e)
            payload["response_format"] = {"type": "json_object"}

    async def _create_deepseek_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: Optional[str] = None,
        disable_thinking: bool = False,
    ) -> Dict[str, Any]:
        """Create completion using DeepSeek API."""
        url = f"{self.endpoint}/chat/completions"
        final_messages = self._apply_no_think_tag(messages) if disable_thinking else messages
        payload = {
            "model": model,
            "messages": final_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        self._apply_structured_output(payload, structured_output, json_schema)

        data = await self._make_request(url, payload)
        content = data["choices"][0]["message"]["content"]
        if disable_thinking:
            content = self._strip_think_blocks(content)
        return {
            "choices": [
                {
                    "message": {"content": content},
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
        disable_thinking: bool = False,
    ) -> Dict[str, Any]:
        """Create completion using OpenAI API.

        Reasoning models (o-series, gpt-5 family) require a different payload
        shape: max_completion_tokens instead of max_tokens, no custom
        temperature, and role "developer" instead of "system". When
        disable_thinking=True for a reasoning model we set reasoning_effort
        to "low" to minimize hidden CoT tokens. For classic chat models the
        Qwen-style /no_think soft switch is appended instead.
        """
        url = f"{self.endpoint}/chat/completions"
        is_reasoning = self._is_openai_reasoning_model(model)

        if is_reasoning:
            prepared_messages = self._convert_system_to_developer(messages)
            payload: Dict[str, Any] = {
                "model": model,
                "messages": prepared_messages,
                "max_completion_tokens": max_tokens,
            }
            if disable_thinking:
                payload["reasoning_effort"] = "low"
        else:
            prepared_messages = (
                self._apply_no_think_tag(messages) if disable_thinking else messages
            )
            payload = {
                "model": model,
                "messages": prepared_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        self._apply_structured_output(payload, structured_output, json_schema)

        data = await self._make_request(url, payload)
        content = data["choices"][0]["message"]["content"]
        # Strip <think> blocks only for classic chat models. Reasoning models
        # never emit the tags in user-facing content.
        if disable_thinking and not is_reasoning:
            content = self._strip_think_blocks(content)
        return {
            "choices": [
                {
                    "message": {"content": content},
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
        disable_thinking: bool = False,
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

        # For Anthropic, add structured output instruction to system prompt.
        # Validate schema is well-formed JSON before concatenation: untrusted
        # schema strings (built from templates/webhook data) could otherwise
        # break out of the JSON fence and rewrite the system instruction.
        if structured_output and json_schema:
            import json as _json
            try:
                _json.loads(json_schema)
            except _json.JSONDecodeError as err:
                _LOGGER.warning(
                    "Anthropic: invalid JSON schema, ignoring structured_output: %s", err
                )
            else:
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

        # Anthropic accepts temperature in [0, 1], not [0, 2] like OpenAI.
        # Clip silently to avoid a 400 when a user-set config exceeds the cap.
        clipped_temp = min(1.0, max(0.0, float(temperature)))
        payload = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
            "temperature": clipped_temp,
        }

        if system_prompt:
            payload["system"] = system_prompt

        data = await self._make_request(url, payload)
        # Anthropic returns text in "content" array; extended thinking arrives
        # as a separate thinking-type block (not <think> tags), so no strip
        # is required. Extended thinking is opt-in — we simply never request it.
        content = data["content"][0]["text"]
        return {
            "choices": [
                {
                    "message": {"content": content},
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
        disable_thinking: bool = False,
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

                # Disable thinking for Gemini 2.5+ models (ignored by 2.0 and earlier)
                if disable_thinking:
                    try:
                        config.thinking_config = types.ThinkingConfig(thinking_budget=0)
                    except (AttributeError, TypeError) as err:
                        _LOGGER.debug(
                            "ThinkingConfig not supported by this google-genai version: %s", err
                        )

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

            # Gemini uses sync SDK via to_thread, so needs its own timeout
            # (aiohttp ClientTimeout doesn't apply here)
            async with asyncio.timeout(self.api_timeout):
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

            if disable_thinking:
                response_text = self._strip_think_blocks(response_text)

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
