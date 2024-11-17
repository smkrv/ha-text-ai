"""Common fixtures for tests."""
import pytest
from homeassistant.core import HomeAssistant

@pytest.fixture
def hass() -> HomeAssistant:
    """Return a Home Assistant instance for testing."""
    return HomeAssistant()
