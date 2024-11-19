"""Sensor platform for HA text AI."""
from datetime import datetime
import logging
from typing import Any, Dict, Optional

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
    ATTR_SYSTEM_PROMPT,
    ATTR_QUEUE_SIZE,
    ATTR_API_STATUS,
    ATTR_ERROR_COUNT,
    ATTR_LAST_ERROR,
    ATTR_RESPONSE_TIME,
    ENTITY_ICON,
    ENTITY_ICON_ERROR,
    ENTITY_ICON_PROCESSING,
    STATE_READY,
    STATE_PROCESSING,
    STATE_ERROR,
    STATE_DISCONNECTED,
    STATE_RATE_LIMITED,
    STATE_INITIALIZING,
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
        self._error_count = 0
        self._last_error = None
        self._state = STATE_INITIALIZING

    @property
    def icon(self) -> str:
        """Return the icon based on the current state."""
        if self._state == STATE_PROCESSING:
            return ENTITY_ICON_PROCESSING
        elif self._state in [STATE_ERROR, STATE_DISCONNECTED, STATE_RATE_LIMITED]:
            return ENTITY_ICON_ERROR
        return ENTITY_ICON

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return None

        try:
            if self.coordinator.data and isinstance(self.coordinator.data, dict):
                last_update = self.coordinator.data.get("last_update")
                if isinstance(last_update, datetime):
                    return dt_util.as_local(last_update)
                return last_update
            return None
        except Exception as err:
            _LOGGER.error("Error getting state: %s", err, exc_info=True)
            return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        attributes = {
            ATTR_TOTAL_RESPONSES: 0,
            ATTR_MODEL: self.coordinator.model,
            ATTR_TEMPERATURE: self.coordinator.temperature,
            ATTR_MAX_TOKENS: self.coordinator.max_tokens,
            ATTR_SYSTEM_PROMPT: self.coordinator.system_prompt,
            ATTR_QUEUE_SIZE: self.coordinator._question_queue.qsize(),
            ATTR_API_STATUS: self._state,
            ATTR_ERROR_COUNT: self._error_count,
            ATTR_LAST_ERROR: self._last_error,
        }

        if not self.coordinator.data:
            return attributes

        try:
            history = list(self.coordinator._responses.items())
            if history:
                last_question, last_data = history[-1]

                if isinstance(last_data, dict):
                    last_response = last_data.get("response", "")
                    last_updated = last_data.get("timestamp") or self.coordinator.data.get("last_update")
                    response_time = last_data.get("response_time")

                    model = last_data.get("model", self.coordinator.model)
                    temperature = last_data.get("temperature", self.coordinator.temperature)
                    max_tokens = last_data.get("max_tokens", self.coordinator.max_tokens)
                    error = last_data.get("error")

                    if error:
                        self._last_error = error
                        self._state = STATE_ERROR
                else:
                    last_response = str(last_data)
                    last_updated = self.coordinator.data.get("last_update")
                    response_time = None
                    model = self.coordinator.model
                    temperature = self.coordinator.temperature
                    max_tokens = self.coordinator.max_tokens

                if isinstance(last_updated, datetime):
                    last_updated = dt_util.as_local(last_updated)

                attributes.update({
                    ATTR_QUESTION: last_question,
                    ATTR_RESPONSE: last_response,
                    ATTR_LAST_UPDATED: last_updated,
                    ATTR_TOTAL_RESPONSES: len(history),
                    ATTR_MODEL: model,
                    ATTR_TEMPERATURE: temperature,
                    ATTR_MAX_TOKENS: max_tokens,
                })

                if response_time is not None:
                    attributes[ATTR_RESPONSE_TIME] = response_time

            return attributes

        except Exception as err:
            _LOGGER.error("Error getting attributes: %s", err, exc_info=True)
            self._error_count += 1
            self._last_error = str(err)
            self._state = STATE_ERROR
            return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        self._state = STATE_READY

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            if self.coordinator.data:
                if self.coordinator._is_ready:
                    self._state = STATE_READY
                else:
                    self._state = STATE_DISCONNECTED
            else:
                self._state = STATE_DISCONNECTED
        except Exception as err:
            _LOGGER.error("Error handling update: %s", err, exc_info=True)
            self._error_count += 1
            self._last_error = str(err)
            self._state = STATE_ERROR

        self.async_write_ha_state()
