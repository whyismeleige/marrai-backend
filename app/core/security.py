"""SSRF protections for the crawler.

The audit endpoint accepts arbitrary user-submitted URLs, so every hostname
(and every redirect target) must be proven to resolve to a public address
before we connect to it. We intentionally rely on resolved IP ranges rather
than hostname string checks, because DNS is the actual trust boundary.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from app.core.errors import UrlSafetyError

ALLOWED_SCHEMES = {"http", "https"}
# Only standard web ports. A public website audit has no reason to talk to
# arbitrary ports, and restricting them removes a large class of probes.
ALLOWED_PORTS = {80, 443}

_BLOCKED_MESSAGES = {
    "loopback": "This website resolves to a local address and cannot be audited.",
    "private": "This website resolves to a private network and cannot be audited.",
    "link_local": "This website resolves to a link-local address and cannot be audited.",
    "reserved": "This website uses a reserved address range and cannot be audited.",
    "other": "This website address is not publicly reachable and cannot be audited.",
}


def _classify_and_check(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    # Unwrap IPv4-mapped IPv6 addresses (::ffff:127.0.0.1) so they are
    # judged by their real IPv4 range.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped

    if ip.is_loopback:
        raise UrlSafetyError(_BLOCKED_MESSAGES["loopback"])
    if ip.is_link_local:
        raise UrlSafetyError(_BLOCKED_MESSAGES["link_local"])
    if ip.is_private:
        raise UrlSafetyError(_BLOCKED_MESSAGES["private"])
    if ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        raise UrlSafetyError(_BLOCKED_MESSAGES["reserved"])
    # Covers CGNAT (100.64/10), documentation ranges, and everything else
    # that is not globally routable.
    if not ip.is_global:
        raise UrlSafetyError(_BLOCKED_MESSAGES["other"])


async def resolve_host(host: str) -> set[str]:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise UrlSafetyError(
            "We could not resolve that website address. Check the URL and try again.",
            code="unresolved",
        ) from exc

    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise UrlSafetyError(
            "We could not resolve that website address. Check the URL and try again.",
            code="unresolved",
        )
    return addresses


async def assert_url_safe(url: str) -> None:
    """Validate scheme, port, credentials, and every resolved IP of `url`."""
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise UrlSafetyError("That URL could not be parsed.") from exc

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UrlSafetyError("Only http and https URLs can be audited.")

    if parsed.username or parsed.password:
        raise UrlSafetyError("URLs with embedded credentials cannot be audited.")

    if not parsed.hostname:
        raise UrlSafetyError("That URL has no hostname.")

    if parsed.port is not None and parsed.port not in ALLOWED_PORTS:
        raise UrlSafetyError("Only standard web ports (80, 443) can be audited.")

    addresses = await resolve_host(parsed.hostname)
    for raw in addresses:
        _classify_and_check(ipaddress.ip_address(raw))
