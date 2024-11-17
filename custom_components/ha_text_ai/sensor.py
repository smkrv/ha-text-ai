"""Sensor platform for HA text AI."""
from typing import Any, Callable, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTR_QUESTION, ATTR_RESPONSE, ATTR_LAST_UPDATED
from .coordinator import HATextAICoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HA text AI sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HATextAISensor(coordinator, entry)], True)

class HATextAISensor(CoordinatorEntity, SensorEntity):
    """HA text AI Sensor."""

    def __init__(
        self,
        coordinator: HATextAICoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}"
        self._attr_name = "HA text AI"

        @property
        def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
            """Return entity specific state attributes."""
            return {
                ATTR_QUESTION: list(self.coordinator.data.keys())[-1] if self.coordinator.data else None,
                ATTR_RESPONSE: list(self.coordinator.data.values())[-1] if self.coordinator.data else None,
                ATTR_LAST_UPDATED: self.coordinator.last_update_success_time,
            }
