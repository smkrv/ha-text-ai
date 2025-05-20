"""
Sensor platform for HA Text AI.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
import logging
import math
from typing import Any, Dict
from datetime import datetime, timedelta

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
    DEFAULT_NAME_PREFIX,
    CONF_MAX_HISTORY_SIZE,
    MAX_ATTRIBUTE_SIZE,
    VERSION,
)

from .coordinator import HATextAICoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HA Text AI sensor."""
    _LOGGER.debug(f"Starting sensor setup for entry: {entry.entry_id}")

    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.debug(f"Found coordinator for entry {entry.entry_id}")

        instance_name = coordinator.instance_name
        _LOGGER.debug(f"Setting up sensor with instance: {instance_name}")

        sensor = HATextAISensor(coordinator, entry)
        _LOGGER.debug(f"Created sensor instance: {sensor.entity_id}")

        async_add_entities([sensor], True)
        _LOGGER.debug(f"Added sensor entity: {sensor.entity_id}")

    except Exception as err:
        _LOGGER.exception(f"Error setting up sensor: {err}")
        raise

class HATextAISensor(CoordinatorEntity, SensorEntity):
    """HA Text AI Sensor."""

    coordinator: HATextAICoordinator

    def __init__(
        self,
        coordinator: HATextAICoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        _LOGGER.debug(f"Initializing sensor with config entry: {config_entry.data}")

        super().__init__(coordinator)

        self._config_entry = config_entry
        self._instance_name = coordinator.instance_name
        self._normalized_name = coordinator.normalized_name

        _LOGGER.debug(f"Instance name: {self._instance_name}")
        _LOGGER.debug(f"Normalized name: {self._normalized_name}")

        self._conversation_history = []
        self._system_prompt = None

        self._attr_name = f"HA Text AI {self._instance_name}"
        self.entity_id = f"sensor.ha_text_ai_{self._normalized_name}"
        self._attr_unique_id = f"{config_entry.entry_id}"

        _LOGGER.debug(f"Created sensor with entity_id: {self.entity_id}")
        _LOGGER.debug(f"Sensor name: {self._attr_name}")
        _LOGGER.debug(f"Unique ID: {self._attr_unique_id}")

        self.entity_description = SensorEntityDescription(
            key=f"ha_text_ai_{self._normalized_name.lower()}",
            entity_registry_enabled_default=True,
        )

        self._current_state = STATE_INITIALIZING
        self._error_count = 0
        self._last_error = None
        self._last_update = None
        self._is_processing = False
        self._last_response = {}
        self._metrics = {}

        model = config_entry.data.get(CONF_MODEL, "Unknown")
        api_provider = config_entry.data.get(CONF_API_PROVIDER, "Unknown")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Community",
            model=f"{model} ({api_provider} provider)",
            sw_version=VERSION,
        )

        _LOGGER.debug(
            f"Initialized sensor: {self.entity_id} for instance: {self._instance_name}"
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._current_state != STATE_DISCONNECTED
        )

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize values for JSON serialization."""
        if isinstance(value, float):
            if math.isinf(value) or math.isnan(value):
                return None
        return value

    def _sanitize_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all attributes for JSON serialization."""
        sanitized = {
            key: self._sanitize_value(value)
            for key, value in attributes.items()
            if value is not None
        }

        # Log metrics for debugging
        metrics_keys = [
            METRIC_TOTAL_TOKENS,
            METRIC_PROMPT_TOKENS,
            METRIC_COMPLETION_TOKENS,
            METRIC_SUCCESSFUL_REQUESTS,
            METRIC_FAILED_REQUESTS,
            METRIC_AVERAGE_LATENCY,
            METRIC_MAX_LATENCY,
            METRIC_MIN_LATENCY,
        ]

        metrics_values = {k: sanitized.get(k) for k in metrics_keys if k in sanitized}
        _LOGGER.debug(f"Metrics for {self.entity_id}: {metrics_values}")

        return sanitized

    @property
    def native_value(self) -> StateType:
        """Return the native value of the sensor."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            self._current_state = STATE_DISCONNECTED
            return self._current_state

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
        if not self.coordinator.data:
            return {}

        try:
            data = self.coordinator.data
            metrics = data.get("metrics", {})

            # Base attributes
            attributes = {
                ATTR_MODEL: self._config_entry.data.get(CONF_MODEL, "Unknown"),
                ATTR_API_PROVIDER: self._config_entry.data.get(CONF_API_PROVIDER, "Unknown"),
                ATTR_API_STATUS: self._current_state,
                ATTR_TOTAL_ERRORS: metrics.get("total_errors", 0),
                "instance_name": self._instance_name,
                "normalized_name": self._normalized_name,
                ATTR_SYSTEM_PROMPT: (data.get("system_prompt", "")[:MAX_ATTRIBUTE_SIZE]
                                   if data.get("system_prompt") else None),
                ATTR_IS_PROCESSING: data.get("is_processing", False),
                ATTR_IS_RATE_LIMITED: data.get("is_rate_limited", False),
                ATTR_IS_MAINTENANCE: data.get("is_maintenance", False),
                ATTR_ENDPOINT_STATUS: data.get("endpoint_status", "unknown"),
                ATTR_UPTIME: round(data.get("uptime", 0), 2),
                ATTR_HISTORY_SIZE: data.get("history_size", 0),
            }

            # History limit
            conversation_history = data.get("conversation_history", [])
            if conversation_history:
                limited_history = []
                for entry in conversation_history:
                    limited_entry = {
                        "timestamp": entry["timestamp"],
                        "question": entry["question"][:MAX_ATTRIBUTE_SIZE],
                        "response": entry["response"][:MAX_ATTRIBUTE_SIZE]
                    }
                    limited_history.append(limited_entry)
                attributes[ATTR_CONVERSATION_HISTORY] = limited_history

            # Metrics
            if isinstance(metrics, dict):
                attributes.update({
                    METRIC_TOTAL_TOKENS: metrics.get("total_tokens", 0),
                    METRIC_PROMPT_TOKENS: metrics.get("prompt_tokens", 0),
                    METRIC_COMPLETION_TOKENS: metrics.get("completion_tokens", 0),
                    METRIC_SUCCESSFUL_REQUESTS: metrics.get("successful_requests", 0),
                    METRIC_FAILED_REQUESTS: metrics.get("failed_requests", 0),
                    METRIC_AVERAGE_LATENCY: round(metrics.get("average_latency", 0), 2),
                    METRIC_MAX_LATENCY: round(metrics.get("max_latency", 0), 2),
                    METRIC_MIN_LATENCY: (metrics.get("min_latency")
                                       if metrics.get("min_latency") != float("inf")
                                       else None),
                })

            # Last response handling
            last_response = data.get("last_response", {})
            if isinstance(last_response, dict):
                attributes.update({
                    ATTR_RESPONSE: last_response.get("response", "")[:MAX_ATTRIBUTE_SIZE],
                    ATTR_QUESTION: last_response.get("question", "")[:MAX_ATTRIBUTE_SIZE],
                    "last_model": last_response.get("model", ""),
                    "last_timestamp": last_response.get("timestamp", ""),
                    "last_error": (last_response.get("error", "")[:MAX_ATTRIBUTE_SIZE]
                                 if last_response.get("error") else None),
                })

            return self._sanitize_attributes(attributes)

        except Exception as err:
            _LOGGER.error("Error preparing attributes: %s", err, exc_info=True)
            return {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        _LOGGER.debug(f"Entity {self.entity_id} added to Home Assistant")

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            data = self.coordinator.data
            if not self.coordinator.last_update_success or not data:
                self._current_state = STATE_DISCONNECTED
                _LOGGER.warning(f"No data available for {self.entity_id}")
                self.async_write_ha_state()
                return

            self._is_processing = data.get("is_processing", False)

            # Update metrics
            metrics = data.get("metrics", {})
            if isinstance(metrics, dict):
                self._metrics.update(metrics)
                _LOGGER.debug(f"Updated metrics for {self.entity_id}: {self._metrics}")

            # Update conversation history and system prompt
            self._conversation_history = data.get("conversation_history", [])
            self._system_prompt = data.get("system_prompt")

            # Update state based on conditions
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
                self._current_state = data.get("state", STATE_READY)

            # Update last update timestamp
            self._last_update = dt_util.utcnow()

            _LOGGER.debug(
                f"Updated {self.entity_id} state to: {self._current_state} "
                f"(available: {self.available})"
            )

        except Exception as err:
            self._current_state = STATE_ERROR
            self._last_error = str(err)
            self._error_count += 1
            _LOGGER.error(
                "Error handling update for %s: %s",
                self.entity_id,
                err,
                exc_info=True,
            )

        self.async_write_ha_state()
