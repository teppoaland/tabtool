"""Configuration helpers."""

from __future__ import annotations

from app.config import is_loopback


def test_loopback_detection() -> None:
    assert is_loopback("127.0.0.1")
    assert is_loopback("::1")
    assert is_loopback("::ffff:127.0.0.1")
    assert is_loopback("localhost")
    assert is_loopback("testclient")


def test_non_loopback_detection() -> None:
    assert not is_loopback(None)
    assert not is_loopback("192.168.1.50")
    assert not is_loopback("10.0.0.2")
