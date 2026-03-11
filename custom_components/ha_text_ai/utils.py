"""
Utility functions for HA Text AI integration.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
import hashlib
from typing import Any

from homeassistant.const import CONF_API_KEY


def normalize_name(name: str) -> str:
    """Normalize name to conform to HA naming convention using underscores."""
    normalized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
    normalized = '_'.join(filter(None, normalized.split('_')))
    return normalized.lower()


def get_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def safe_log_data(
    data: dict[str, Any],
    sensitive_keys: tuple[str, ...] = (CONF_API_KEY,),
) -> dict[str, Any]:
    """Filter sensitive keys from data for safe logging."""
    return {k: "***" if k in sensitive_keys else v for k, v in data.items()}
