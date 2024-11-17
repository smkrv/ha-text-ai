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
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return "Ready"  # Assuming "Ready" is a valid state, you might want to return something meaningful, like the last response time.
        return "Not Ready"

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return None
        keys = list(self.coordinator.data.keys())
        values = list(self.coordinator.data.values())
        last_question = keys[-1]
        last_response = values[-1]
        return {
            ATTR_QUESTION: last_question,
            ATTR_RESPONSE: last_response,
            ATTR_LAST_UPDATED: self.coordinator.last_update_success_time,
        }
        
