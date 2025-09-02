"""
The HA Text AI coordinator.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import logging
import traceback
import aiofiles
import os
import json
import asyncio
import psutil
import re
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME

from .config_flow import normalize_name
from .const import (
    DOMAIN,
    STATE_READY,
    STATE_PROCESSING,
    STATE_ERROR,
    STATE_RATE_LIMITED,
    STATE_MAINTENANCE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_CONTEXT_MESSAGES,
    ABSOLUTE_MAX_HISTORY_SIZE,
    MAX_ATTRIBUTE_SIZE,
    MAX_HISTORY_FILE_SIZE,
    TRUNCATION_INDICATOR,
)

_LOGGER = logging.getLogger(__name__)


class AsyncFileHandler:
    """Async context manager for file operations."""

    def __init__(self, file_path: str, mode: str = 'a'):
        self.file_path = file_path
        self.mode = mode

    async def __aenter__(self):
        self.file = await aiofiles.open(self.file_path, self.mode)
        return self.file

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.file.close()

class HATextAICoordinator(DataUpdateCoordinator):
    """Home Assistant Text AI Conversation Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,
        model: str,
        update_interval: int,
        instance_name: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_history_size: int = DEFAULT_MAX_HISTORY,
        context_messages: int = DEFAULT_CONTEXT_MESSAGES,
        is_anthropic: bool = False,
    ) -> None:
        """Initialize coordinator."""
        self.instance_name = instance_name
        self.normalized_name = None

        # Use the normalize_name function from config_flow to ensure consistency
        from .config_flow import normalize_name

        self.normalized_name = normalize_name(instance_name)
        self._metrics_file = os.path.join(
            hass.config.path(".storage"),
            "ha_text_ai_history",
            f"ha_text_ai_metrics_{normalize_name(instance_name)}.json"
        )

        # Initialize performance metrics first
        self._performance_metrics = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_errors": 0,
            "average_latency": 0,
            "max_latency": 0,
            "min_latency": float("inf"),
        }

        # Continue with other initializations
        self.hass = hass
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_history_size = min(
            max(1, max_history_size),
            ABSOLUTE_MAX_HISTORY_SIZE
        )
        self.is_anthropic = is_anthropic

        # Initialize essential attributes
        self._is_processing = False
        self._is_rate_limited = False
        self._is_maintenance = False
        self.endpoint_status = "ready"
        self._system_prompt = None
        self._conversation_history = []

        self._last_response = {
            "timestamp": dt_util.utcnow().isoformat(),
            "question": "",
            "response": "",
            "model": model,
            "instance": instance_name,
            "normalized_name": self.normalized_name,
            "error": None,
        }

        update_interval_td = timedelta(seconds=update_interval)

        # Call super().__init__
        super().__init__(
            hass,
            _LOGGER,
            name=instance_name,
            update_interval=update_interval_td,
        )

        # Now initialize _initial_state
        self._initial_state = {
            "state": STATE_READY,
            "metrics": self._performance_metrics.copy(),
            "last_response": self.last_response.copy(),
            "is_processing": self._is_processing,
            "is_rate_limited": self._is_rate_limited,
            "is_maintenance": self._is_maintenance,
            "endpoint_status": self.endpoint_status,
            "uptime": 0,
            "system_prompt": self._system_prompt,
            "history_size": len(self._conversation_history),
            "conversation_history": self._conversation_history.copy(),
        }

        self.available = True
        self._state = STATE_READY

        self._start_time = dt_util.utcnow()

        # Create history directory with safe mechanism
        self._history_dir = os.path.join(
            hass.config.path(".storage"),
            "ha_text_ai_history"
        )

        # Initialize all async tasks in proper order
        self.hass.async_create_task(self._create_history_dir())
        self.hass.async_create_task(self._check_history_directory())
        self.hass.async_create_task(self._initialize_metrics())
        self.hass.async_create_task(self.async_initialize_history_file())
        self.hass.async_create_task(self._migrate_history_from_txt_to_json())

        # History file path using instance name
        self._history_file = os.path.join(
            self._history_dir,
            f"{self.normalized_name}_history.json"
        )

        # Maximum history file size (1 MB) from const.py
        self._max_history_file_size = MAX_HISTORY_FILE_SIZE

        # Asynchronous file initialization
        hass.async_create_task(self.async_initialize_history_file())

        _LOGGER.info(f"Initialized HA Text AI coordinator with instance: {instance_name}")

        # Register instance
        self.hass.data.setdefault(DOMAIN, {})
        self.hass.data[DOMAIN][instance_name] = self
        self.context_messages = context_messages

    @property
    def last_response(self) -> Dict[str, Any]:
        """
        Get the last response with fallback to conversation history.

        Returns:
            Dict containing last response information
        """
        if self._last_response:
            return self._last_response

        if self._conversation_history:
            latest = self._conversation_history[-1]
            return {
                "timestamp": latest.get("timestamp"),
                "question": latest.get("question", ""),
                "response": latest.get("response", ""),
                "model": self.model,
                "instance": self.instance_name,
                "normalized_name": self.normalized_name,
                "error": None
            }

        return {
            "timestamp": dt_util.utcnow().isoformat(),
            "question": "",
            "response": "",
            "model": self.model,
            "instance": self.instance_name,
            "normalized_name": self.normalized_name,
            "error": None
        }

    @last_response.setter
    def last_response(self, value: Dict[str, Any]) -> None:
        """
        Set the last response value.

        Args:
            value: Dictionary containing response information
        """
        self._last_response = value

    async def _file_exists(self, path: str) -> bool:
        """
        Check if file exists asynchronously.

        Args:
            path (str): Full path to the file to check

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            result = await self.hass.async_add_executor_job(os.path.exists, path)

            _LOGGER.debug(f"File existence check: {path} - {'Exists' if result else 'Not Found'}")

            return result

        except Exception as e:
            _LOGGER.error(f"Error checking file existence for {path}: {e}")
            return False

    async def _create_history_dir(self) -> None:
        """
        Asynchronously create history directory.
        """
        try:
            def mkdir_sync():
                os.makedirs(self._history_dir, exist_ok=True)

            await self.hass.async_add_executor_job(mkdir_sync)
            _LOGGER.debug(f"History directory created/verified: {self._history_dir}")

        except PermissionError:
            _LOGGER.error(f"Permission denied when creating history directory: {self._history_dir}")
            raise
        except OSError as e:
            _LOGGER.error(f"Error creating history directory {self._history_dir}: {e}")
            raise

    async def _initialize_metrics(self) -> None:
        self._performance_metrics = await self._load_metrics() or {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_errors": 0,
            "average_latency": 0,
            "max_latency": 0,
            "min_latency": float("inf"),
        }

    async def _load_metrics(self) -> Dict[str, Any]:
        try:
            if await self._file_exists(self._metrics_file):
                def read_metrics():
                    with open(self._metrics_file, 'r') as f:
                        try:
                            return json.load(f)
                        except json.JSONDecodeError:
                            _LOGGER.warning("Metrics file corrupted, creating new")
                            return None
                return await self.hass.async_add_executor_job(read_metrics)
        except Exception as e:
            _LOGGER.warning(f"Failed to load metrics: {e}")
        return None

    async def _save_metrics(self) -> None:
        try:
            def write_metrics():
                with open(self._metrics_file, 'w') as f:
                    json.dump(self._performance_metrics, f)
            await self.hass.async_add_executor_job(write_metrics)
        except Exception as e:
            _LOGGER.warning(f"Failed to save metrics: {e}")

    async def _update_metrics(self, latency: float, response: dict) -> None:
        """Update performance metrics and save to storage."""
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
        metrics["min_latency"] = min(metrics["min_latency"], latency)

        # Save metrics after update
        await self._save_metrics()

    async def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics = self._performance_metrics.copy()
        _LOGGER.debug(f"Current performance metrics: {metrics}")
        return metrics

    async def _handle_error(self, error: Exception) -> None:
        """Enhanced error handling with metric persistence."""
        self._performance_metrics["total_errors"] += 1
        self._performance_metrics["failed_requests"] += 1

        # Save metrics after error
        await self._save_metrics()

        error_details = {
            "timestamp": dt_util.utcnow().isoformat(),
            "model": self.model,
            "instance": self.instance_name,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc() if _LOGGER.isEnabledFor(logging.DEBUG) else None,
        }

        # Specific error type handling
        error_mapping = {
            HomeAssistantError: {"is_ha_error": True},
            ConnectionError: {
                "is_connection_error": True,
                "is_rate_limited": True
            },
            TimeoutError: {"is_timeout": True},
            PermissionError: {"is_permission_denied": True},
            ValueError: {"is_validation_error": True}
        }

        for error_type, error_flags in error_mapping.items():
            if isinstance(error, error_type):
                error_details.update(error_flags)
                break

        # Update system state based on error type
        if error_details.get("is_rate_limited"):
            self._is_rate_limited = True
            _LOGGER.warning(f"Rate limit detected for {self.instance_name}")

        if error_details.get("is_connection_error"):
            self.endpoint_status = "unavailable"

        self.last_response = error_details
        _LOGGER.error(f"AI Processing Error: {error_details}")

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Full Error Traceback: {error_details['traceback']}")

    async def async_initialize_history_file(self) -> None:
        """
        Asynchronously initialize history file and load existing history.
        """
        try:
            await self._create_history_dir()

            if await self._file_exists(self._history_file):
                # Load existing history
                async with AsyncFileHandler(self._history_file, 'r') as f:
                    content = await f.read()
                    if content:
                        history = json.loads(content)
                        # Validate and load history
                        if isinstance(history, list):
                            self._conversation_history = history[-self.max_history_size:]
                            _LOGGER.debug(
                                f"Loaded {len(self._conversation_history)} history entries "
                                f"for {self.instance_name}"
                            )
            else:
                # Create new history file
                async with AsyncFileHandler(self._history_file, 'w') as f:
                    await f.write(json.dumps([]))

            await self._check_history_size()
            await self.async_update_ha_state()

            _LOGGER.debug(f"History file initialized: {self._history_file}")

        except Exception as e:
            _LOGGER.error(f"Could not initialize history file: {e}")
            _LOGGER.debug(traceback.format_exc())

    # Size check to _update_history method
    async def _update_history(self, question: str, response: dict) -> None:
        """Update conversation history with size validation."""
        try:
            history_entry = {
                "timestamp": dt_util.utcnow().isoformat(),
                "question": self._truncate_text(question, MAX_ATTRIBUTE_SIZE),
                "response": self._truncate_text(
                    response.get("content", ""),
                    MAX_ATTRIBUTE_SIZE
                ),
            }

            # Check approximate entry size
            entry_size = len(json.dumps(history_entry).encode('utf-8'))
            current_size = await self._check_file_size(self._history_file)

            if current_size + entry_size > MAX_HISTORY_FILE_SIZE:
                _LOGGER.warning(
                    f"History size limit approaching. "
                    f"Current: {current_size}, "
                    f"Entry: {entry_size}, "
                    f"Max: {MAX_HISTORY_FILE_SIZE}"
                )
                await self._rotate_history()

            self._conversation_history.append(history_entry)

            # Enforce size limit
            while len(self._conversation_history) > self.max_history_size:
                self._conversation_history.pop(0)

            await self._write_history_entry(history_entry)

        except Exception as e:
            _LOGGER.error(f"Error updating history: {e}")
            _LOGGER.debug(traceback.format_exc())

    async def _write_history_entry(self, entry: dict) -> None:
        """Write history entry with file size checks."""
        try:
            if not await self._file_exists(self._history_dir):
                await self._create_history_dir()

            # Check current file size
            current_size = 0
            if await self._file_exists(self._history_file):
                current_size = await self.hass.async_add_executor_job(
                    os.path.getsize,
                    self._history_file
                )

            # Calculate approximate entry size
            entry_size = len(json.dumps(entry).encode('utf-8'))

            if current_size + entry_size > MAX_HISTORY_FILE_SIZE:
                _LOGGER.warning(
                    f"History file size limit reached. Current: {current_size}, "
                    f"Entry size: {entry_size}, Max: {MAX_HISTORY_FILE_SIZE}"
                )
                # Trigger rotation before writing
                await self._rotate_history()

            # Continue with writing
            history = []
            if await self._file_exists(self._history_file):
                async with AsyncFileHandler(self._history_file, 'r') as f:
                    content = await f.read()
                    if content:
                        history = json.loads(content)

            history.append(entry)

            if len(history) > self.max_history_size:
                history = history[-self.max_history_size:]

            async with AsyncFileHandler(self._history_file, 'w') as f:
                await f.write(json.dumps(history, indent=2))

        except Exception as e:
            _LOGGER.error(f"Error writing history entry: {e}")
            _LOGGER.debug(traceback.format_exc())

    async def _check_history_size(self) -> None:
        """Verify and adjust history size if needed."""
        if len(self._conversation_history) > self.max_history_size:
            _LOGGER.warning(
                f"History size ({len(self._conversation_history)}) exceeds "
                f"maximum ({self.max_history_size}). Trimming..."
            )
            self._conversation_history = self._conversation_history[-self.max_history_size:]

    async def _check_file_size(self, file_path: str) -> int:
        """
        Check file size asynchronously.

        Args:
            file_path: Path to file to check

        Returns:
            int: File size in bytes
        """
        try:
            if await self._file_exists(file_path):
                size = await self.hass.async_add_executor_job(os.path.getsize, file_path)
                _LOGGER.debug(f"File size check for {file_path}: {size} bytes")
                return size
            return 0
        except Exception as e:
            _LOGGER.error(f"Error checking file size for {file_path}: {e}")
            return 0

    def _sync_write_history_entry(self, entry: dict) -> None:
        """Synchronous method to write history entry with enhanced error handling."""
        try:
            history = []
            if os.path.exists(self._history_file):
                try:
                    with open(self._history_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            history = json.loads(content)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    _LOGGER.warning(f"Corrupted history file, creating new: {e}")
                    # Backup corrupted file
                    backup_path = f"{self._history_file}.corrupted.{dt_util.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        os.rename(self._history_file, backup_path)
                        _LOGGER.info(f"Corrupted history backed up to: {backup_path}")
                    except OSError:
                        pass
                except PermissionError as e:
                    _LOGGER.error(f"Permission denied reading history file: {e}")
                    raise
                except OSError as e:
                    _LOGGER.error(f"OS error reading history file: {e}")
                    raise

            history.append(entry)

            if len(history) > self.max_history_size:
                history = history[-self.max_history_size:]

            # Write with atomic operation
            temp_file = f"{self._history_file}.tmp"
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
                os.replace(temp_file, self._history_file)
            except PermissionError as e:
                _LOGGER.error(f"Permission denied writing history file: {e}")
                raise
            except OSError as e:
                _LOGGER.error(f"OS error writing history file: {e}")
                # Clean up temp file if it exists
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
                raise

        except Exception as e:
            _LOGGER.error(f"Synchronous history entry writing failed: {e}")
            raise

    async def _rotate_history(self) -> None:
        """Rotate conversation history with file management."""
        try:
            _LOGGER.debug(f"Starting history rotation for {self._history_file}")
            await self.hass.async_add_executor_job(self._rotate_history_files)
            _LOGGER.debug(f"Completed history rotation")
        except Exception as e:
            _LOGGER.error(f"Error rotating history: {e}")
            _LOGGER.debug(traceback.format_exc())

    async def _check_history_directory(self) -> None:
        """
        Asynchronously check history directory permissions and writability.
        """
        try:
            # First ensure directory exists
            await self._create_history_dir()

            # Then test write permission in a separate thread
            test_file_path = os.path.join(self._history_dir, ".write_test")
            await self.hass.async_add_executor_job(self._sync_test_directory_write, test_file_path)

        except PermissionError:
            _LOGGER.error(f"No write permissions for history directory: {self._history_dir}")
        except Exception as e:
            _LOGGER.error(f"Error checking history directory: {e}")

    def _sync_test_directory_write(self, test_file_path: str) -> None:
        """
        Synchronous method to test directory write permissions.
        """
        try:
            with open(test_file_path, 'w') as f:
                f.write("Permission test")
            os.remove(test_file_path)
        except Exception as e:
            _LOGGER.error(f"Directory write test failed: {e}")

    async def _rotate_history_files(self) -> None:
        """Rotate history files with size validation."""
        try:
            if await self._file_exists(self._history_file):
                current_size = await self._check_file_size(self._history_file)

                if current_size > MAX_HISTORY_FILE_SIZE:
                    _LOGGER.info(
                        f"Rotating history file. "
                        f"Current size: {current_size}, "
                        f"Max allowed: {MAX_HISTORY_FILE_SIZE}"
                    )

                    # Create archive filename with timestamp
                    archive_file = os.path.join(
                        self._history_dir,
                        f"{self.normalized_name}_history_{dt_util.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                    )

                    # Rotate files
                    await self.hass.async_add_executor_job(
                        os.rename,
                        self._history_file,
                        archive_file
                    )

                    # Create new history file with recent entries
                    async with AsyncFileHandler(self._history_file, 'w') as f:
                        await f.write(json.dumps(
                            self._conversation_history[-self.max_history_size:],
                            indent=2
                        ))

                    _LOGGER.info(f"History file rotated to: {archive_file}")

        except Exception as e:
            _LOGGER.error(f"History rotation failed: {e}")
            _LOGGER.debug(traceback.format_exc())

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update coordinator data with improved error handling and performance."""
        try:
            async with asyncio.Semaphore(1):
                current_state = self._get_current_state()

                # Get limited history with info
                history_data = await self._get_limited_history()

                metrics = await self._get_current_metrics()
                if metrics is None:
                    metrics = {}

                data = {
                    "state": current_state,
                    "metrics": metrics,
                    "last_response": await self._get_sanitized_last_response(),
                    "is_processing": self._is_processing,
                    "is_rate_limited": self._is_rate_limited,
                    "is_maintenance": self._is_maintenance,
                    "endpoint_status": self.endpoint_status,
                    "uptime": self._calculate_uptime(),
                    "system_prompt": self._get_truncated_system_prompt(),
                    "history_size": len(self._conversation_history),
                    "conversation_history": history_data["entries"],
                    "history_info": history_data["info"],
                    "normalized_name": self.normalized_name,
                }

                await self._validate_update_data(data)
                return data

        except Exception as err:
            _LOGGER.error(f"Error updating data: {err}", exc_info=True)
            return self._get_safe_initial_state()

    async def _get_limited_history(self) -> Dict[str, Any]:
        """Get limited conversation history showing only last Q&A."""
        limited_history = []

        if self._conversation_history:
            last_entry = self._conversation_history[-1]
            limited_entry = {
                "timestamp": last_entry["timestamp"],
                "question": last_entry["question"][:4096] + (TRUNCATION_INDICATOR if len(last_entry["question"]) > 4096 else ""),
                "response": last_entry["response"][:4096] + (TRUNCATION_INDICATOR if len(last_entry["response"]) > 4096 else ""),
            }
            limited_history.append(limited_entry)

        history_info = {
            "total_entries": len(self._conversation_history),
            "displayed_entries": len(limited_history),
            "full_history_available": True,
            "history_path": self._history_file,
        }

        return {
            "entries": limited_history,
            "full_history": self._conversation_history,
            "info": history_info
        }

    async def _get_sanitized_last_response(self) -> Dict[str, Any]:
        """Get sanitized version of last response with truncation indicators."""
        response = self.last_response.copy()

        if "response" in response:
            original_response = response["response"]
            is_response_truncated = len(original_response) > 4096
            response["response"] = original_response[:4096] + (TRUNCATION_INDICATOR if is_response_truncated else "")
            response["is_response_truncated"] = is_response_truncated
            response["full_response_length"] = len(original_response)

        if "question" in response:
            original_question = response["question"]
            is_question_truncated = len(original_question) > 4096
            response["question"] = original_question[:4096] + (TRUNCATION_INDICATOR if is_question_truncated else "")
            response["is_question_truncated"] = is_question_truncated
            response["full_question_length"] = len(original_question)

        return response

    def _truncate_text(self, text: str, max_length: int = MAX_ATTRIBUTE_SIZE) -> str:
        """Safely truncate text to maximum length."""
        return text[:max_length] if text else ""

    def _calculate_uptime(self) -> float:
        """Calculate current uptime in seconds."""
        return (dt_util.utcnow() - self._start_time).total_seconds()

    def _get_truncated_system_prompt(self) -> Optional[str]:
        """Get truncated system prompt."""
        return self._truncate_text(self._system_prompt, 4096) if self._system_prompt else None

    async def _validate_update_data(self, data: Dict[str, Any]) -> None:
        """Validate update data structure and content."""
        required_keys = ["state", "metrics", "last_response"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")

        if not isinstance(data["metrics"], dict):
            raise ValueError("Invalid metrics format")

    async def async_update_ha_state(self) -> None:
        """Update Home Assistant state."""
        try:
            _LOGGER.debug(
                f"Requesting state update for {self.instance_name} (normalized: {self.normalized_name})"
            )
            await self.async_request_refresh()

            # Force update of all entities
            entity_id_base = f"sensor.ha_text_ai_{self.normalized_name.lower()}"
            for entity_id in self.hass.states.async_entity_ids():
                if entity_id.startswith(entity_id_base):
                    self.hass.states.async_set(entity_id, self._get_current_state())

        except Exception as err:
            _LOGGER.error(f"Error updating HA state for {self.instance_name}: {err}")

    def _get_current_state(self) -> str:
        """Get current state based on internal flags."""
        if self._is_processing:
            return STATE_PROCESSING
        elif self._is_rate_limited:
            return STATE_RATE_LIMITED
        elif self._is_maintenance:
            return STATE_MAINTENANCE
        elif self.last_response.get("error"):
            return STATE_ERROR
        return STATE_READY

    def _get_safe_initial_state(self) -> Dict[str, Any]:
        """Return safe initial state when update fails."""
        return {
            "state": STATE_ERROR,
            "metrics": {},
            "last_response": self.last_response,
            "is_processing": False,
            "is_rate_limited": False,
            "is_maintenance": False,
            "endpoint_status": "error",
            "uptime": self._calculate_uptime(),
            "system_prompt": None,
            "history_size": 0,
            "conversation_history": [],
            "normalized_name": self.normalized_name,
        }

    async def async_ask_question(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        context_messages: Optional[int] = None,
    ) -> dict:
        """
        Process a question with optional parameters.

        This method is a direct wrapper around async_process_question,
        allowing flexible AI interaction with optional model, temperature,
        and context customization.

        Args:
            question: The input question or prompt
            model: Optional AI model to use
            temperature: Optional response creativity level
            max_tokens: Optional maximum response length
            system_prompt: Optional system-level instruction
            context_messages: Optional number of context messages to include

        Returns:
            Full response dictionary from the AI
        """
        return await self.async_process_question(
            question, model, temperature, max_tokens, system_prompt, context_messages
        )

    async def async_process_question(
            self,
            question: str,
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            system_prompt: Optional[str] = None,
            context_messages: Optional[int] = None,
        ) -> dict:
            """Process question with context management."""
            if self.client is None:
                raise HomeAssistantError("AI client not initialized")

            try:
                self._is_processing = True
                await self.async_update_ha_state()

                temp_context_messages = context_messages or self.context_messages
                temp_model = model or self.model
                temp_temperature = temperature or self.temperature
                temp_max_tokens = max_tokens or self.max_tokens
                temp_system_prompt = system_prompt or self._system_prompt

                # Start timing
                start_time = dt_util.utcnow()

                # Prepare messages with system prompt
                messages = []
                if temp_system_prompt:
                    messages.append({"role": "system", "content": temp_system_prompt})

                # Add context from history
                context_history = self._conversation_history[-temp_context_messages:]
                for entry in context_history:
                    messages.append({"role": "user", "content": entry["question"]})
                    messages.append({"role": "assistant", "content": entry["response"]})

                # Add current question
                messages.append({"role": "user", "content": question})

                # Process message
                kwargs = {
                    "model": temp_model,
                    "temperature": temp_temperature,
                    "max_tokens": temp_max_tokens,
                    "messages": messages,
                }

                response = await self.async_process_message(question, **kwargs)

                # Update metrics
                end_time = dt_util.utcnow()
                latency = (end_time - start_time).total_seconds()
                await self._update_metrics(latency, response)

                await self._update_history(question, response)

                return response

            except Exception as err:
                self._handle_error(err)
                raise HomeAssistantError(f"Failed to process question: {err}")

            finally:
                self._is_processing = False
                await self.async_update_ha_state()

    async def async_process_message(self, question: str, **kwargs) -> dict:
        """Process message using the AI client."""
        try:
            async with asyncio.timeout(60):  # 60 second timeout
                if self.is_anthropic:
                    response = await self._process_anthropic_message(question, **kwargs)
                else:
                    response = await self._process_openai_message(question, **kwargs)

            # Add timestamp and model information to response
            timestamp = dt_util.utcnow().isoformat()
            model_used = kwargs.get("model", self.model)
            
            # Enhance response with metadata
            enhanced_response = {
                "content": response["content"],
                "tokens": response.get("tokens", {}),
                "model": model_used,
                "timestamp": timestamp,
                "instance": self.instance_name,
                "question": question,
                "success": True
            }

            self.last_response = {
                "timestamp": timestamp,
                "question": question,
                "response": response["content"],
                "model": model_used,
                "instance": self.instance_name,
                "normalized_name": self.normalized_name,
                "error": None,
            }

            return enhanced_response

        except asyncio.TimeoutError:
            raise HomeAssistantError("Request timed out")

        except Exception as err:
            await self._handle_error(err)
            raise

    async def _process_anthropic_message(self, question: str, **kwargs) -> dict:
        """Process message using Anthropic API."""
        try:
            _LOGGER.debug(f"Anthropic API call: model={kwargs['model']}, max_tokens={kwargs['max_tokens']}")
            response = await self.client.messages.create(
                model=kwargs["model"],
                max_tokens=kwargs["max_tokens"],
                messages=kwargs["messages"],
                temperature=kwargs["temperature"],
            )
            _LOGGER.debug(f"Anthropic response: tokens={response.usage}")
            return {
                "content": response.content[0].text,
                "tokens": {
                    "prompt": response.usage.input_tokens,
                    "completion": response.usage.output_tokens,
                    "total": response.usage.input_tokens + response.usage.output_tokens,
                },
            }
        except Exception as e:
            _LOGGER.error(f"Anthropic API error: {str(e)}")
            raise

    async def _process_openai_message(self, question: str, **kwargs) -> dict:
        """Process message using OpenAI API."""
        try:
            response = await self.client.create(
                model=kwargs["model"],
                messages=kwargs["messages"],
                temperature=kwargs["temperature"],
                max_tokens=kwargs["max_tokens"],
            )

            return {
                "content": response["choices"][0]["message"]["content"],
                "tokens": {
                    "prompt": response["usage"]["prompt_tokens"],
                    "completion": response["usage"]["completion_tokens"],
                    "total": response["usage"]["total_tokens"],
                },
            }
        except Exception as e:
            _LOGGER.error(f"Error in OpenAI API call: {str(e)}")
            raise

    async def _migrate_history_from_txt_to_json(self) -> None:
        try:
            old_history_file = os.path.join(
                self._history_dir,
                f"{self.normalized_name}_history.txt"
            )

            if not await self._file_exists(old_history_file):
                return

            _LOGGER.info(f"Found old history file for {self.instance_name}, starting migration to JSON format")

            # Read old history
            history_entries = []
            async with AsyncFileHandler(old_history_file, 'r') as f:
                content = await f.read()

            # Parse txt content
            for line in content.split('\n'):
                if not line or line.startswith("History initialized at:"):
                    continue

                try:
                    # Parse the old format: "timestamp: Question: question - Response: response"
                    parts = line.split(': ', 1)
                    if len(parts) != 2:
                        continue

                    timestamp = parts[0]
                    content_parts = parts[1].split(' - ')
                    if len(content_parts) != 2:
                        continue

                    question = content_parts[0].replace('Question: ', '')
                    response = content_parts[1].replace('Response: ', '')

                    history_entries.append({
                        "timestamp": timestamp,
                        "question": question,
                        "response": response
                    })

                except Exception as e:
                    _LOGGER.warning(f"Error parsing history line: {line}. Error: {e}")
                    continue

            if history_entries:
                # Write to new JSON file
                async with AsyncFileHandler(self._history_file, 'w') as f:
                    await f.write(json.dumps(history_entries, indent=2))

                # Backup old file
                backup_file = old_history_file + '.backup'
                os.rename(old_history_file, backup_file)

                _LOGGER.info(
                    f"Successfully migrated {len(history_entries)} entries "
                    f"from txt to JSON for {self.instance_name}. "
                    f"Old file backed up as {backup_file}"
                )

                # Update in-memory history
                self._conversation_history = history_entries

        except Exception as e:
            _LOGGER.error(f"Error during history migration for {self.instance_name}: {e}")
            _LOGGER.debug(traceback.format_exc())

    async def async_clear_history(self) -> None:
        """
        Asynchronously clear conversation history.

        Removes in-memory history and deletes history file.
        """
        try:
            self._conversation_history = []
            if await self._file_exists(self._history_file):
                await self.hass.async_add_executor_job(os.remove, self._history_file)
            await self.async_update_ha_state()
            _LOGGER.info(f"History for {self.instance_name} cleared successfully")
        except Exception as e:
            _LOGGER.error(f"Error clearing history: {e}")
            _LOGGER.debug(traceback.format_exc())

    async def async_get_history(
        self,
        limit: Optional[int] = None,
        filter_model: Optional[str] = None,
        start_date: Optional[str] = None,
        include_metadata: bool = False,
        sort_order: str = "newest"
    ) -> List[Dict[str, Any]]:
        """Get conversation history with optional filtering and sorting."""
        try:
            history = self._conversation_history.copy()
            
            # Filter by model if specified
            if filter_model:
                history = [entry for entry in history if entry.get("model") == filter_model]
            
            # Filter by start date if specified
            if start_date:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    history = [
                        entry for entry in history 
                        if datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00')) >= start_dt
                    ]
                except (ValueError, KeyError) as e:
                    _LOGGER.warning(f"Invalid start_date format: {start_date}. Error: {e}")
            
            # Sort history
            if sort_order == "oldest":
                history.sort(key=lambda x: x.get("timestamp", ""))
            else:  # newest (default)
                history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Apply limit
            if limit and limit > 0:
                history = history[:limit]
            
            # Add metadata if requested
            if include_metadata:
                for entry in history:
                    entry["metadata"] = {
                        "entry_size": len(str(entry)),
                        "question_length": len(entry.get("question", "")),
                        "response_length": len(entry.get("response", "")),
                        "model_used": entry.get("model", self.model),
                        "instance": self.instance_name
                    }
            
            return history
            
        except Exception as e:
            _LOGGER.error(f"Error getting history: {e}")
            return []

    async def async_set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        self._system_prompt = prompt
        await self.async_update_ha_state()

    def _check_memory_available(self) -> bool:
        """Check if enough memory is available."""
        try:
            memory = psutil.virtual_memory()
            
            # Log the total and available memory
            _LOGGER.debug("Total memory: %s, Available memory: %s", memory.total, memory.available)
            
            if memory.available > 1024 * 1024 * 100:  # 100MB
                _LOGGER.debug("Sufficient memory available: %s bytes", memory.available)
                return True
            else:
                _LOGGER.warning("Insufficient memory available: %s bytes", memory.available)
                return False
        except Exception as e:
            _LOGGER.error("Error checking memory availability: %s", e)
            return True  # Assume memory is available if check fails

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        _LOGGER.debug(f"Shutting down coordinator for {self.instance_name}")
        self.hass.data[DOMAIN].pop(self.instance_name, None)
