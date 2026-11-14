"""LAN helpers for the phone/tablet view.

The laptop may sit in another room; the phone in front of the piano opens the
same page over the LAN. This module only answers "which address would a phone
use" and draws the QR code - the same routing-table trick TabTool's remote uses.
"""

from __future__ import annotations

import io
import os
import socket

import segno

from piano import config


def lan_ip() -> str | None:
    """The address a phone on the same network should use, or None."""
    override = os.getenv("PIANO_LAN_IP", "").strip()
    if override:
        return override
    # A UDP connect sends nothing; it asks the routing table which local
    # address would be used. That avoids hard-coding an interface.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        candidate = sock.getsockname()[0]
    except OSError:
        candidate = ""
    finally:
        sock.close()
    if candidate and not candidate.startswith("127."):
        return candidate
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127."):
                return address
    except OSError:
        pass
    return None


def base_url(port: int | None = None) -> str | None:
    """Base URL for a phone, or None when only loopback is reachable."""
    address = lan_ip()
    if not address:
        return None
    return f"http://{address}:{int(port or config.PORT)}"


def qr_svg(text: str, scale: int = 6, border: int = 3) -> bytes:
    """A standalone SVG QR code (dark modules on light, easy to scan)."""
    qr = segno.make(text, error="m")
    buffer = io.BytesIO()
    qr.save(
        buffer,
        kind="svg",
        scale=scale,
        border=border,
        dark="#0b0f14",
        light="#f6f8fb",
        xmldecl=False,
    )
    return buffer.getvalue()
