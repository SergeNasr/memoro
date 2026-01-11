"""Test that network access is blocked in tests."""

import socket

import pytest


def test_network_blocked():
    """TCP connections are blocked during tests."""
    with pytest.raises(Exception) as exc_info:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 8000))
    assert "SocketBlockedError" in str(type(exc_info.value))
