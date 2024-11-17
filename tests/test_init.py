"""Tests for the HA text AI integration."""
from unittest.mock import patch
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from custom_components.ha_text_ai.const import DOMAIN

@pytest.mark.asyncio
async def test_setup(hass: HomeAssistant):
    """Test the setup."""
    with patch('custom_components.ha_text_ai.coordinator.HATextAICoordinator'):
        assert await async_setup_component(hass, DOMAIN, {
            DOMAIN: {
                "api_key": "test_key",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "api_endpoint": "https://api.openai.com/v1",
                "request_interval": 1.0
            }
        })
        await hass.async_block_till_done()
        assert DOMAIN in hass.data
