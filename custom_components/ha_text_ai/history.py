"""
History management for HA Text AI integration.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiofiles

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    ABSOLUTE_MAX_HISTORY_SIZE,
    MAX_ATTRIBUTE_SIZE,
    MAX_HISTORY_FILE_SIZE,
    TRUNCATION_INDICATOR,
)

# Per-entry storage cap (32KB per field) to prevent disk exhaustion
MAX_STORED_FIELD_SIZE = 32 * 1024
MAX_ARCHIVE_FILES = 3

_LOGGER = logging.getLogger(__name__)


class AsyncFileHandler:
    """Async context manager for file operations."""

    def __init__(self, file_path: str, mode: str = "a"):
        self.file_path = file_path
        self.mode = mode

    async def __aenter__(self):
        self.file = await aiofiles.open(self.file_path, self.mode)
        return self.file

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.file.close()


class HistoryManager:
    """Manages conversation history for an instance."""

    def __init__(
        self,
        hass: HomeAssistant,
        instance_name: str,
        normalized_name: str,
        history_dir: str,
        max_history_size: int,
    ) -> None:
        self.hass = hass
        self.instance_name = instance_name
        self.normalized_name = normalized_name
        self._history_dir = history_dir
        self.max_history_size = min(
            max(1, max_history_size), ABSOLUTE_MAX_HISTORY_SIZE
        )
        self._history_file = os.path.join(
            history_dir, f"{normalized_name}_history.json"
        )
        self._max_history_file_size = MAX_HISTORY_FILE_SIZE
        self._conversation_history: List[Dict[str, Any]] = []

    @property
    def conversation_history(self) -> List[Dict[str, Any]]:
        return self._conversation_history

    @property
    def history_size(self) -> int:
        return len(self._conversation_history)

    async def async_initialize(self) -> None:
        """Initialize history: directories, file, migration."""
        await self._create_history_dir()
        await self._check_history_directory()
        await self._initialize_history_file()
        await self._migrate_history_from_txt_to_json()

    async def _file_exists(self, path: str) -> bool:
        try:
            return await self.hass.async_add_executor_job(os.path.exists, path)
        except Exception as e:
            _LOGGER.error("Error checking file existence for %s: %s", path, e)
            return False

    async def _create_history_dir(self) -> None:
        try:
            await self.hass.async_add_executor_job(
                os.makedirs, self._history_dir, 0o755, True
            )
        except PermissionError:
            _LOGGER.error("Permission denied creating history directory: %s", self._history_dir)
            raise
        except OSError as e:
            _LOGGER.error("Error creating history directory %s: %s", self._history_dir, e)
            raise

    async def _check_history_directory(self) -> None:
        """Check history directory permissions and writability."""
        try:
            test_file_path = os.path.join(self._history_dir, ".write_test")
            await self.hass.async_add_executor_job(
                self._sync_test_directory_write, test_file_path
            )
        except PermissionError:
            _LOGGER.error("No write permissions for history directory: %s", self._history_dir)
        except Exception as e:
            _LOGGER.error("Error checking history directory: %s", e)

    @staticmethod
    def _sync_test_directory_write(test_file_path: str) -> None:
        try:
            with open(test_file_path, "w") as f:
                f.write("Permission test")
            os.remove(test_file_path)
        except Exception as e:
            _LOGGER.error("Directory write test failed: %s", e)

    async def _initialize_history_file(self) -> None:
        """Initialize history file and load existing history."""
        try:
            if await self._file_exists(self._history_file):
                async with AsyncFileHandler(self._history_file, "r") as f:
                    content = await f.read()
                    if content:
                        history = json.loads(content)
                        if isinstance(history, list):
                            self._conversation_history = history[
                                -self.max_history_size :
                            ]
                            _LOGGER.debug(
                                "Loaded %d history entries for %s",
                                len(self._conversation_history),
                                self.instance_name,
                            )
            else:
                async with AsyncFileHandler(self._history_file, "w") as f:
                    await f.write(json.dumps([]))

            await self._check_history_size()
        except Exception as e:
            _LOGGER.error("Could not initialize history file: %s", e)
            _LOGGER.debug(traceback.format_exc())

    async def update_history(self, question: str, response: dict) -> None:
        """Update conversation history.

        In-memory history stores full text for context retrieval.
        On-disk storage caps per-field size to prevent disk exhaustion.
        Display truncation is handled by get_limited_history().
        """
        try:
            content = response.get("content", "")
            history_entry = {
                "timestamp": dt_util.utcnow().isoformat(),
                "question": question[:MAX_STORED_FIELD_SIZE],
                "response": content[:MAX_STORED_FIELD_SIZE],
            }

            self._conversation_history.append(history_entry)

            while len(self._conversation_history) > self.max_history_size:
                self._conversation_history.pop(0)

            await self._save_history_to_file()
        except Exception as e:
            _LOGGER.error("Error updating history: %s", e)
            _LOGGER.debug(traceback.format_exc())

    async def _save_history_to_file(self) -> None:
        """Serialize in-memory history to file with rotation if needed."""
        try:
            data = json.dumps(self._conversation_history, indent=2)
            data_size = len(data.encode("utf-8"))

            if data_size > MAX_HISTORY_FILE_SIZE:
                await self._rotate_history()

            async with AsyncFileHandler(self._history_file, "w") as f:
                await f.write(data)
        except Exception as e:
            _LOGGER.error("Error writing history file: %s", e)
            _LOGGER.debug(traceback.format_exc())

    async def _check_history_size(self) -> None:
        if len(self._conversation_history) > self.max_history_size:
            _LOGGER.warning(
                "History size (%d) exceeds maximum (%d). Trimming...",
                len(self._conversation_history), self.max_history_size,
            )
            self._conversation_history = self._conversation_history[
                -self.max_history_size :
            ]

    async def _check_file_size(self, file_path: str) -> int:
        try:
            if await self._file_exists(file_path):
                return await self.hass.async_add_executor_job(
                    os.path.getsize, file_path
                )
            return 0
        except Exception as e:
            _LOGGER.error("Error checking file size for %s: %s", file_path, e)
            return 0

    async def _rotate_history(self) -> None:
        try:
            _LOGGER.debug("Starting history rotation for %s", self._history_file)
            await self._rotate_history_files()
        except Exception as e:
            _LOGGER.error("Error rotating history: %s", e)
            _LOGGER.debug(traceback.format_exc())

    async def _rotate_history_files(self) -> None:
        """Rotate history files with size validation."""
        try:
            if await self._file_exists(self._history_file):
                current_size = await self._check_file_size(self._history_file)

                if current_size > MAX_HISTORY_FILE_SIZE:
                    _LOGGER.info(
                        "Rotating history file. Current size: %d, Max: %d",
                        current_size, MAX_HISTORY_FILE_SIZE,
                    )

                    archive_file = os.path.join(
                        self._history_dir,
                        f"{self.normalized_name}_history_{dt_util.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                    )

                    await self.hass.async_add_executor_job(
                        shutil.move, self._history_file, archive_file
                    )

                    async with AsyncFileHandler(self._history_file, "w") as f:
                        await f.write(
                            json.dumps(
                                self._conversation_history[
                                    -self.max_history_size :
                                ],
                                indent=2,
                            )
                        )

                    _LOGGER.info("History file rotated to: %s", archive_file)

                    # Clean up old archive files, keep only MAX_ARCHIVE_FILES
                    await self._cleanup_archives()
        except Exception as e:
            _LOGGER.error("History rotation failed: %s", e)
            _LOGGER.debug(traceback.format_exc())

    async def _cleanup_archives(self) -> None:
        """Remove old archive files beyond MAX_ARCHIVE_FILES."""
        try:
            prefix = f"{self.normalized_name}_history_"

            def find_archives():
                archives = []
                for f in os.listdir(self._history_dir):
                    if f.startswith(prefix) and f.endswith(".json") and f != os.path.basename(self._history_file):
                        archives.append(os.path.join(self._history_dir, f))
                archives.sort()
                return archives

            archives = await self.hass.async_add_executor_job(find_archives)
            if len(archives) > MAX_ARCHIVE_FILES:
                for old_file in archives[:-MAX_ARCHIVE_FILES]:
                    await self.hass.async_add_executor_job(os.remove, old_file)
                    _LOGGER.debug("Removed old archive: %s", old_file)
        except Exception as e:
            _LOGGER.warning("Archive cleanup error: %s", e)

    async def _migrate_history_from_txt_to_json(self) -> None:
        """Migrate old .txt history to .json format."""
        try:
            old_history_file = os.path.join(
                self._history_dir, f"{self.normalized_name}_history.txt"
            )

            if not await self._file_exists(old_history_file):
                return

            # Skip migration if JSON history already has entries
            if self._conversation_history:
                _LOGGER.debug(
                    "JSON history already has %d entries for %s, skipping txt migration",
                    len(self._conversation_history), self.instance_name,
                )
                return

            _LOGGER.info(
                "Found old history file for %s, migrating to JSON", self.instance_name
            )

            history_entries = []
            async with AsyncFileHandler(old_history_file, "r") as f:
                content = await f.read()

            for line in content.split("\n"):
                if not line or line.startswith("History initialized at:"):
                    continue
                try:
                    parts = line.split(": ", 1)
                    if len(parts) != 2:
                        continue
                    timestamp = parts[0]
                    content_parts = parts[1].split(" - ")
                    if len(content_parts) != 2:
                        continue
                    question = content_parts[0].replace("Question: ", "")
                    response = content_parts[1].replace("Response: ", "")
                    history_entries.append(
                        {
                            "timestamp": timestamp,
                            "question": question,
                            "response": response,
                        }
                    )
                except Exception as e:
                    _LOGGER.warning("Error parsing history line: %s. Error: %s", line, e)
                    continue

            if history_entries:
                async with AsyncFileHandler(self._history_file, "w") as f:
                    await f.write(json.dumps(history_entries, indent=2))

                backup_file = old_history_file + ".backup"
                await self.hass.async_add_executor_job(
                    shutil.move, old_history_file, backup_file
                )

                _LOGGER.info(
                    "Migrated %d entries from txt to JSON for %s. Old file: %s",
                    len(history_entries), self.instance_name, backup_file,
                )

                self._conversation_history = history_entries
        except Exception as e:
            _LOGGER.error("Error during history migration for %s: %s", self.instance_name, e)
            _LOGGER.debug(traceback.format_exc())

    async def async_clear_history(self) -> None:
        """Clear conversation history."""
        try:
            self._conversation_history = []
            if await self._file_exists(self._history_file):
                await self.hass.async_add_executor_job(os.remove, self._history_file)
            _LOGGER.info("History for %s cleared", self.instance_name)
        except Exception as e:
            _LOGGER.error("Error clearing history: %s", e)
            _LOGGER.debug(traceback.format_exc())

    async def async_get_history(
        self,
        limit: Optional[int] = None,
        filter_model: Optional[str] = None,
        start_date: Optional[str] = None,
        include_metadata: bool = False,
        sort_order: str = "newest",
        default_model: str = "",
    ) -> List[Dict[str, Any]]:
        """Get conversation history with optional filtering and sorting."""
        try:
            history = self._conversation_history.copy()

            if filter_model:
                history = [
                    entry for entry in history if entry.get("model") == filter_model
                ]

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(
                        start_date.replace("Z", "+00:00")
                    )
                    history = [
                        entry
                        for entry in history
                        if datetime.fromisoformat(
                            entry["timestamp"].replace("Z", "+00:00")
                        )
                        >= start_dt
                    ]
                except (ValueError, KeyError) as e:
                    _LOGGER.warning("Invalid start_date format: %s. Error: %s", start_date, e)

            if sort_order == "oldest":
                history.sort(key=lambda x: x.get("timestamp", ""))
            else:
                history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            if limit and limit > 0:
                history = history[:limit]

            if include_metadata:
                enriched = []
                for entry in history:
                    enriched_entry = dict(entry)
                    enriched_entry["metadata"] = {
                        "entry_size": len(str(entry)),
                        "question_length": len(entry.get("question", "")),
                        "response_length": len(entry.get("response", "")),
                        "model_used": entry.get("model", default_model),
                        "instance": self.instance_name,
                    }
                    enriched.append(enriched_entry)
                return enriched

            return history
        except Exception as e:
            _LOGGER.error("Error getting history: %s", e)
            return []

    def get_limited_history(self, max_display: int = 5) -> Dict[str, Any]:
        """Get limited conversation history for sensor attributes.

        Returns last `max_display` entries with truncated text for HA state.
        """
        recent = self._conversation_history[-max_display:]
        limited_history = [
            {
                "timestamp": entry["timestamp"],
                "question": self._truncate_text(entry["question"], 4096),
                "response": self._truncate_text(entry["response"], 4096),
            }
            for entry in recent
        ]

        return {
            "entries": limited_history,
            "info": {
                "total_entries": len(self._conversation_history),
                "displayed_entries": len(limited_history),
            },
        }

    @staticmethod
    def _truncate_text(text: str, max_length: int = MAX_ATTRIBUTE_SIZE) -> str:
        """Safely truncate text to maximum length with indicator."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length] + TRUNCATION_INDICATOR
