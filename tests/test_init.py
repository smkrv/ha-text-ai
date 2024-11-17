"""Tests for the HA text AI integration."""
from unittest.mock import AsyncMock, patch
import pytest

from custom_components.ha_text_ai.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

@pytest.fixture
def mock_setup_entry() -> AsyncMock:
    """Override async_setup_entry."""
    with patch(
        "custom_components.ha_text_ai.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry

@pytest.fixture
def mock_coordinator() -> AsyncMock:
    """Override coordinator."""
    with patch(
        "custom_components.ha_text_ai.coordinator.HATextAICoordinator",
        return_value=AsyncMock(),
    ) as mock_coordinator:
        yield mock_coordinator

async def test_async_setup(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test the initial setup."""
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

async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_coordinator: AsyncMock
) -> None:
    """Test setup entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000,
            "api_endpoint": "https://api.openai.com/v1",
            "request_interval": 1.0
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(mock_coordinator.mock_calls) == 1
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
