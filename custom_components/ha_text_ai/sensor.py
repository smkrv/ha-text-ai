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

        self._attr_name = "HA Text AI"

        self._current_state = STATE_INITIALIZING
        self._error_count = 0
        self._last_error = None

        # Девайс инфо
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": "HA Text AI",
            "manufacturer": "Community",
            "model": f"{coordinator.model} ({self._config_entry.data.get(CONF_API_PROVIDER, 'Unknown')} provider)",
            "sw_version": coordinator.api_version,
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "HA Text AI"

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

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return entity specific state attributes."""
        attributes = {
            ATTR_TOTAL_RESPONSES: 0,
            ATTR_MODEL: self.coordinator.model,
            ATTR_API_STATUS: self._current_state,
            ATTR_ERROR_COUNT: self._error_count,
            ATTR_LAST_ERROR: self._last_error,
        }

        last_response = self.coordinator.last_response
        if last_response:
            attributes.update({
                ATTR_RESPONSE: last_response.get("response", ""),
                ATTR_QUESTION: last_response.get("question", ""),
            })

        return attributes

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

    async def async_reset_error_count(self) -> None:
        """Reset the error counter."""
        self._error_count = 0
        self._last_error = None
        self.async_write_ha_state()
