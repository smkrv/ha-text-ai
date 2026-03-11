"""
Metrics management for HA Text AI integration.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import json
import logging
import os
import re
import traceback
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

DEFAULT_METRICS: Dict[str, Any] = {
    "total_tokens": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_errors": 0,
    "average_latency": 0,
    "max_latency": 0,
    "min_latency": 0,
}


class MetricsManager:
    """Manages performance metrics for an instance."""

    def __init__(
        self,
        hass: HomeAssistant,
        instance_name: str,
        metrics_file: str,
    ) -> None:
        self.hass = hass
        self.instance_name = instance_name
        self._metrics_file = metrics_file
        self._performance_metrics: Dict[str, Any] = DEFAULT_METRICS.copy()

    @property
    def metrics(self) -> Dict[str, Any]:
        return self._performance_metrics

    async def async_initialize(self) -> None:
        """Load metrics from storage or create defaults."""
        loaded = await self._load_metrics()
        self._performance_metrics = loaded or DEFAULT_METRICS.copy()

    async def _load_metrics(self) -> Dict[str, Any] | None:
        try:
            exists = await self.hass.async_add_executor_job(
                os.path.exists, self._metrics_file
            )
            if exists:
                def read_metrics():
                    with open(self._metrics_file, "r") as f:
                        try:
                            return json.load(f)
                        except json.JSONDecodeError:
                            _LOGGER.warning("Metrics file corrupted, creating new")
                            return None

                return await self.hass.async_add_executor_job(read_metrics)
        except Exception as e:
            _LOGGER.warning("Failed to load metrics: %s", e)
        return None

    async def _save_metrics(self) -> None:
        try:
            def write_metrics():
                with open(self._metrics_file, "w") as f:
                    json.dump(self._performance_metrics, f)

            await self.hass.async_add_executor_job(write_metrics)
        except Exception as e:
            _LOGGER.warning("Failed to save metrics: %s", e)

    async def update_metrics(self, latency: float, response: dict) -> None:
        """Update performance metrics after a successful request."""
        metrics = self._performance_metrics
        tokens = response.get("tokens", {})

        metrics["total_tokens"] += tokens.get("total", 0)
        metrics["prompt_tokens"] += tokens.get("prompt", 0)
        metrics["completion_tokens"] += tokens.get("completion", 0)
        metrics["successful_requests"] += 1

        metrics["average_latency"] = (
            (metrics["average_latency"] * (metrics["successful_requests"] - 1) + latency)
            / metrics["successful_requests"]
        )
        metrics["max_latency"] = max(metrics["max_latency"], latency)
        if metrics["min_latency"] == 0:
            metrics["min_latency"] = latency
        else:
            metrics["min_latency"] = min(metrics["min_latency"], latency)

        await self._save_metrics()

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._performance_metrics.copy()

    async def handle_error(
        self,
        error: Exception,
        model: str,
    ) -> Dict[str, Any]:
        """Record an error in metrics and return error details."""
        self._performance_metrics["total_errors"] += 1
        self._performance_metrics["failed_requests"] += 1
        await self._save_metrics()

        error_msg = str(error)
        # Strip URLs, API keys, and query parameters from error messages
        error_msg = re.sub(r'https?://\S+', '[URL]', error_msg)
        error_msg = re.sub(r'[?&]key=[^\s&]+', '?key=***', error_msg)
        error_msg = re.sub(r'AIza[A-Za-z0-9_-]+', '***', error_msg)
        if len(error_msg) > 256:
            error_msg = error_msg[:256] + "..."

        error_details: Dict[str, Any] = {
            "timestamp": dt_util.utcnow().isoformat(),
            "model": model,
            "instance": self.instance_name,
            "error_message": error_msg,
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc()
            if _LOGGER.isEnabledFor(logging.DEBUG)
            else None,
        }

        error_mapping = {
            HomeAssistantError: {"is_ha_error": True},
            ConnectionError: {"is_connection_error": True},
            TimeoutError: {"is_timeout": True},
            PermissionError: {"is_permission_denied": True},
            ValueError: {"is_validation_error": True},
        }

        for error_type, error_flags in error_mapping.items():
            if isinstance(error, error_type):
                error_details.update(error_flags)
                break

        _LOGGER.error("AI Processing Error: %s", error_details)
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Full Error Traceback: %s", error_details.get("traceback"))

        return error_details
