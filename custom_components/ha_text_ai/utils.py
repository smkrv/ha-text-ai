"""
Utility functions for HA Text AI integration.

@license: MIT (https://opensource.org/licenses/MIT)
@author: SMKRV
@github: https://github.com/smkrv/ha-text-ai
@source: https://github.com/smkrv/ha-text-ai
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse

import aiohttp
from aiohttp.abc import AbstractResolver

from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

def normalize_name(name: str) -> str:
    """Normalize name to conform to HA naming convention using underscores.

    If the input collapses to an empty string (all non-alphanumeric or
    all underscores), fall back to a short hash of the original so that
    downstream entity IDs never end with a trailing underscore.
    """
    normalized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
    normalized = '_'.join(filter(None, normalized.split('_'))).lower()
    if not normalized:
        digest = hashlib.sha256(name.encode("utf-8", errors="replace")).hexdigest()[:8]
        normalized = f"instance_{digest}"
    return normalized

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

def _is_cloud_metadata_or_unsafe(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    """Block link-local and cloud instance-metadata addresses.

    These must be blocked even in allow_local_network mode:
    - IPv4 link-local (169.254.0.0/16) covers AWS/GCP/Azure IMDS 169.254.169.254.
    - IPv6 link-local (fe80::/10).
    - Multicast and unspecified addresses.
    Without this check, a self-hosted HA running on a cloud VM could be
    tricked into exfiltrating cloud credentials via IMDS.
    """
    return addr.is_multicast or addr.is_unspecified or addr.is_link_local

class _PinnedResolver(AbstractResolver):
    """aiohttp resolver that returns pre-validated IPs for a single hostname.

    Why: prevents DNS-rebinding attacks. After validate_endpoint has
    confirmed the hostname resolves to a safe IP, we pin that IP in the
    resolver used by the aiohttp session. aiohttp then skips its own
    DNS lookup on each request and uses the pinned IP, closing the
    TOCTOU gap between validation and actual HTTP call.
    """

    def __init__(
        self,
        pinned: dict[str, list[tuple[str, int]]],
    ) -> None:
        self._pinned = pinned

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: int = socket.AF_INET,
    ) -> list[dict[str, Any]]:
        entries = self._pinned.get(host.lower())
        if entries is None:
            # Every request on a pinned session must target the validated
            # host. Resolving anything else means a request escaped the pin
            # (a new call site or a config bug) — fail closed rather than
            # fall back to live, unvalidated DNS.
            raise OSError(f"Refusing to resolve unpinned host: {host}")
        return [
            {
                "hostname": host,
                "host": ip,
                "port": port or default_port,
                "family": _family_for(ip),
                "proto": 0,
                "flags": 0,
            }
            for ip, default_port in entries
        ]

    async def close(self) -> None:
        """Nothing to close; the resolver holds only the pinned map."""

def _family_for(ip: str) -> int:
    """Return AF_INET or AF_INET6 based on the IP literal."""
    try:
        return socket.AF_INET6 if ":" in ip else socket.AF_INET
    except Exception:
        return socket.AF_INET

async def resolve_hostname_ips(
    hass: HomeAssistant,
    hostname: str,
) -> list[str]:
    """Resolve hostname to all its IPs via the event-loop-safe executor.

    Returns a list of IP strings (may contain both IPv4 and IPv6).
    Raises ValueError on resolution failure.
    """
    try:
        addrinfos = await hass.async_add_executor_job(
            socket.getaddrinfo, hostname, None
        )
    except socket.gaierror as err:
        raise ValueError(f"Cannot resolve hostname: {hostname}") from err
    ips = []
    seen: set[str] = set()
    for _family, _type, _proto, _canonname, sockaddr in addrinfos:
        ip = sockaddr[0]
        if ip not in seen:
            seen.add(ip)
            ips.append(ip)
    if not ips:
        raise ValueError(f"No IPs for hostname: {hostname}")
    return ips

def create_pinned_session(
    endpoint: str,
    resolved_ips: list[str],
) -> aiohttp.ClientSession:
    """Create an isolated aiohttp session with pinned DNS and no cookie jar.

    Addresses two issues at once:
    - DNS rebinding: aiohttp will reuse the pinned IPs from validate_endpoint
      rather than re-resolving the hostname on each request.
    - Cookie pollution: DummyCookieJar prevents cookies from leaking between
      this integration and other HA components sharing the same domain.

    Built directly on aiohttp: HA's async_create_clientsession always
    injects its own pooled connector and rejects a caller-supplied one,
    so a custom resolver cannot go through the helper. The caller owns
    the session and must close it. Requests must pass
    allow_redirects=False so a 3xx response cannot route past the pinned
    resolver to an unvalidated host.
    """
    parsed = urlparse(endpoint)
    hostname = (parsed.hostname or "").lower()
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    pinned: dict[str, list[tuple[str, int]]] = {
        hostname: [(ip, port) for ip in resolved_ips]
    }
    connector = aiohttp.TCPConnector(resolver=_PinnedResolver(pinned))
    return aiohttp.ClientSession(
        connector=connector,
        cookie_jar=aiohttp.DummyCookieJar(),
    )

async def validate_endpoint(
    hass: HomeAssistant,
    endpoint: str,
    *,
    allow_local: bool = False,
) -> tuple[str, list[str]]:
    """Validate API endpoint URL for security and pin resolved IPs.

    Ensures HTTPS-only and blocks private/reserved IP ranges (SSRF protection).
    When allow_local is True, permits private IPs and HTTP scheme for self-hosted proxies.
    Uses async DNS resolution to avoid blocking the event loop.

    Returns: (validated_endpoint_without_trailing_slash, resolved_ips).
    The resolved IPs are intended for pinning in aiohttp resolver via
    create_pinned_session(), closing the DNS-rebinding TOCTOU gap.

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

    resolved_ips: list[str] = []

    # Collect and check all resolved IPs (or IP literal directly).
    def _collect(ips: list[str]) -> None:
        for ip in ips:
            if ip not in resolved_ips:
                resolved_ips.append(ip)

    try:
        addr = ipaddress.ip_address(hostname)
        _is_ip_literal = True
    except ValueError:
        addr = None
        _is_ip_literal = False

    if _is_ip_literal:
        _collect([hostname])
    else:
        try:
            addrinfos = await hass.async_add_executor_job(
                socket.getaddrinfo, hostname, None
            )
        except socket.gaierror as err:
            raise ValueError(f"Cannot resolve hostname: {hostname}") from err
        _collect([sockaddr[0] for (*_, sockaddr) in addrinfos])

    if not resolved_ips:
        raise ValueError(f"No IPs resolved for hostname: {hostname}")

    # Validate each resolved IP against the selected policy.
    for ip_str in resolved_ips:
        ip_obj = ipaddress.ip_address(ip_str)
        if allow_local:
            if _is_cloud_metadata_or_unsafe(ip_obj):
                raise ValueError(
                    "Link-local/metadata/multicast addresses are not allowed"
                )
        else:
            if _check_ip_restricted(ip_obj):
                raise _RestrictedIPError(
                    "Private/reserved IP addresses are not allowed"
                )

    return endpoint.rstrip("/"), resolved_ips
