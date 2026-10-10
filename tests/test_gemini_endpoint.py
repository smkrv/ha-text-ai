"""Regression tests for Gemini SDK endpoint handling."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.ha_text_ai.api_client import APIClient
from custom_components.ha_text_ai.const import API_PROVIDER_GEMINI


class GeminiEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_options_and_client_lifecycle(self):
        cases = [
            ("https://custom.example", {"base_url": "https://custom.example"}),
            (
                "https://custom.example/v1beta",
                {"base_url": "https://custom.example", "api_version": "v1beta"},
            ),
            (
                "https://custom.example/proxy/v1/",
                {"base_url": "https://custom.example/proxy", "api_version": "v1"},
            ),
            (
                "https://custom.example/v1alpha",
                {"base_url": "https://custom.example", "api_version": "v1alpha"},
            ),
            ("https://generativelanguage.googleapis.com/v1beta", None),
        ]
        for endpoint, options in cases:
            with self.subTest(endpoint=endpoint):
                session = SimpleNamespace(closed=False, close=AsyncMock())
                sdk = MagicMock()
                sdk.models.generate_content.return_value = SimpleNamespace(
                    text="answer",
                    usage_metadata=SimpleNamespace(
                        prompt_token_count=1,
                        candidates_token_count=2,
                        total_token_count=3,
                    ),
                )
                client = APIClient(
                    session, endpoint, {}, API_PROVIDER_GEMINI,
                    "gemini-test", api_key="test-key",
                )
                with patch("google.genai.Client", return_value=sdk) as factory:
                    try:
                        for _ in range(2):
                            response = await client.create(
                                "gemini-test",
                                [{"role": "user", "content": "question"}],
                                0.5, 100,
                            )
                            self.assertEqual(
                                response["choices"][0]["message"]["content"],
                                "answer",
                            )
                        kwargs = {"api_key": "test-key"}
                        if options is not None:
                            kwargs["http_options"] = options
                        factory.assert_called_once_with(**kwargs)
                    finally:
                        await client.shutdown()
                    sdk.close.assert_called_once_with()
                    session.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
