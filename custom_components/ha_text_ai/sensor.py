"""Sensor platform for HA text AI."""
from datetime import datetime
import logging
from typing import Any, Callable, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ATTR_QUESTION,
    ATTR_RESPONSE,
    ATTR_LAST_UPDATED,
    ATTR_MODEL,
    ATTR_TEMPERATURE,
    ATTR_MAX_TOKENS,
    ATTR_TOTAL_RESPONSES,
)
from .coordinator import HATextAICoordinator

_LOGGER = logging.getLogger(__name__)

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

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:robot"

    def __init__(
        self,
        coordinator: HATextAICoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}"
        self._attr_name = "Last Response"
        self._attr_suggested_display_precision = 0

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data or not self.coordinator.last_update_success_time:
            return None

        # Convert to local time
        if isinstance(self.coordinator.last_update_success_time, datetime):
            return dt_util.as_local(self.coordinator.last_update_success_time)
        return self.coordinator.last_update_success_time

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return {
                ATTR_TOTAL_RESPONSES: 0,
                ATTR_MODEL: self.coordinator.model,
                ATTR_TEMPERATURE: self.coordinator.temperature,
                ATTR_MAX_TOKENS: self.coordinator.max_tokens,
            }

        try:
            history = list(self.coordinator.data.items())
            if not history:
                return {
                    ATTR_TOTAL_RESPONSES: 0,
                    ATTR_MODEL: self.coordinator.model,
                    ATTR_TEMPERATURE: self.coordinator.temperature,
                    ATTR_MAX_TOKENS: self.coordinator.max_tokens,
                }

            last_question, last_data = history[-1]

            # Handle different response formats
            if isinstance(last_data, dict):
                last_response = last_data.get("response", "")
                last_updated = last_data.get("timestamp", self.coordinator.last_update_success_time)
            else:
                last_response = str(last_data)
                last_updated = self.coordinator.last_update_success_time

            # Convert timestamp to local time if needed
            if isinstance(last_updated, datetime):
                last_updated = dt_util.as_local(last_updated)

            return {
                ATTR_QUESTION: last_question,
                ATTR_RESPONSE: last_response,
                ATTR_LAST_UPDATED: last_updated,
                ATTR_TOTAL_RESPONSES: len(history),
                ATTR_MODEL: self.coordinator.model,
                ATTR_TEMPERATURE: self.coordinator.temperature,
                ATTR_MAX_TOKENS: self.coordinator.max_tokens,
            }
        except Exception as err:
            _LOGGER.error("Error getting attributes: %s", err, exc_info=True)
            return {
                ATTR_TOTAL_RESPONSES: 0,
                ATTR_MODEL: self.coordinator.model,
                ATTR_TEMPERATURE: self.coordinator.temperature,
                ATTR_MAX_TOKENS: self.coordinator.max_tokens,
            }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
