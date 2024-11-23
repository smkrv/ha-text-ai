"""Sensor platform for HA text AI."""
import logging
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    CONF_API_PROVIDER,
    ATTR_QUESTION,
    ATTR_RESPONSE,
    ATTR_MODEL,
    ATTR_TOTAL_RESPONSES,
    ATTR_API_STATUS,
    ATTR_ERROR_COUNT,
    ATTR_LAST_ERROR,
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

    def __init__(
        self,
        coordinator: HATextAICoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry

        # Используем имя из конфигурации
        self._name = config_entry.title

        # Создаем уникальный ID используя имя
        self._attr_unique_id = f"{config_entry.entry_id}_{slugify(self._name)}"

        # Создаем entity_id используя имя
        self.entity_id = f"sensor.ha_text_ai_{slugify(self._name)}"

        # Устанавливаем отображаемое имя
        self._attr_name = self._name

        self._current_state = STATE_INITIALIZING
        self._error_count = 0
        self._last_error = None

        # Обновляем device_info с использованием DeviceInfo
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._name,
            manufacturer="Community",
            model=f"{coordinator.model} ({self._config_entry.data.get(CONF_API_PROVIDER, 'Unknown')} provider)",
            sw_version=coordinator._api_version,
        )

    @property
    def icon(self) -> str:
        """Return the icon based on the current state."""
        if self._current_state == STATE_ERROR:
            return ENTITY_ICON_ERROR
        elif self._current_state == STATE_PROCESSING:
            return ENTITY_ICON_PROCESSING
        return ENTITY_ICON

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("last_update", self._current_state)
        return self._current_state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        attributes = {
            ATTR_TOTAL_RESPONSES: len(getattr(self.coordinator, '_history', [])),
            ATTR_MODEL: self.coordinator.model,
            ATTR_API_STATUS: self._current_state,
            ATTR_ERROR_COUNT: self._error_count,
            ATTR_LAST_ERROR: self._last_error,
        }

        if self.coordinator.data:
            data = self.coordinator.data
            if "metrics" in data:
                attributes.update({"metrics": data["metrics"]})
            if "status" in data:
                attributes[ATTR_API_STATUS] = data["status"]
            if "last_response" in data:
                last_response = data["last_response"]
                if last_response:
                    attributes.update({
                        ATTR_RESPONSE: last_response.get("response", ""),
                        ATTR_QUESTION: last_response.get("question", ""),
                    })

        return attributes

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            data = self.coordinator.data
            if data:
                if data.get("is_processing"):
                    self._current_state = STATE_PROCESSING
                elif data.get("is_rate_limited"):
                    self._current_state = STATE_RATE_LIMITED
                elif data.get("is_maintenance"):
                    self._current_state = STATE_MAINTENANCE
                else:
                    self._current_state = STATE_READY

                if "metrics" in data:
                    self._error_count = data["metrics"].get("total_errors", 0)
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

    async def async_reset_error_count(self) -> None:
        """Reset the error counter."""
        self._error_count = 0
        self._last_error = None
        self.async_write_ha_state()
