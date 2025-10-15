"""Test that network requests are blocked in tests."""

import socket

import httpx
import pytest


def test_tcp_socket_is_blocked():
    """Verify TCP connections are blocked."""
    with pytest.raises(Exception) as exc_info:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 8000))

    assert "SocketBlockedError" in str(type(exc_info.value))


async def test_http_requests_are_blocked():
    """Verify HTTP requests to external URLs are blocked."""
    with pytest.raises(Exception) as exc_info:
        async with httpx.AsyncClient() as client:
            await client.get("https://www.google.com")

    assert "SocketBlockedError" in repr(exc_info.value)


async def test_localhost_http_is_blocked():
    """Verify even localhost HTTP requests are blocked."""
    with pytest.raises(Exception) as exc_info:
        async with httpx.AsyncClient() as client:
            await client.get("http://localhost:8000")

    assert "SocketBlockedError" in repr(exc_info.value)
