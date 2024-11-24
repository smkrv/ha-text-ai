"""Sensor platform for HA Text AI."""
import logging
import math
from typing import Any, Dict

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
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
    ATTR_CONVERSATION_HISTORY,
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

    sensor = HATextAISensor(coordinator, entry)
    sensor.platform = "sensor"
    sensor.platform_domain = DOMAIN

    async_add_entities([sensor], True)

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
        self._conversation_history = []
        self._system_prompt = None

        # Entity attributes
        self._attr_has_entity_name = True
        self.entity_id = f"sensor.ha_text_ai_{self._instance_name}"
        self._attr_name = f"HA Text AI {self._instance_name}"
        self._attr_unique_id = f"{config_entry.entry_id}"

        # Entity description
        self.entity_description = SensorEntityDescription(
            key=f"ha_text_ai_{self._instance_name}",
            name=self._attr_name,
            entity_registry_enabled_default=True,
        )

        # Integration info
        self._attr_platform = "sensor"
        self._attr_domain = DOMAIN

        # State tracking
        self._current_state = STATE_INITIALIZING
        self._error_count = 0
        self._last_error = None
        self._last_update = None
        self._is_processing = False

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

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize values for JSON serialization.

        Args:
            value: The value to sanitize

        Returns:
            Sanitized value safe for JSON serialization
        """
        if isinstance(value, float):
            if math.isinf(value) or math.isnan(value):
                return None
        return value

    def _sanitize_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all attributes for JSON serialization.

        Args:
            attributes: Dictionary of attributes to sanitize

        Returns:
            Dictionary with sanitized values
        """
        return {
            key: self._sanitize_value(value)
            for key, value in attributes.items()
        }

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
            "instance_name": self._instance_name,
            ATTR_SYSTEM_PROMPT: self._system_prompt,
            ATTR_CONVERSATION_HISTORY: self._conversation_history,
            ATTR_IS_PROCESSING: self._is_processing,
        }

        if not self.coordinator.data:
            return self._sanitize_attributes(attributes)

        data = self.coordinator.data

        # Basic attributes
        for attr in [
            ATTR_TOTAL_RESPONSES,
            ATTR_AVG_RESPONSE_TIME,
            ATTR_LAST_REQUEST_TIME,
            ATTR_IS_RATE_LIMITED,
            ATTR_IS_MAINTENANCE,
            ATTR_API_VERSION,
            ATTR_ENDPOINT_STATUS,
            ATTR_PERFORMANCE_METRICS,
            ATTR_HISTORY_SIZE,
            ATTR_UPTIME,
        ]:
            value = data.get(attr)
            if value is not None:
                attributes[attr] = value

        # Metrics
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

        # Last response
        last_response = data.get("last_response", {})
        if isinstance(last_response, dict):
            attributes[ATTR_RESPONSE] = last_response.get("response", "")
            attributes[ATTR_QUESTION] = last_response.get("question", "")

        return self._sanitize_attributes(attributes)

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

            # Update state
            self._is_processing = data.get("is_processing", False)
            if self._is_processing:
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

            # Update history
            history = data.get("conversation_history", [])
            if isinstance(history, list):
                self._conversation_history = history

            # Update system prompt
            system_prompt = data.get("system_prompt")
            if system_prompt is not None:
                self._system_prompt = system_prompt

            # Update metrics
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
