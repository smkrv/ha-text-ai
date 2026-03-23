"""
Utility functions for HA Text AI integration.

@license: PolyForm Noncommercial 1.0.0 (https://polyformproject.org/licenses/noncommercial/1.0.0)
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant


def normalize_name(name: str) -> str:
    """Normalize name to conform to HA naming convention using underscores."""
    normalized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
    normalized = '_'.join(filter(None, normalized.split('_')))
    return normalized.lower()


def safe_log_data(
    data: dict[str, Any],
    sensitive_keys: tuple[str, ...] = (CONF_API_KEY,),
) -> dict[str, Any]:
    """Filter sensitive keys from data for safe logging."""
    return {k: "***" if k in sensitive_keys else v for k, v in data.items()}


class _RestrictedIPError(ValueError):
    """Raised when an IP address is in a restricted range."""


def _check_ip_restricted(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address is in a restricted range."""
    return (
        addr.is_private
        or addr.is_reserved
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
    )


async def validate_endpoint(hass: HomeAssistant, endpoint: str, *, allow_local: bool = False) -> str:
    """Validate API endpoint URL for security.

    Ensures HTTPS-only and blocks private/reserved IP ranges (SSRF protection).
    When allow_local is True, permits private IPs and HTTP scheme for self-hosted proxies.
    Uses async DNS resolution to avoid blocking the event loop.
    Returns the validated endpoint stripped of trailing slashes.

    Raises:
        ValueError: If the endpoint fails validation.
    """
    parsed = urlparse(endpoint)

    if allow_local:
        if parsed.scheme not in ("https", "http"):
            raise ValueError("Only HTTPS and HTTP endpoints are allowed")
    else:
        if parsed.scheme not in ("https",):
            raise ValueError("Only HTTPS endpoints are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid endpoint URL: no hostname")

    if allow_local:
        # Even in local mode, block multicast and unspecified addresses
        _is_ip_literal = True
        try:
            addr = ipaddress.ip_address(hostname)
        except ValueError:
            _is_ip_literal = False

        if _is_ip_literal:
            if addr.is_multicast or addr.is_unspecified:
                raise ValueError("Multicast and unspecified addresses are not allowed")
        else:
            # Not an IP literal — resolve and check
            try:
                addrinfos = await hass.async_add_executor_job(
                    socket.getaddrinfo, hostname, None
                )
                for family, _type, _proto, _canonname, sockaddr in addrinfos:
                    resolved = ipaddress.ip_address(sockaddr[0])
                    if resolved.is_multicast or resolved.is_unspecified:
                        raise ValueError(
                            "Hostname resolves to multicast/unspecified address"
                        )
            except socket.gaierror as err:
                raise ValueError(f"Cannot resolve hostname: {hostname}") from err
    else:
        # Full SSRF protection — block private/reserved IPs
        try:
            addr = ipaddress.ip_address(hostname)
            if _check_ip_restricted(addr):
                raise _RestrictedIPError("Private/reserved IP addresses are not allowed")
        except _RestrictedIPError:
            raise
        except ValueError:
            # Not an IP literal — resolve hostname and check all resolved IPs
            # to prevent DNS rebinding attacks
            try:
                addrinfos = await hass.async_add_executor_job(
                    socket.getaddrinfo, hostname, None
                )
                for family, _type, _proto, _canonname, sockaddr in addrinfos:
                    ip_str = sockaddr[0]
                    resolved_addr = ipaddress.ip_address(ip_str)
                    if _check_ip_restricted(resolved_addr):
                        raise ValueError(
                            "Hostname resolves to a restricted IP range"
                        )
            except socket.gaierror as err:
                raise ValueError(f"Cannot resolve hostname: {hostname}") from err

    return endpoint.rstrip("/")
