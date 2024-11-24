"""Sensor platform for HA Text AI."""
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
    CONF_MODEL,
    CONF_API_PROVIDER,
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
    ATTR_API_STATUS,
    ATTR_RESPONSE,
    ATTR_QUESTION,
    METRIC_TOTAL_TOKENS,
    METRIC_PROMPT_TOKENS,
    METRIC_COMPLETION_TOKENS,
    METRIC_SUCCESSFUL_REQUESTS,
    METRIC_FAILED_REQUESTS,
    METRIC_AVERAGE_LATENCY,
    METRIC_MAX_LATENCY,
    METRIC_MIN_LATENCY,
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
    """Set up the HA Text AI sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    instance_name = coordinator.instance_name
    _LOGGER.info(f"Setting up HA Text AI sensor with instance: {instance_name}")
    async_add_entities([HATextAISensor(coordinator, entry)], True)

class HATextAISensor(CoordinatorEntity, SensorEntity):
    """HA Text AI Sensor."""

    coordinator: HATextAICoordinator

    def __init__(
        self,
        coordinator: HATextAICoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._config_entry = config_entry
        self._instance_name = coordinator.instance_name

        # Упрощаем формирование entity_id
        self.entity_id = f"sensor.ha_text_ai_{self._instance_name}"
        self._attr_name = f"HA Text AI {self._instance_name}"
        self._attr_unique_id = f"{config_entry.entry_id}"

        _LOGGER.debug(f"Initializing sensor with entity_id: {self.entity_id}")

        self._current_state = STATE_INITIALIZING
        self._error_count = 0
        self._last_error = None
        self._last_update = None

        # Device info
        model = config_entry.data.get(CONF_MODEL, "Unknown")
        api_provider = config_entry.data.get(CONF_API_PROVIDER, "Unknown")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Community",
            model=f"{model} ({api_provider} provider)",
            sw_version="1.0.0",
        )

        _LOGGER.info(f"Initialized sensor: {self.entity_id} for instance: {self._instance_name}")

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        if not self.coordinator.data:
            return STATE_DISCONNECTED

        status = self.coordinator.data.get("state", STATE_READY)
        self._current_state = status
        return status

    @property
    def icon(self) -> str:
        """Return the icon based on the current state."""
        if self._current_state == STATE_ERROR:
            return ENTITY_ICON_ERROR
        elif self._current_state == STATE_PROCESSING:
            return ENTITY_ICON_PROCESSING
        return ENTITY_ICON

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        attributes = {
            ATTR_MODEL: self._config_entry.data.get(CONF_MODEL, "Unknown"),
            ATTR_API_PROVIDER: self._config_entry.data.get(CONF_API_PROVIDER, "Unknown"),
            ATTR_API_STATUS: self._current_state,
            ATTR_TOTAL_ERRORS: self._error_count,
            ATTR_LAST_ERROR: self._last_error,
            "instance_name": self._instance_name,  # Добавляем instance_name в атрибуты
        }

        if not self.coordinator.data:
            return attributes

        data = self.coordinator.data

        # Основные атрибуты
        for attr in [
            ATTR_TOTAL_RESPONSES,
            ATTR_AVG_RESPONSE_TIME,
            ATTR_LAST_REQUEST_TIME,
            ATTR_IS_PROCESSING,
            ATTR_IS_RATE_LIMITED,
            ATTR_IS_MAINTENANCE,
            ATTR_API_VERSION,
            ATTR_ENDPOINT_STATUS,
            ATTR_PERFORMANCE_METRICS,
            ATTR_HISTORY_SIZE,
            ATTR_UPTIME,
            ATTR_SYSTEM_PROMPT,
        ]:
            value = data.get(attr)
            if value is not None:
                attributes[attr] = value

        # Метрики
        metrics = data.get("metrics", {})
        if isinstance(metrics, dict):
            for metric in [
                METRIC_TOTAL_TOKENS,
                METRIC_PROMPT_TOKENS,
                METRIC_COMPLETION_TOKENS,
                METRIC_SUCCESSFUL_REQUESTS,
                METRIC_FAILED_REQUESTS,
                METRIC_AVERAGE_LATENCY,
                METRIC_MAX_LATENCY,
                METRIC_MIN_LATENCY,
            ]:
                value = metrics.get(metric)
                if value is not None:
                    attributes[metric] = value

        # Последний ответ
        last_response = data.get("last_response", {})
        if isinstance(last_response, dict):
            attributes[ATTR_RESPONSE] = last_response.get("response", "")
            attributes[ATTR_QUESTION] = last_response.get("question", "")

        return attributes

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            self._current_state = STATE_DISCONNECTED
            self.async_write_ha_state()
            return

        try:
            data = self.coordinator.data

            # Обновляем состояние
            if data.get("is_processing"):
                self._current_state = STATE_PROCESSING
            elif data.get("is_rate_limited"):
                self._current_state = STATE_RATE_LIMITED
            elif data.get("is_maintenance"):
                self._current_state = STATE_MAINTENANCE
            elif data.get("error"):
                self._current_state = STATE_ERROR
                self._last_error = data["error"]
                self._error_count += 1
            else:
                self._current_state = STATE_READY

            # Обновляем метрики
            metrics = data.get("metrics", {})
            if isinstance(metrics, dict):
                self._error_count = metrics.get("total_errors", self._error_count)

            self._last_update = data.get("last_update")

        except Exception as err:
            _LOGGER.error("Error handling update: %s", err, exc_info=True)
            self._current_state = STATE_ERROR
            self._last_error = str(err)
            self._error_count += 1

        self.async_write_ha_state()
