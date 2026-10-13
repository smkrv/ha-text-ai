"""Regression tests for token usage parsing and coordinator error-state flags."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import HomeAssistantError

from custom_components.ha_text_ai.api_client import (
    APIClient,
    RateLimitAPIError,
    UpstreamAPIError,
)
from custom_components.ha_text_ai.const import (
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_GEMINI,
)
from custom_components.ha_text_ai.coordinator import HATextAICoordinator
from custom_components.ha_text_ai.metrics import MetricsManager


class UsageParsingTests(unittest.IsolatedAsyncioTestCase):
    def test_usage_missing_and_none_values(self):
        cases = [
            ({"usage": {"prompt_tokens": None}}, 0),
            ({"usage": None}, 0),
            ({}, 0),
            ({"usage": {"prompt_tokens": 7}}, 7),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertEqual(APIClient._usage(data, "prompt_tokens"), expected)


class AnthropicUsageTests(unittest.IsolatedAsyncioTestCase):
    async def test_none_token_counts_map_to_zero(self):
        session = SimpleNamespace(closed=False, close=AsyncMock())
        client = APIClient(
            session, "https://api.anthropic.com", {}, API_PROVIDER_ANTHROPIC,
            "claude-test", api_key="test-key",
        )
        client._make_request = AsyncMock(return_value={
            "content": [{"type": "text", "text": "hi"}],
            "usage": {"input_tokens": 5, "output_tokens": None},
        })
        try:
            response = await client.create(
                "claude-test",
                [{"role": "user", "content": "question"}],
                0.5, 100,
            )
        finally:
            await client.shutdown()
        self.assertEqual(
            response["usage"],
            {"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5},
        )


class GeminiUsageTests(unittest.IsolatedAsyncioTestCase):
    async def test_none_token_counts_map_to_zero(self):
        session = SimpleNamespace(closed=False, close=AsyncMock())
        sdk = MagicMock()
        sdk.models.generate_content.return_value = SimpleNamespace(
            text="answer",
            usage_metadata=SimpleNamespace(
                prompt_token_count=4,
                candidates_token_count=None,
                total_token_count=4,
            ),
        )
        client = APIClient(
            session, "https://generativelanguage.googleapis.com/v1beta", {},
            API_PROVIDER_GEMINI, "gemini-test", api_key="test-key",
        )
        with patch("google.genai.Client", return_value=sdk):
            try:
                response = await client.create(
                    "gemini-test",
                    [{"role": "user", "content": "question"}],
                    0.5, 100,
                )
            finally:
                await client.shutdown()
        usage = response["usage"]
        self.assertEqual(usage["completion_tokens"], 0)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            self.assertIsInstance(usage[key], int)


class CoordinatorErrorFlagTests(unittest.IsolatedAsyncioTestCase):
    def _make_coordinator(self) -> HATextAICoordinator:
        coordinator = object.__new__(HATextAICoordinator)
        coordinator.instance_name = "Test AI"
        coordinator.normalized_name = "test_ai"
        coordinator.model = "test-model"
        coordinator.temperature = 0.5
        coordinator.max_tokens = 100
        coordinator.api_timeout = 30
        coordinator.disable_thinking = False
        coordinator.context_messages = 10
        coordinator._system_prompt = None
        coordinator._request_lock = asyncio.Lock()
        coordinator._is_processing = False
        coordinator._is_rate_limited = False
        coordinator._is_maintenance = False
        coordinator.endpoint_status = "ready"
        coordinator._last_response = {
            "timestamp": None,
            "question": "",
            "response": "",
            "model": "test-model",
            "instance": "Test AI",
            "normalized_name": "test_ai",
            "error": None,
        }
        coordinator.async_update_ha_state = AsyncMock()
        coordinator._history = MagicMock()
        coordinator._history.conversation_history = []
        coordinator._history.update_history = AsyncMock()
        coordinator._metrics = MetricsManager(
            hass=MagicMock(),
            instance_name="Test AI",
            metrics_file="/tmp/ha_text_ai_test_metrics.json",
        )
        coordinator._metrics._save_metrics = AsyncMock()
        coordinator._metrics.update_metrics = AsyncMock()
        coordinator.client = MagicMock()
        return coordinator

    async def test_rate_limited_describes_latest_failure_only(self):
        coordinator = self._make_coordinator()
        coordinator.client.create = AsyncMock(
            side_effect=RateLimitAPIError("API rate limit exceeded")
        )
        with self.assertRaises(HomeAssistantError):
            await coordinator.async_ask_question("question")
        self.assertTrue(coordinator._is_rate_limited)
        self.assertEqual(coordinator._get_current_state(), "rate_limited")

        coordinator.client.create = AsyncMock(
            side_effect=HomeAssistantError("API error: status 401")
        )
        with self.assertRaises(HomeAssistantError):
            await coordinator.async_ask_question("question")
        self.assertFalse(coordinator._is_rate_limited)
        self.assertFalse(coordinator._is_maintenance)

    async def test_maintenance_describes_latest_failure_only(self):
        coordinator = self._make_coordinator()
        coordinator.client.create = AsyncMock(
            side_effect=UpstreamAPIError("API error: status 503")
        )
        with self.assertRaises(HomeAssistantError):
            await coordinator.async_ask_question("question")
        self.assertTrue(coordinator._is_maintenance)

        coordinator.client.create = AsyncMock(
            side_effect=HomeAssistantError("API error: status 401")
        )
        with self.assertRaises(HomeAssistantError):
            await coordinator.async_ask_question("question")
        self.assertFalse(coordinator._is_maintenance)
        self.assertFalse(coordinator._is_rate_limited)


if __name__ == "__main__":
    unittest.main()
