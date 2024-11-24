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
    # Основные константы домена
    DOMAIN,
    CONF_INSTANCE,
    CONF_MODEL,

    # Атрибуты сенсора
    ATTR_TOTAL_RESPONSES,
    ATTR_TOTAL_ERRORS,
    ATTR_AVG_RESPONSE_TIME,
    ATTR_LAST_REQUEST_TIME,
    ATTR_LAST_ERROR,
    ATTR_IS_PROCESSING,
    ATTR_IS_RATE_LIMITED,
    ATTR_IS_MAINTENANCE,
    ATTR_API_VERSION,
    ATTR_ENDPOINT_STATUS,
    ATTR_PERFORMANCE_METRICS,
    ATTR_HISTORY_SIZE,
    ATTR_UPTIME,
    ATTR_API_PROVIDER,
    ATTR_MODEL,
    ATTR_SYSTEM_PROMPT,

    # Метрики
    METRIC_TOTAL_TOKENS,
    METRIC_PROMPT_TOKENS,
    METRIC_COMPLETION_TOKENS,
    METRIC_SUCCESSFUL_REQUESTS,
    METRIC_FAILED_REQUESTS,
    METRIC_AVERAGE_LATENCY,
    METRIC_MAX_LATENCY,
    METRIC_MIN_LATENCY,

    # Состояния и иконки
    STATE_READY,
    STATE_PROCESSING,
    STATE_ERROR,
    STATE_INITIALIZING,
    STATE_MAINTENANCE,
    STATE_RATE_LIMITED,
    STATE_DISCONNECTED,
    ENTITY_ICON,
    ENTITY_ICON_ERROR,
    ENTITY_ICON_PROCESSING,
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
        self._name = config_entry.title
        self._attr_unique_id = f"{config_entry.entry_id}_{slugify(self._name)}"
        self.entity_id = f"sensor.ha_text_ai_{slugify(self._name)}"
        self._attr_name = self._name
        self._current_state = STATE_INITIALIZING
        self._error_count = 0
        self._last_error = None

        # Получаем модель из конфигурации или данных координатора
        model = (
            self.coordinator.data.get("model")
            if self.coordinator.data
            else self._config_entry.data.get(CONF_MODEL, "Unknown")
        )

        api_provider = self._config_entry.data.get(CONF_API_PROVIDER, "Unknown")
        api_version = (
            self.coordinator.data.get("api_version", "v1")
            if self.coordinator.data
            else "v1"
        )

        # Обновляем device_info с использованием DeviceInfo
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._name,
            manufacturer="Community",
            model=f"{model} ({api_provider} provider)",
            sw_version=api_version,
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
        try:
            if self.coordinator.data and "last_update" in self.coordinator.data:
                timestamp = self.coordinator.data["last_update"]
                if isinstance(timestamp, str):
                    return dt_util.parse_datetime(timestamp)
                return timestamp
        except Exception as err:
            _LOGGER.debug("Error parsing state: %s", err)
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

            # Обновляем метрики если они есть
            if "metrics" in data and isinstance(data["metrics"], dict):
                attributes.update({"metrics": data["metrics"]})

            # Обновляем статус API
            if "status" in data:
                attributes[ATTR_API_STATUS] = data["status"]

            # Обновляем информацию о последнем ответе
            last_response = data.get("last_response", {})
            if isinstance(last_response, dict):
                attributes.update({
                    ATTR_RESPONSE: last_response.get("response", ""),
                    ATTR_QUESTION: last_response.get("question", ""),
                })

        return attributes

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            data = self.coordinator.data
            if not data:
                self._current_state = STATE_DISCONNECTED
                return

            # Определяем текущее состояние
            if data.get("is_processing"):
                self._current_state = STATE_PROCESSING
            elif data.get("is_rate_limited"):
                self._current_state = STATE_RATE_LIMITED
            elif data.get("is_maintenance"):
                self._current_state = STATE_MAINTENANCE
            else:
                self._current_state = STATE_READY

            # Обновляем счетчик ошибок из метрик
            if "metrics" in data and isinstance(data["metrics"], dict):
                self._error_count = data["metrics"].get("total_errors", self._error_count)

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
