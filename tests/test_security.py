import socket

import pytest

from app.core.errors import UrlSafetyError
from app.core.security import assert_url_safe


def _fake_getaddrinfo(ip):
    if isinstance(ip, Exception):
        def _raise(host, port, *args, **kwargs):
            raise ip
        return _raise

    if ":" in ip:
        sockaddr = (ip, 0, 0, 0)
        family = socket.AF_INET6
    else:
        sockaddr = (ip, 0)
        family = socket.AF_INET

    def _fake(host, port, *args, **kwargs):
        return [(family, socket.SOCK_STREAM, 6, "", sockaddr)]

    return _fake


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "127.0.0.10",
        "10.0.0.5",
        "172.16.0.1",
        "172.31.255.254",
        "192.168.1.1",
        "169.254.169.254",  # cloud metadata endpoint
        "0.0.0.0",
        "100.64.0.1",  # CGNAT / carrier-grade NAT
        "192.0.2.1",  # documentation range
        "255.255.255.255",
        "::1",
        "::",
        "fe80::1",
        "fc00::1",
    ],
)
async def test_private_and_reserved_addresses_blocked(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo(ip))
    with pytest.raises(UrlSafetyError):
        await assert_url_safe("https://example.com/")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ip",
    [
        "93.184.216.34",
        "2606:2800:220:1:248:1893:25c8:1946",
    ],
)
async def test_public_addresses_allowed(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo(ip))
    await assert_url_safe("https://example.com/")


@pytest.mark.asyncio
async def test_ipv4_mapped_ipv6_loopback_blocked(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("::ffff:127.0.0.1"))
    with pytest.raises(UrlSafetyError):
        await assert_url_safe("https://example.com/")


@pytest.mark.asyncio
async def test_unresolvable_host_cannot_be_audited(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo", _fake_getaddrinfo(socket.gaierror("nope"))
    )
    with pytest.raises(UrlSafetyError) as excinfo:
        await assert_url_safe("https://does-not-exist.invalid/")
    assert excinfo.value.code == "unresolved"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/",
        "file:///etc/passwd",
        "ws://example.com/",
        "https://example.com:22/",
        "https://user:pass@example.com/",
        "https://example.com:8080/",
    ],
)
async def test_scheme_port_and_credentials_blocked(monkeypatch, url):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    with pytest.raises(UrlSafetyError):
        await assert_url_safe(url)