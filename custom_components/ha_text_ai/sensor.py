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
    CONF_API_PROVIDER,
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
    ATTR_API_VERSION,
    ATTR_ENDPOINT_STATUS,
    ATTR_REQUEST_COUNT,
    ATTR_TOKENS_USED,
    ENTITY_ICON,
    ENTITY_ICON_ERROR,
    ENTITY_ICON_PROCESSING,
    STATE_READY,
    STATE_PROCESSING,
    STATE_ERROR,
    STATE_DISCONNECTED,
    STATE_RATE_LIMITED,
    STATE_INITIALIZING,
    STATE_MAINTENANCE,
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
    _attr_translation_key = "ha_text_ai"

    def __init__(
        self,
        coordinator: HATextAICoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = config_entry.entry_id
        # Добавьте инициализацию состояния
        self._current_state = STATE_INITIALIZING

        # Девайс инфо
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": "HA Text AI",
            "manufacturer": "Community",
            "model": f"{coordinator.model} ({self._config_entry.data.get(CONF_API_PROVIDER, 'Unknown')} provider)",
            "sw_version": coordinator.api_version,
        }

    @property
    def icon(self) -> str:
        """Return the icon based on the current state."""
        if self._current_state == STATE_PROCESSING:
            return ENTITY_ICON_PROCESSING
        elif self._current_state in [STATE_ERROR, STATE_DISCONNECTED, STATE_RATE_LIMITED]:
            return ENTITY_ICON_ERROR
        return ENTITY_ICON

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        last_response = self.coordinator.last_response
        if last_response and 'timestamp' in last_response:
            return dt_util.as_local(last_response['timestamp'])
        return self._current_state

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            last_response = self.coordinator.last_response

            if last_response:
                if last_response.get("error"):
                    self._current_state = STATE_ERROR
                    self._error_count += 1
                elif self.coordinator._is_processing:
                    self._current_state = STATE_PROCESSING
                elif self.coordinator._is_rate_limited:
                    self._current_state = STATE_RATE_LIMITED
                elif self.coordinator._is_maintenance:
                    self._current_state = STATE_MAINTENANCE
                else:
                    self._current_state = STATE_READY
            else:
                self._current_state = STATE_DISCONNECTED

        except Exception as err:
            _LOGGER.error("Error handling update: %s", err, exc_info=True)
            self._error_count += 1
            self._last_error = str(err)
            self._current_state = STATE_ERROR

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        self._current_state = STATE_READY

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            last_response = self.coordinator.last_response

            if last_response:
                if last_response.get("error"):
                    self._state = STATE_ERROR
                    self._error_count += 1
                elif self.coordinator._is_processing:
                    self._state = STATE_PROCESSING
                elif self.coordinator._is_rate_limited:
                    self._state = STATE_RATE_LIMITED
                elif self.coordinator._is_maintenance:
                    self._state = STATE_MAINTENANCE
                else:
                    self._state = STATE_READY
            else:
                self._state = STATE_DISCONNECTED

        except Exception as err:
            _LOGGER.error("Error handling update: %s", err, exc_info=True)
            self._error_count += 1
            self._last_error = str(err)
            self._state = STATE_ERROR

        self.async_write_ha_state()

    async def async_reset_error_count(self) -> None:
        """Reset the error counter."""
        self._error_count = 0
        self._last_error = None
        self.async_write_ha_state()
