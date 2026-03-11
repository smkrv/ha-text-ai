"""
Utility functions for HA Text AI integration.

@license: CC BY-NC-SA 4.0 International
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

from homeassistant.const import CONF_API_KEY


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



def validate_endpoint(endpoint: str) -> str:
    """Validate API endpoint URL for security.

    Ensures HTTPS-only and blocks private/reserved IP ranges (SSRF protection).
    Returns the validated endpoint stripped of trailing slashes.

    Raises:
        ValueError: If the endpoint fails validation.
    """
    parsed = urlparse(endpoint)

    if parsed.scheme not in ("https",):
        raise ValueError("Only HTTPS endpoints are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid endpoint URL: no hostname")

    # Block private/reserved IPs (direct IP or resolved hostname)
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_reserved or addr.is_loopback or addr.is_link_local:
            raise ValueError("Private/reserved IP addresses are not allowed")
    except ValueError as e:
        if "not allowed" in str(e):
            raise
        # Not an IP literal — resolve hostname and check all resolved IPs
        # to prevent DNS rebinding attacks
        try:
            addrinfos = socket.getaddrinfo(hostname, None)
            for family, _type, _proto, _canonname, sockaddr in addrinfos:
                ip_str = sockaddr[0]
                resolved_addr = ipaddress.ip_address(ip_str)
                if (
                    resolved_addr.is_private
                    or resolved_addr.is_reserved
                    or resolved_addr.is_loopback
                    or resolved_addr.is_link_local
                ):
                    raise ValueError(
                        f"Hostname {hostname} resolves to private/reserved IP {ip_str}"
                    )
        except socket.gaierror:
            raise ValueError(f"Cannot resolve hostname: {hostname}")

    return endpoint.rstrip("/")
