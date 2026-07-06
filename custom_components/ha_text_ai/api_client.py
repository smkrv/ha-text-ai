"""
API Client for HA Text AI.

@license: MIT (https://opensource.org/licenses/MIT)
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any
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
        headers: dict[str, str],
        api_provider: str,
        model: str,
        api_timeout: int = DEFAULT_API_TIMEOUT,
        api_key: str | None = None,
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
        payload: dict[str, Any],
    ) -> dict[str, Any]:
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
                    # The session pins DNS to validated IPs; following a
                    # redirect would resolve a new host past that pin.
                    allow_redirects=False,
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
    def _parse_retry_after(value: str | None) -> float | None:
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
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: str | None = None,
        disable_thinking: bool = False,
    ) -> dict[str, Any]:
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

    # Non-reasoning variants whose names otherwise overlap with the
    # reasoning prefix set (e.g. "gpt-5-chat-latest" is classic chat).
    _OPENAI_NON_REASONING_PATTERNS: tuple[str, ...] = ("gpt-5-chat",)
    _OPENAI_REASONING_REGEX = re.compile(
        r"^(?:o\d+|gpt-[5-9](?:\.\d+)?)(?:[-_].*)?$"
    )

    @classmethod
    def _is_openai_reasoning_model(cls, model: str) -> bool:
        """Detect OpenAI reasoning models (o-series and GPT-5+ family).

        Reasoning models require max_completion_tokens (not max_tokens),
        do not accept custom temperature, and use "developer" role instead
        of "system". Uses a regex so future o5/gpt-6 releases are caught
        without code change. Explicitly excludes chat-variants
        (e.g. gpt-5-chat-latest) which are classic chat models.
        """
        if not model:
            return False
        m = model.strip().lower()
        # OpenRouter-style "openai/o3" prefix — strip provider namespace.
        if "/" in m:
            m = m.rsplit("/", 1)[-1]
        for non_reasoning in cls._OPENAI_NON_REASONING_PATTERNS:
            if m.startswith(non_reasoning):
                return False
        return bool(cls._OPENAI_REASONING_REGEX.match(m))

    @staticmethod
    def _convert_system_to_developer(
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Rename role "system" to "developer" for OpenAI reasoning models."""
        return [
            {**m, "role": "developer"} if m.get("role") == "system" else m
            for m in messages
        ]

    # Matches /no_think only as a standalone soft-switch token (word-bounded),
    # not when users discuss the concept ("discuss /no_think semantics").
    _NO_THINK_TOKEN_RE = re.compile(r"(?:^|\s)/no_think(?:\s|$)")

    @classmethod
    def _apply_no_think_tag(
        cls,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Append Qwen-style /no_think soft switch to the last user message.

        Why: Qwen3 reasoning models treat "/no_think" in the last user turn as a
        request to skip thinking. Non-Qwen models ignore the trailing token
        harmlessly, so this is safe to apply to all OpenAI-compatible backends.
        Uses word-boundary regex for dedup so that user content mentioning
        "/no_think" mid-sentence isn't mistaken for an existing soft switch.
        """
        if not messages:
            return messages
        patched = [m.copy() for m in messages]
        for i in range(len(patched) - 1, -1, -1):
            if patched[i].get("role") == "user":
                content = patched[i].get("content", "")
                if not cls._NO_THINK_TOKEN_RE.search(content):
                    patched[i]["content"] = f"{content.rstrip()} /no_think".lstrip()
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
        payload: dict[str, Any],
        structured_output: bool,
        json_schema: str | None,
    ) -> None:
        """Apply OpenAI-compatible structured output to payload in-place."""
        if not (structured_output and json_schema):
            return
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
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: str | None = None,
        disable_thinking: bool = False,
    ) -> dict[str, Any]:
        """Create completion using DeepSeek API.

        DeepSeek-reasoner (R1) is a reasoning model: it ignores /no_think
        (thinking is always on by design) and emits reasoning_content as a
        separate field alongside content. We skip the no_think append for
        this model and preserve reasoning_content in the response payload
        so it's available for logging/debug.

        DeepSeek V4+ (deepseek-v4-flash/-pro) selects thinking mode via a
        top-level "thinking" request parameter instead of the model name,
        so /no_think does not apply there.
        """
        url = f"{self.endpoint}/chat/completions"
        m_lower = model.lower()
        is_reasoner = "reasoner" in m_lower
        is_v4plus = re.search(r"deepseek-v[4-9]", m_lower) is not None
        final_messages = (
            self._apply_no_think_tag(messages)
            if (disable_thinking and not is_reasoner and not is_v4plus)
            else messages
        )
        payload = {
            "model": model,
            "messages": final_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if disable_thinking and is_v4plus:
            payload["thinking"] = {"type": "disabled"}
        self._apply_structured_output(payload, structured_output, json_schema)

        data = await self._make_request(url, payload)
        message = data["choices"][0]["message"]
        content = message.get("content", "")
        reasoning = message.get("reasoning_content")
        if disable_thinking and not is_reasoner:
            content = self._strip_think_blocks(content)
        return {
            "choices": [
                {
                    "message": {
                        "content": content,
                        **({"reasoning_content": reasoning} if reasoning else {}),
                    },
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
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: str | None = None,
        disable_thinking: bool = False,
    ) -> dict[str, Any]:
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
            payload: dict[str, Any] = {
                "model": model,
                "messages": prepared_messages,
                "max_completion_tokens": max_tokens,
            }
            if disable_thinking:
                # gpt-5+ supports "minimal" (cheapest, lowest-CoT). o-series
                # rejects "minimal" and accepts low/medium/high — fall back to "low".
                effort = "minimal" if model.lower().startswith(("gpt-5", "gpt5")) else "low"
                payload["reasoning_effort"] = effort
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
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: str | None = None,
        disable_thinking: bool = False,
    ) -> dict[str, Any]:
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
            try:
                json.loads(json_schema)
            except json.JSONDecodeError as err:
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
        # Anthropic returns an array of content blocks; if extended thinking
        # is ever enabled the first block may be type="thinking". Find the
        # first text-type block instead of hardcoding index [0].
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content = block.get("text", "")
                break
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
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        structured_output: bool = False,
        json_schema: str | None = None,
        disable_thinking: bool = False,
    ) -> dict[str, Any]:
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

                # Disable thinking. Gemini 3.x+ replaced the numeric
                # thinking_budget with a semantic thinking_level; Pro
                # variants do not accept MINIMAL, their floor is LOW.
                # Gemini 2.5: Flash accepts thinking_budget=0 (fully off),
                # Pro rejects 0 and requires at least 128 tokens.
                # 2.0 and earlier ignore the field.
                if disable_thinking:
                    m_lower = model.lower()
                    try:
                        if re.search(r"gemini-[3-9]", m_lower):
                            level = "LOW" if "pro" in m_lower else "MINIMAL"
                            config.thinking_config = types.ThinkingConfig(
                                thinking_level=level
                            )
                        else:
                            budget = 128 if "2.5-pro" in m_lower else 0
                            config.thinking_config = types.ThinkingConfig(
                                thinking_budget=budget
                            )
                    except (AttributeError, TypeError, ValueError) as err:
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
            raise HomeAssistantError(
                "Missing dependency: google-genai. Please install it."
            ) from e
        except Exception as e:
            _LOGGER.error("Gemini API error: %s", e)
            raise HomeAssistantError(f"Gemini API request failed: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown API client and close its dedicated session."""
        _LOGGER.debug("Shutting down API client")
        self._closed = True
        # The session is dedicated to this config entry (pinned resolver,
        # isolated cookie jar), so it must be closed here to release the
        # connector; nothing else owns it.
        if self.session is not None and not self.session.closed:
            await self.session.close()
