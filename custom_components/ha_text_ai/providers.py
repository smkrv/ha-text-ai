"""
Provider registry for HA Text AI integration.

Centralizes provider-specific configuration to avoid dispatch duplication
across __init__.py, config_flow.py, and api_client.py.

@license: PolyForm Noncommercial 1.0.0 (https://polyformproject.org/licenses/noncommercial/1.0.0)
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

from typing import Any

from .const import (
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_DEEPSEEK,
    API_PROVIDER_GEMINI,
    DEFAULT_MODEL,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_ENDPOINT,
    DEFAULT_ANTHROPIC_ENDPOINT,
    DEFAULT_DEEPSEEK_ENDPOINT,
    DEFAULT_GEMINI_ENDPOINT,
)

PROVIDER_REGISTRY: dict[str, dict[str, Any]] = {
    API_PROVIDER_OPENAI: {
        "default_model": DEFAULT_MODEL,
        "default_endpoint": DEFAULT_OPENAI_ENDPOINT,
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "check_path": "/models",
    },
    API_PROVIDER_ANTHROPIC: {
        "default_model": DEFAULT_ANTHROPIC_MODEL,
        "default_endpoint": DEFAULT_ANTHROPIC_ENDPOINT,
        "auth_header": "x-api-key",
        "auth_prefix": "",
        "check_path": "/v1/models",
        "extra_headers": {
            "anthropic-version": "2023-06-01",
        },
    },
    API_PROVIDER_DEEPSEEK: {
        "default_model": DEFAULT_DEEPSEEK_MODEL,
        "default_endpoint": DEFAULT_DEEPSEEK_ENDPOINT,
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "check_path": "/models",
    },
    API_PROVIDER_GEMINI: {
        "default_model": DEFAULT_GEMINI_MODEL,
        "default_endpoint": DEFAULT_GEMINI_ENDPOINT,
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "check_path": None,  # Gemini does not support /models check
    },
}


def get_provider_config(provider: str) -> dict[str, Any]:
    """Get full provider configuration.

    Raises ValueError for unknown providers to avoid sending
    credentials to the wrong endpoint.
    """
    if provider not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown API provider: {provider}")
    return PROVIDER_REGISTRY[provider]


def get_default_endpoint(provider: str) -> str:
    """Get default API endpoint for a provider."""
    return get_provider_config(provider)["default_endpoint"]


def get_default_model(provider: str) -> str:
    """Get default model for a provider."""
    return get_provider_config(provider)["default_model"]


def build_auth_headers(provider: str, api_key: str) -> dict[str, str]:
    """Build authentication headers for a provider."""
    config = get_provider_config(provider)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    headers[config["auth_header"]] = f"{config['auth_prefix']}{api_key}"
    if "extra_headers" in config:
        headers.update(config["extra_headers"])
    return headers
